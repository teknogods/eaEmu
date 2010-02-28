from __future__ import absolute_import
import hashlib
import random
import time
import struct
import base64

from socket import inet_aton, inet_ntoa
from array import array

from ..db import *
from .. import util

class CipherFactory:
   def __init__(self, gameName):
      self.gameKey = Game.objects.get(name=gameName).key

   def getMasterCipher(self, validate):
      return EncTypeX(self.gameKey, validate)

   def getHeartbeatCipher(self):
      return HeartbeatCipher()

class HeartbeatCipher:
   alphabet = ''.join(chr(x) for x in range(0x21, 0x7f))
   def __init__(self, salt=None):
      if salt == None:
         salt = ''.join(random.choice(self.alphabet) for _ in range(6))
      self.salt = salt

# adapted from aluigi's peerchat_ip.h
class IpEncode:
   cipher = 'aFl4uOD9sfWq1vGp'
   @classmethod
   def encode(cls, ip):
      ip = struct.unpack('<L', inet_aton(ip))[0]
      ip ^= 0xc3801dc7
      return 'X{0}X'.format(''.join(cls.cipher[ip>>4*i&0xf] for i in reversed(range(8))))

   @classmethod
   def decode(cls, encIp):
      ip = 0
      for i, x in enumerate(reversed(encIp[1:-1])):
         ip |= cls.cipher.index(x) << 4*i
      ip ^= 0xc3801dc7
      return inet_ntoa(struct.pack('<L', ip))

   @classmethod
   def d(cls, encIp):
      ip = 0
      for i, x in enumerate(reversed(encIp[1:-1])):
         ip |= cls.cipher.index(x) << 4*i
      ip ^= 0xc3801dc7
      import socket
      ip = socket.ntohl(ip)
      return ip
#SERVER:  \lc\2\sesskey\123456789\proof\0\id\1\final\
#CLIENT:  \authp\\pid\87654321\resp\7fcb80a6255c183dc149fb80abcd4675\lid\0\final\
#resp is the MD5 hash of "passwordDxtLwy}K"
#password is your Gamespy password
#DxtLwy}K is the result of gs_sesskey(123456789);
def gs_sessionkey(sesskey):
   return ''.join(chr(ord(c)+0x11+i) for i, c in enumerate('{0:08x}'.format(sesskey^0x38f371e6)))

def gs_xor(data):
   xs = 'GameSpy3D'
   return ''.join(chr(ord(data[i])^ord(xs[i%len(xs)])) for i in range(len(data)))

def gslame(num):
   c = (num >> 16) & 0xffff
   a = num & 0xffff
   c *= 0x41a7
   a *= 0x41a7
   a += ((c & 0x7fff) << 16)
   a += (c >> 15)
   if a >= 0x80000000: # if a<0 in C
      #make it positive again
      a &= 0x7fffffff
      a += 1
   return a

# adapted from aluigi's code -- thanks!
def passenc(data):
   data = array('B', data)
   num = struct.unpack('<L', 'gspy')[0]

   for i in range(len(data)):
      num = gslame(num)
      data[i] ^= num % 0xff
   return data.tostring()

_gsSpecial = {
   '+' : '[',
   '/' : ']',
   '=' : '_',
}

_eaSpecial = {
   '+' : '_', # these 2 might be swapped
   '/' : '-', # these 2 might be swapped
   '=' : '.',
}

## ???: is all b64 encoded data encrypted like passwords?
def gs64encode(data):
   encData = base64.b64encode(passenc(data))
   for k, v in _gsSpecial.items():
      encData = encData.replace(k, v)
   return encData

def gs64decode(data):
   for k, v in _gsSpecial.items():
      data = data.replace(v, k)
   return passenc(base64.b64decode(data))

def gs_login_proof(pwd, usr, cChal, sChal):
   md5hex = lambda x: hashlib.md5(x).hexdigest()
   return md5hex(md5hex(pwd) + ' '*48 + usr + sChal + cChal + md5hex(pwd))

def getMsName(gamename):
   num = 0
   for c in gamename.lower():
      num = ord(c) - num * 0x63306ce7
   return '{0}.ms{1}.gamespy.com'.format(gamename, (num&0xffffffff)%20)

class EncTypeX:
   #'!"#$%&\'()*+,-./0123456789:;<=>?@ABCDEFGHIJKLMNOPQRSTUVWXYZ[\\]^_`abcdefghijklmnopqrstuvwxyz{|}~'
   alphabet = ''.join(chr(x) for x in range(0x21, 0x7f))
   @staticmethod
   def getRandValidate():
      return ''.join(random.choice(alphabet) for _ in range(8))

   def __init__(self, key, validate=None):
      self.key = array('B', str(key))
      self.start = 0

      # this is gathered from the first message to the server
      # and is generated randomly by the client.
      validate = validate or EncTypeX.getRandValidate()
      self.validate = array('B', str(validate))

      # IV is an array of random bytes of random length X to Y (unsure what x,y are)
      self.initDecoder(''.join(chr(random.getrandbits(8)) for _ in range(random.randint(9, 15))))

   def Decode(self, data):
      '''
      This is just a convenience method for decoding server messages; it strips
      off the header and IV, then returns the decrypted payload.
      '''
      data = array('B', data)

      # initialization takes place here, after the first msg
      # is received that contains some initialization data
      # that varies in length on each connect.
      if self.start == 0:
         assert len(data) > 0
         hdrLen = (data[0] ^ 0xEC) + 2
         #util.getLogger('gamespy.enctypex', self).debug('hdr is %s, len=%d', repr(data[:hdrLen].tostring()), len(data[:hdrLen]))
         assert len(data) >= hdrLen         ivLen = data[hdrLen - 1] ^ 0xEA
         self.start = hdrLen + ivLen
         #util.getLogger('gamespy.enctypex', self).debug('IV is %s, len=%d', repr(data[hdrLen:self.start].tostring()), len(data[hdrLen:self.start]))
         assert len(data) >= self.start
         self.initDecoder(data[hdrLen:][:ivLen])
         data = data[self.start:] #sometimes there is no extra data til next receive

      return self.decrypt(data)

   def initDecoder(self, salt):
      # init the IV
      self.salt = array('B', salt) # in case iv is a string
      # mesh the gamekey, IV, and validate strings together
      # (formerly enctypex_funcx)
      self.iv = array('B', self.validate)
      for i in range(len(self.salt)):
         self.iv[(self.key[i % len(self.key)] * i) & 7] ^= self.iv[i & 7] ^ self.salt[i]

      # init the pad
      self.encxkey = array('B', range(256) + [0]*5)
      self.n1 = self.n2 = 0 # a couple un-understood indexes used during init
      # formerly func4 hereafter
      if len(self.iv) < 1:
         return

      for i in reversed(range(256)):
         t1 = self._func5(i)
         t2 = self.encxkey[i]
         self.encxkey[i] = self.encxkey[t1]
         self.encxkey[t1] = t2

      self.encxkey[256] = self.encxkey[1]
      self.encxkey[257] = self.encxkey[3]
      self.encxkey[258] = self.encxkey[5]
      self.encxkey[259] = self.encxkey[7]
      self.encxkey[260] = self.encxkey[self.n1 & 0xff]

   def _func5(self, cnt):
      if not cnt:
         return 0

      mask = 0
      while mask < cnt:
         mask = (mask << 1) + 1

      i = 0
      while True:
         self.n1 = self.encxkey[self.n1 & 0xff] + self.iv[self.n2]
         self.n2 += 1
         if self.n2 >= len(self.iv):
            self.n2 = 0
            self.n1 += len(self.iv)
         tmp = self.n1 & mask
         i += 1
         if i > 11:
            tmp %= cnt
         if tmp <= cnt:
            break
      return tmp

   def encrypt(self, data):
      return self._crypt(data, True)

   def decrypt(self, data):
      return self._crypt(data, False)

   def _crypt(self, data, encrypt):
      data = array('B', data) # in case data is a string
      for i in range(len(data)):
         d = data[i]
         # formerly func7
         a = self.encxkey[256]
         b = self.encxkey[257]
         c = self.encxkey[a]
         self.encxkey[256] = a + 1 & 0xff
         self.encxkey[257] = b + c & 0xff
         a = self.encxkey[260]
         b = self.encxkey[257]
         b = self.encxkey[b]
         c = self.encxkey[a]
         self.encxkey[a] = b
         a = self.encxkey[259]
         b = self.encxkey[257]
         a = self.encxkey[a]
         self.encxkey[b] = a
         a = self.encxkey[256]
         b = self.encxkey[259]
         a = self.encxkey[a]
         self.encxkey[b] = a
         a = self.encxkey[256]
         self.encxkey[a] = c
         b = self.encxkey[258]
         a = self.encxkey[c]
         c = self.encxkey[259]
         b = b + a & 0xff
         self.encxkey[258] = b
         a = b
         c = self.encxkey[c]
         b = self.encxkey[257]
         b = self.encxkey[b]
         a = self.encxkey[a]
         c = c + b & 0xff
         b = self.encxkey[260]
         b = self.encxkey[b]
         c = c + b & 0xff
         b = self.encxkey[c]
         c = self.encxkey[256]
         c = self.encxkey[c]
         a = a + c & 0xff
         c = self.encxkey[b]
         b = self.encxkey[a]
         c ^= b ^ d
         # en/de crypt diverge here
         if encrypt:
            self.encxkey[259] = d
            self.encxkey[260] = c
         else:
            self.encxkey[259] = c
            self.encxkey[260] = d
         data[i] = c
      return data.tostring()


class PeerchatCipherFactory:
   def __init__(self, gamekey):
      self.gamekey = gamekey
   def getCipher(self):
      return PeerchatCipher(PeerchatCipher.makeChallenge(), self.gamekey)

class PeerchatCipher:
   @staticmethod
   def makeChallenge():
      ## from ';' to '~' -- this is pretty close to exact range.
      ## ':' at the beginning is def. not included (IRC significance)
      alphabet = ''.join(chr(i) for i in range(ord(';'), ord('~')))
      return ''.join(random.choice(alphabet) for _ in range(16))

   def __init__(self, challenge, gamekey):
      self.challenge = challenge
      self.pc1 = 0
      self.pc2 = 0

      gamekey = [ord(x) for x in gamekey]
      chall = [ord(challenge[i])^gamekey[i%len(gamekey)] for i in range(len(challenge))]

      self.table = [x for x in reversed(range(256))]
      # scramble up the table based on challenge
      tmp = 0
      for i in range(len(self.table)):
         tmp = (tmp + chall[i%len(chall)] + self.table[i]) & 0xFF

         # now just swap
         tmp2 = self.table[tmp]
         self.table[tmp] = self.table[i]
         self.table[i] = tmp2

   def crypt(self, data):
      outdata = array('B')

      for datum in data:
         self.pc1 = (self.pc1 + 1) & 0xFF
         tmp = self.table[self.pc1]
         self.pc2 = (self.pc2 + tmp) & 0xFF
         self.table[self.pc1] = self.table[self.pc2]
         self.table[self.pc2] = tmp
         tmp = (tmp + self.table[self.pc1]) & 0xFF
         outdata.append(ord(datum) ^ self.table[tmp])

      return outdata.tostring()
