import struct
import random
import md5
import logging
import time
import re

from array import array

from twisted.internet.protocol import DatagramProtocol, Protocol, ServerFactory
from twisted.application.internet import TCPServer, UDPServer
from twisted.web.server import Site
from twisted.web.static import File
from twisted.web.resource import Resource
from twisted.protocols.portforward import *
from twisted.words.protocols.irc import IRC

from SOAPpy.SOAPBuilder import SOAPBuilder

from matchmaking import *

# TODO: move to own module, conditional import
from dj.eaEmu.models import Channel, GamespyGame

# TODO: move to db
# to find gamekey, look for gameid in memory, like 'menofwarpcd' ASCII
# gamekey is usually nearby, <1k away
gameKeys = {
   'redalert3pc'    : 'uBZwpf',
   'menofwarpcd'    : 'z4L7mK',
   'menofwarpc'     : 'KrMW4d',
}

class AvailableServer(DatagramProtocol):
   log = logging.getLogger('gamespy.available.server')
   def datagramReceived(self, data, (host, port)):
      if data.startswith('\x09\0\0\0'):
         # eg, '\x09\0\0\0\0redalert3pc\0':
         # same response for all games
         print 'available!'
         self.transport.write(struct.pack('L', 0x0009fdfe) + '\0'*3, (host, port))
      else:
         self.log.error('unhandled request: %s' % repr(data))
         # TODO (maybe just skip it and fix as needed): udp forward
         #ProxyServer.dataReceived(self, data)

# It's pretty awesome how simple this is...
class DownloadsServerFactory(Site):
   def __init__(self):
      Site.__init__(self, File('.'))

#def getService(address):
   #return UDPServer(address[1], AvailableServer())
   #return TCPServer(address[1], DownloadsServerFactory())
   #return TCPServer(address[1], GPCMFwdServerFactory(*address))
   
class PeerchatCipher:
   @staticmethod
   def makeChallenge():
      return ''.join(random.sample(r'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ_|\<>[]{}=^@;?`', 16)) # TODO figure out this exact set
   
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
   
class GamespyMessage:
   def __init__(self, data):
      self.data = data
      self.map = dict(self.data)
   
   def __repr__(self):
      #return ''.join(['\\{0}\\{1}'.format(k, v) for k, v in self.data.iteritems()] + ['final\\'])
      return ''.join(['\\{0}\\{1}'.format(k, v) for k, v in self.data] + ['\\final\\'])

def parseMsgs(data, xor=False):
   # this technique does not properly discard garbage
   # Should use regex r'(\\.*\\.*\\)+\\final\\'
   msgs = []
   for msg in [gs_xor(x) if xor else x for x in data.split('\\final\\') if x]:
      tokens = msg.split('\\')[1:]
      msgs.append(GamespyMessage(zip(tokens[::2], tokens[1::2])))
   return msgs
   
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

class GamespySession(Session):
   pass

class GamespyTheater(Theater):
   sessionClass = GamespySession
   #userClass = GamespyUser

class LoginServer(Protocol):
   def connectionMade(self):
      Protocol.connectionMade(self)
      self.session = self.theater.Connect()
      
   def dataReceived(self, data):
      try:
         for msg in parseMsgs(data):
            ep = '{0.host}:{0.port}'.format(self.transport.getPeer())
            self.factory.log.debug('received ({0}): {1}'.format(ep, msg.data))
            method = getattr(self, 'cmd_{0}'.format(msg.data[0][0]), None)
            if method:
               method(msg)
            else:
               self.factory.log.debug('unhandled: {0}'.format(msg.data))
      except:
         raise
      
   def cmd_ka(self, msg):
      self.sChal = ''.join(random.sample(string.ascii_uppercase, 10))
      self.sendMsg(GamespyMessage([
         ('lc', '1'),
         ('challenge', self.sChal),
         ('id', '1'),
      ]))
      
   def sendMsg(self, msg):
      self.factory.log.debug('sent: {0}'.format(msg.data))
      self.transport.write(repr(msg))

gsBase64 = '0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ]['

def gs_login_proof(pwd, usr, cChal, sChal):
   def md5hex(data):
      m = md5.new()
      m.update(data)
      return m.hexdigest()
   return md5hex(md5hex(pwd) + ' '*48 + usr + sChal + cChal + md5hex(pwd))
   
def getMsName(gamename):
   num = 0
   for c in gamename.lower():
      num = ord(c) - num * 0x63306ce7
   return '{0}.ms{1}.gamespy.com'.format(gamename, (num&0xffffffff)%20)

class CipherFactory:
   @staticmethod
   def getMasterCipher(gameName, validate):
      return EncTypeX(gameKeys[gameName], validate)


class EncTypeX:
   def __init__(self, key, validate=None):
      self.key = array('B', key)
      self.encxkey = array('B', range(256) + [0]*5)
      self.start = 0
      
      # this is gathered from the first message to the server
      # and is generated randomly by the client.
      validate = validate or gs_rand_validate()
      self.validate = array('B', validate)
      
      # IV is a random array of bytes of random length - unsure what bounds are
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
         #logging.getLogger('gamespy.enctypex').debug('hdr is %s, len=%d', repr(data[:hdrLen].tostring()), len(data[:hdrLen]))
         assert len(data) >= hdrLen         ivLen = data[hdrLen - 1] ^ 0xEA
         self.start = hdrLen + ivLen
         #logging.getLogger('gamespy.enctypex').debug('IV is %s, len=%d', repr(data[hdrLen:self.start].tostring()), len(data[hdrLen:self.start]))
         assert len(data) >= self.start
         self.initDecoder(data[hdrLen:][:ivLen])
         data = data[self.start:] #sometimes there is no extra data til next receive
      
      return self.decrypt(data)
   
   def initDecoder(self, salt):
      self.salt = array('B', salt) # in case iv is a string
      # a couple un-understood indexes used during init
      self.n1 = self.n2 = 0
      def func5(cnt):
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
      
      # mesh the gamekey, IV, and validate strings together
      # (formerly enctypex_funcx)
      self.iv = array('B', self.validate)
      for i in range(len(self.salt)):
         self.iv[(self.key[i % len(self.key)] * i) & 7] ^= self.iv[i & 7] ^ self.salt[i]
         
      # formerly func4 hereafter
      if len(self.iv) < 1:
         return
      
      for i in reversed(range(256)):
         t1 = func5(i)
         t2 = self.encxkey[i]
         self.encxkey[i] = self.encxkey[t1]
         self.encxkey[t1] = t2
   
      self.encxkey[256] = self.encxkey[1]
      self.encxkey[257] = self.encxkey[3]
      self.encxkey[258] = self.encxkey[5]
      self.encxkey[259] = self.encxkey[7]
      self.encxkey[260] = self.encxkey[self.n1 & 0xff]
   
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

def gs_rand_validate():
   validate = ''
   rnd = ~int(time.time())
   for i in range(8):
      while True:
         rnd = ((rnd * 0x343FD) + 0x269EC3) & 0x7f
         if rnd >= 0x21 and rnd < 0x7f:
            break
      validate += chr(rnd)
   return ''.join(validate)



class PeerchatCipherFactory:
   def __init__(self, gamekey):
      self.gamekey = gamekey
   def getCipher(self):
      return PeerchatCipher(PeerchatCipher.makeChallenge(), self.gamekey)

class Peerchat(IRC):
   def connectionMade(self):
      IRC.connectionMade(self)
      self.sCipher = self.cipherFactory.getCipher()
      self.cCipher = self.cipherFactory.getCipher()
      self.doCrypt = False
      self.log  = logging.getLogger('gamespy.peerchat.{0}'.format(self.factory.gameName))

   def dataReceived(self, data):
      if self.doCrypt:
         data = self.cCipher.crypt(data)
      self.log.debug('recv IRC: {0}'.format(repr(data)))
      IRC.dataReceived(self, data)
   
   def sendLine(self, line):
      data = line + '\n' # peerchat doesn't send \r
      self.log.debug('send IRC: {0}'.format(repr(data)))
      if self.doCrypt:
         data = self.sCipher.crypt(data)
      #IRC.sendLine(self, line) # NONO! \r\n won't get encrypted!!
      self.transport.write(data)
      
   # TODO: enumerate cmd ids and use more meaningful names
   
   # note that trailing params come as last element in 'params'
   
   def irc_CRYPT(self, prefix, params):
      self.sendMessage('705', '*', self.cCipher.challenge, self.sCipher.challenge, prefix='s')
      self.doCrypt = True
      
   def irc_USRIP(self, prefix, params):
         self.sendMessage('302', '', ':=+@{0}'.format(self.transport.getPeer().host), prefix='s')
   
   def irc_USER(self, prefix, params):
      #'XflsaqOa9X|165580976' is encodedIp|GSProfileId aka user, '127.0.0.1', 'peerchat.gamespy.com', 'a69b3a7a0837fdcd763fdeb0456e77cb' is cdkey
      self.user, ip, host, cdkey = params
   
   def irc_NICK(self, prefix, params):
      self.nick = params[0]
      self.sendMessage('001', self.nick, ':Welcome to the Matrix {0}'.format(self.nick))
      self.sendMessage('002', self.nick, ':Your host is xs5, running version 1.0') # TODO
      self.sendMessage('003', self.nick, ':This server was created Fri Oct 19 1979 at 21:50:00 PDT') # TODO
      self.sendMessage('004', self.nick, 's 1.0 iq biklmnopqustvhe')
      self.sendMessage('375', self.nick, ':(M) Message of the day -')
      self.sendMessage('372', self.nick, ':Welcome to GameSpy')
      self.sendMessage('376', self.nick, ':End of MOTD command')
      
   def irc_CDKEY(self, prefix, params):
      self.sendMessage('706', self.nick, '1', ':Authenticated')
      
   def irc_JOIN(self, prefix, params):
      chan = params[0]
      chanTokens = chan.split('!')
      if chanTokens[0] == '#GPG': # chat lobby
         chanId = chanTokens[1]
         self.channel = Channel.objects.get(id=chanId)
         self.sendMessage('JOIN', ':#GPG!{0}'.format(chanId), prefix=self.getClientPrefix())
      elif chanTokens[0] == '#GSP': # we're joining a game lobby
         self.channel = Channel.objects.create(name=chan, prettyName=chan, game=GamespyGame.objects.get(name=chanTokens[1]))
         self.sendMessage('JOIN', ':'+params[0], prefix=self.getClientPrefix())
         
   def getClientPrefix(self):
      # follows RFC prefix BNF
      return '{0}!{1}@*'.format(self.nick, self.user)
         
   def irc_PART(self, prefix, params):
      pass
   
   def irc_QUIT(self, prefix, params):
      pass
   
   def irc_MODE(self, prefix, params):
      chan = self.channel.name
      if chan.startswith('#GPG'):
         self.send_RPL_TOPIC('Click on the "Game Info" button at the top of your screen for '
                             'the latest information on patches, add-on files, interviews, '
                             'strategy guides and more!  It`s all there!')
         self.sendMessage('333', self.nick, chan, 'SERVER', '1245741924', prefix='s')
         # don't forget self in this list!
         self.send_RPL_NAMEREPLY((self.nick,))
         self.send_RPL_ENDOFNAMES()
      elif chan.startswith('#GSP'):
         self.send_RPL_NOTOPIC()
         #self.sendNamesList()
         self.send_RPL_NAMEREPLY(('@'+self.nick,))
         self.send_RPL_ENDOFNAMES()
         
   def irc_UTM(self, prefix, params):
      if params and params[-1].startswith('MAP'):
         self.sendMessage('UTM', self.nick, prefix=self.getClientPrefix())
         
   def irc_TOPIC(self, prefix, params):
      pass # TODO: analyze and implement
         
   def irc_GETCKEY(self, prefix, params):
      pass # TODO: analyze and implement
   
   def irc_SETCKEY(self, prefix, params):
      pass # TODO: analyze and implement
   
   def send_RPL_NOTOPIC(self):
         self.sendMessage('331', self.nick, self.channel.name, ':No topic is set', prefix='s')
   def send_RPL_TOPIC(self, topic):
         self.sendMessage('332', self.nick, self.channel.name, ':'+topic, prefix='s')
   def send_RPL_NAMEREPLY(self, names):
         self.sendMessage('353', self.nick, '*', self.channel.name, ':'+' '.join(names), prefix='s')
   def send_RPL_ENDOFNAMES(self):
         self.sendMessage('366', self.nick, self.channel.name, ':End of NAMES list', prefix='s')
      

class PeerchatFactory(ServerFactory):
   protocol = Peerchat
   
   def __init__(self,  gameName):
      self.gameName = gameName
      
   def buildProtocol(self, addr):
      inst = ServerFactory.buildProtocol(self, addr)
      inst.cipherFactory = PeerchatCipherFactory(gameKeys[self.gameName])
      return inst
   
def makeRecv(superClass, xor=False):
   def recv(self, data):
      self.factory.log.debug('received: {0}'.format([x.data for x in parseMsgs(data, xor)]))
      superClass.dataReceived(self, data)
   return recv

def recvMasterCli(self, data):
   self.factory.log.debug('received: {0}'.format(data))
   ProxyClient.dataReceived(self, data)

def recvMasterSrv(self, data):
   self.factory.log.debug('received: {0}'.format(data))
   ProxyServer.dataReceived(self, data)
   

class CipherProxy:
   def __init__(self, server, client, gamekey):
      self.clientIngress = PeerchatCipher(server, gamekey)
      self.clientEgress = PeerchatCipher(server, gamekey)
      self.serverIngress = PeerchatCipher(client ,gamekey)
      self.serverEgress = PeerchatCipher(client ,gamekey)
   
   def recvFromServer(self, data):
      unenc = self.serverIngress.crypt(data)
      log = logging.getLogger('gamespy.chatCli') #HACKy
      log.debug('received: '+repr(unenc))
      if 'Unknown CD Key' in unenc:
         unenc = re.sub(r'(:s 706 \w+) .*', r'\1 1 :Authenticated', unenc)
         log.debug('but sending this instead: %s', unenc)
      return self.serverEgress.crypt(unenc)
   
   def recvFromClient(self, data):
      unenc = self.clientIngress.crypt(data)
      log = logging.getLogger('gamespy.chatServ') #HACKy
      log.debug('received: '+repr(unenc))
      #patches follow
      return self.clientEgress.crypt(unenc)

class ProxyPeerchatClient(ProxyClient):
   cipher = None #a little HACKy
   def dataReceived(self, data):
      # first receive should have challenges
      if not self.cipher:
         logging.getLogger('gamespy').debug(repr(data))
         sChal = data.split(' ')[-2].strip()
         cChal = data.split(' ')[-1].strip()
         self.cipher = CipherProxy(sChal, cChal, self.peer.gamekey)
      else:
         data = self.cipher.recvFromServer(data)
      ProxyClient.dataReceived(self, data)
   
class ProxyPeerchatClientFactory(ProxyClientFactory):
   protocol = ProxyPeerchatClient
   log = logging.getLogger('gamespy.chatCli')
   
class ProxyPeerchatServer(ProxyServer):
   clientProtocolFactory = ProxyPeerchatClientFactory
   def dataReceived(self, data):
      if self.peer.cipher:
         data = self.peer.cipher.recvFromClient(data)
      else:
         logging.getLogger('gamespy').debug(repr(data))
      ProxyServer.dataReceived(self, data)

class ProxyPeerchatServerFactory(ProxyFactory):
   protocol = ProxyPeerchatServer
   log = logging.getLogger('gamespy.chatSrv')
   
   def __init__(self, gameName, host, port):
      ProxyFactory.__init__(self, host, port)
      self.gameName = gameName
      
   def buildProtocol(self, addr):
      p = ProxyFactory.buildProtocol(self, addr)
      p.gamekey = gameKeys[self.gameName]
      return p
   
from twisted.web.soap import SOAPPublisher

# generate the classes with 'wsdl2py -wb http://redalert3pc.sake.gamespy.com/SakeStorageServer/StorageServer.asmx?WSDL'
from StorageServer_server import *
from StorageServer_server import StorageServer as StorageServerBase
class StorageServer(StorageServerBase):
   def soap_SearchForRecords(self, ps, **kw):
      #TODO: write helpers that will covert dict+lists into these calls
      request = ps.Parse(SearchForRecordsSoapIn.typecode)
      logging.getLogger('gamespy.sake').debug(request.__dict__)
      logging.getLogger('gamespy.sake').debug(request._ownerids.__dict__)
      logging.getLogger('gamespy.sake').debug(request._fields.__dict__)
      result = SearchForRecordsSoapOut()
      result.SearchForRecordsResult = 'Success'
      result.Values = result.new_values()
      # TODO - return real vals. null just skips to login ;)
      # -- find out how to return null element... <value />
      '''
      result.Values.ArrayOfRecordValue = [result.Values.new_ArrayOfRecordValue()]
      result.Values.ArrayOfRecordValue[0].RecordValue = []
      for val in [1, 2, 2, 5]:
         container = result.Values.ArrayOfRecordValue[0].new_RecordValue()
         container.ShortValue = container.new_shortValue()
         container.ShortValue.Value = val
         result.Values.ArrayOfRecordValue[0].RecordValue.append(container)
      '''
      return request, result
   
   def _writeResponse(self, response, request, status=200):
      #response = response.replace('<SOAP-ENV:Header></SOAP-ENV:Header>', '')
      #response = response.replace('<ns1:values></ns1:values>', '<ns1:values />')
      #response = '<?xml version="1.0" encoding="utf-8"?>' + response
      logging.getLogger('gamespy.sake').debug(response)
      r = StorageServerBase._writeResponse(self, response, request, status)
      return r
   
class SakeServer(Site):
   def __init__(self):
      root = Resource()
      sakeStorageServer = Resource()
      root.putChild('SakeStorageServer', sakeStorageServer)
      sakeStorageServer.putChild('StorageServer.asmx', StorageServer())
      Site.__init__(self, root)


class ProxyMasterClient(ProxyClient):
   def dataReceived(self, data):
      dec = self.peer.decoder.Decode(data)
      if dec:
         self.factory.log.debug('decoded: '+ repr(dec))
      ProxyClient.dataReceived(self, data)
         
class ProxyMasterClientFactory(ProxyClientFactory):
   protocol = ProxyMasterClient
   log = logging.getLogger('gamespy.masterCli')
         
class ProxyMasterServer(ProxyServer):
   clientProtocolFactory = ProxyMasterClientFactory
   
   def dataReceived(self, data):
      # everytime a request goes out, re-init the decoder
      validate = data[9:].split('\0')[2][:8]
      self.decoder = EncTypeX(self.gamekey, validate)
      self.factory.log.debug('received: '+repr(data))
      ProxyServer.dataReceived(self, data)

class ProxyMasterServerFactory(ProxyFactory):
   protocol = ProxyMasterServer
   log = logging.getLogger('gamespy.masterSrv')
   
   def __init__(self, gameName, host, port):
      ProxyFactory.__init__(self, host, port)
      self.gameName = gameName

   def buildProtocol(self, addr):
      p = ProxyFactory.buildProtocol(self, addr)
      p.gamekey = gameKeys[self.gameName]
      return p
   
