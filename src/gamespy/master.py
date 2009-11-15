import logging
import re
import base64
import struct
from socket import inet_aton, inet_ntoa
from datetime import datetime, timedelta

from twisted.internet.protocol import Protocol, DatagramProtocol
from twisted.protocols.portforward import *

import db
import aspects2 as aspects
from enum import Enum
from cipher import CipherFactory

class MasterMsg(Enum):
   CHALLENGE_RESPONSE = 0x01
   HEARTBEAT          = 0x03
   KEEPALIVE          = 0x08
   AVAILABLE          = 0x09
   RESPONSE_CORRECT   = 0x0A

#class HeartbeatMasterProxy(DatagramProtocol):
   #def datagramReceived(self, data, (host, port)):

class HeartbeatMaster(DatagramProtocol):
   '''
   This fulfills the role of both redalert3pc.available.gamespy.com and redalert3pc.master.gamespy.com.
   Both of these real DNS addrs point to the same master.gamespy.com currently.

   I think the two master servs are separate in order to save
   bandwidth and CPU usage by running the heartbeat service as UDP. heartbeat packets can get dropped too.
   '''
   log = logging.getLogger('gamespy.heartbeatMaster')

   def datagramReceived(self, data, (host, port)):
      msgId, clientId, body = ord(data[0]), struct.unpack('!L', data[1:][:4])[0], data[5:]
      if msgId == MasterMsg.AVAILABLE:
         # eg, '\x09\0\0\0\0redalert3pc\0':
         # same response for all games
         self.log.debug('{0} is available.'.format(body.strip('\0')))
         self.sendMsg(struct.pack('L', 0x0009fdfe) + '\0'*3, (host, port))
      elif msgId == MasterMsg.HEARTBEAT:
         #msgDict = dict(zip(*[info.split('\0')[x::2] for x in range(2)]))
         info = {}
         tokens = body.split('\0')
         for i in range(0, len(tokens), 2):
            if tokens[i]:
               info[tokens[i]] = tokens[i+1]
            else:
               remainder = '\0'.join(tokens[i:])
               break

         self.log.debug('{0}:{1} - info: {2}'.format(host, port, repr(info)))
         self.log.debug('remainder: {0}'.format(repr(remainder)))
         if info['publicip'] == '0': # first heartbeat has no public ip because it needs it from us
            cFact = CipherFactory(info['gamename'])
            chall = cFact.getHeartbeatCipher().salt
            self.sendMsg(
               '\xfe\xfd' + chr(MasterMsg.CHALLENGE_RESPONSE) + struct.pack('!L', clientId) + chall + base64.b16encode('\x00' + inet_aton(host) + struct.pack('!H',  port)) + '\0',
               (host, port)
            )
         ## sometimes, messages come with just ip update info and no groupid or hostname. I'm assuming the 4byte id is used to identify the session.
         if 'groupid' not in info:
            #self.log.debug('weird msg from {0}:{1} -- {2}'.format(host, port, repr(data)))
            session = db.MasterGameSession.objects.get(clientId=clientId)
         else:
            try:
               ## HACK: grab old instance, if it exists
               session = db.MasterGameSession.objects.get(hostname=info['hostname'])
               session.clientId = clientId
            except db.MasterGameSession.DoesNotExist, ex:
               ## create new session
               session = db.MasterGameSession.objects.create(hostname=info['hostname'], clientId=clientId, channel=db.Channel.objects.get(id=info['groupid']))

         ## update and save the info
         for k, v in info.iteritems():
            if k == 'publicip': ## this comes as BE int string
               v = inet_ntoa(struct.pack('<l', int(v))) ## assume the client behaved badly and took a BE int and read it as a signed LE
            setattr(session, k, v)
         session.save()

      elif msgId == MasterMsg.CHALLENGE_RESPONSE:
         self.log.debug('TODO: chall resp is always accepted, currently.')
         ## send the acknowledgment
         self.sendMsg('\xfe\xfd' + chr(MasterMsg.RESPONSE_CORRECT) + struct.pack('!L', clientId), (host, port))
      elif msgId == MasterMsg.KEEPALIVE:
         self.log.debug('TODO: keepalive')
      else:
         self.log.error('unhandled message: {0}'.format(repr(data)))

   def sendMsg(self, data, (host, port)):
      self.log.debug('sent: {0}'.format(repr(data)))
      self.transport.write(data, (host, port))

class ProxyMasterClient(ProxyClient):
   def dataReceived(self, data):
      dec = self.peer.decoder.Decode(data)
      if dec:
         self.factory.log.debug('decoded: '+ repr(dec))
         if '~' in dec:
            from socket import *
            tokens = dec.split('~')
            for sub in tokens[1:]:
               if len(sub) >= 16:
                  self.factory.log.debug('ips: {0}'.format([inet_ntoa(x) for x in [sub[:4], sub[6:][:4], sub[12:][:4]]]))
      ProxyClient.dataReceived(self, data)

class ProxyMasterClientFactory(ProxyClientFactory):
   protocol = ProxyMasterClient
   log = logging.getLogger('gamespy.masterCli')

class ProxyMasterServer(ProxyServer):
   clientProtocolFactory = ProxyMasterClientFactory

   def dataReceived(self, data):
      self.factory.log.debug('received: '+repr(data))
      ProxyServer.dataReceived(self, data)
      # everytime a request goes out, re-init the decoder
      validate = data[9:].split('\0')[2][:8]
      self.decoder = self.factory.cipherFactory.getMasterCipher(validate)

class ProxyMasterServerFactory(ProxyFactory):
   protocol = ProxyMasterServer
   log = logging.getLogger('gamespy.masterSrv')

   def __init__(self, gameName, host, port):
      ProxyFactory.__init__(self, host, port)
      self.cipherFactory = CipherFactory(gameName)

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

class QueryMasterMessage(dict):
   @classmethod
   def getMessage(cls, data):
      m = cls()
      (m['length'], m['headerRemainder']), data = struct.unpack('!H6s', data[:8]), data[9:] # 8, 9 skip the null in between
      m['gameName'], m['gameName2'], data = data.split('\0', 2)
      m['validate'], (m['request'], m['fields'], m['tail']) = data[:8], data[8:].lstrip('\0').split('\0', 2) # sometimes theres a preceding null, sometimes not?? :P
      m['fields'] = m['fields'].split('\\')[1:]
      return m

# HACK, TODO: right now this depends on the factory having a gameName attr, see also Proxy verison above
class QueryMaster(Protocol):
   def dataReceived(self, data):
      # first 8 are binary with some nulls, so have to skip those manually before splitting
      msg = QueryMasterMessage.getMessage(data)
      #self.factory.log.debug('received: {0}'.format(m))
      self.factory.log.debug('received: request={0}'.format(msg['request']))
      self.handleRequest(msg)

   def sendMsg(self, msg):
      self.factory.log.debug('sent: {0}'.format(repr(msg)))
      self.transport.write(msg)

   def handleRequest(self, msg):
      # HACK, TODO: do this more intelligently
      if msg['request'].startswith('\\hostname'):
         self.handle_getRooms(msg)
      elif msg['request'].startswith('(groupid'):
         #print('got game request: {0} | {1}'.format(msg['request'], msg['fields']))
         self.handle_getGames(msg)

   def makeFieldList(self, fields):
      '''
      Fields must always be returned in the order requested, so use list of tuples
      for 'fields'.
      '''
      return chr(len(fields)) + ''.join(chr(v)+k+'\0' for k, v in fields)


   ## TODO: if this list is too long, client can't find the game it's looking for when invited
   ##       Fix is to implement the continuation msgs like the real service does. Also, use string table for smaller msgs.
   def handle_getGames(self, msg):
      '''
      ## requests look like this:
      ## msg tags
      "\x00\xd9\x00\x01\x03\x00\x00\x01\x00redalert3pc\x00redalert3pc\x00f99.qM3$"
      ## request
      "(groupid=2167) AND (gamemode != 'closedplaying')\x00"
      ## fieldlist
      '\\hostname\\gamemode\\hostname\\mapname\\gamemode\\vCRC\\iCRC\\cCRC\\pw\\obs\\rules\\pings\\numRPlyr\\maxRPlyr\\numObs\\mID\\mod\\modv\\name_\x00'
      '\x00\x00\x00\x04' # big endian 4? is this used as a continuation marker for next request?

      ## TODO: handle queries generically, given to us in the format
      ## "(blah = val) and (blah2 = val2)"
      '''
      epList = []
      match = re.match(r'\(groupid=(.*?)\)', msg['request'])
      ep = self.transport.getPeer()
      response = inet_aton(ep.host) + struct.pack('!H', ep.port)
      response += self.makeFieldList([(f, 0) for f in msg['fields']])
      ## TODO: dynamically determine whether to use these and pick fields dynamically
      ## to do this, do select top 5 distinct col or something to find most frequent values among col
      response += '\0' ## TODO : use vals list
      if match:
         groupId = match.group(1)
         for session in db.MasterGameSession.objects.filter(channel__id=groupId):
            ## prune any stale entries that have had no updates for 2 mins
            if session.updated < datetime.now() - timedelta(minutes=2):
               session.delete()
               continue

            epList.append(inet_aton(session.publicip) + struct.pack('!H', session.publicport))

            ## Use first class C ip as the local ip. This rule is guessed, but seems to always work.
            for ndx in range(4):
               localIp = getattr(session, 'localip{0}'.format(ndx))
               if localIp.startswith('192.168.') or localIp.startswith('10.'):
                  #print('selecting', localIp)
                  break
            ## This first part of a gamelobby entry is used to create the room name's hash.
            ## room name hash is based off of publicip, localip reported here (maybe ports too?)
            response += ('~'
               ## game channel name is based off of some or all of this info!
               ## TODO: RE that hash

               + inet_aton(session.publicip)
               + struct.pack('!H', session.publicport)
               + inet_aton(localIp)
               + struct.pack('!H', session.localport)
               ## This 3rd ip is the the host farthest along the route.
               ## When all the hosts respond along the route, it's the same as the public ip.
               ## I don't know how/if this is actually used by the game.
               + inet_aton(session.publicip)
             )
            print('public={0} private={1}'.format((session.publicip, session.publicport), (localIp, session.localport)))
            response += ''.join('\xff{0}\x00'.format(getattr(session, f.rstrip('_'))) for f in msg['fields'])
         response += '\x00'
         response += '\xff'*4 ## terminator for first part of the response
         self.sendMsg(response)
         ## once this first response is sent, this server can continue to send
         ## results one-by-one. To do this, it first sends a hdr msg in the format of:
         ##   len of whole msg(BE-short),0x01,makeFieldList()-type list
         ## then entries in format:
         ##   BE-shortlen of whole msg,0x02,regular entry starting with '~...', then an extra \x00 terminator
         ##     (thats 1 term for last value, 1 regular term as with first msg, then another null in place of FFFFFFFF for first msg)
         ## these update lines must embed all strings (val list cannot be used as in first response)
         ## TODO: sometimes these lines are even shorter, though, and dont begin with a '~'!
         ## TODO: msg type 0x04, it updates ip of a game in the order it was sent -- BElen,0x04,ip,port

         ## is this just a complete list of all fields?
         fields = [
            'hostname',
            'mapname',
            'numplayers',
            'maxplayers',
            'gamemode',
            'vCRC',
            'iCRC',
            'pw',
            'obs',
            'rules',
            'pings',
            'numRPlyr',
            'maxRPlyr',
            'numObs',
            'name',
            'cCRC',
            'mID',
            'mod',
            'modv',
            'teamAuto',
            'joinable',
         ]
         response = '\x01' + self.makeFieldList([(f,0) for f in fields]) ## TODO enum this 01
         response = struct.pack('!H', len(response) + 2) + response
         self.sendMsg(response)
         for ep in epList:
            response = '\x04' + ep
            response = struct.pack('!H', len(response) + 2) + response
            self.sendMsg(response)


   def handle_getRooms(self, msg):
      channels = db.Channel.objects.filter(game__name=self.factory.gameName, name__startswith='gpg')
      ep = self.transport.getPeer()
      self.sendMsg(
         inet_aton(ep.host)
         + struct.pack('!H', ep.port) ## TODO: is this always 0 in real msgs?
         + self.makeFieldList((
            ('hostname', 0),
            ('numwaiting', 0),
            ('maxwaiting', 0),
            ('numservers', 0),
            ('numplayers', 1),
            ('roomType', 0),
         )) +
         '\0' ## TODO: strings array goes here
         + ''.join(
                   ## TODO!!!!!!!
                   ## numwaiting < maxwaiting for client to be allowed to join?
                   ## numplayers plrs in numservers?
                   ## what's roomtype? always '1' in real list i think
                   ## how does the channel:number notation work?? -- maybe number is string ndx?
                   '@{0}' # room id
                   '\xff{1}\x00' ##hostname (room name)
                   '\xff0\x00' ##numwaiting
                   '\xff100\x00' ## maxwaiting
                   '\xff0\x00' ## numservers
                   '\x00' ## numplayers (immediate val as defined above)
                   '\xff1\x00' ## roomtype
                  .format(struct.pack('!L', c.id), c.prettyName) for c in channels)
         + '\x00\xff\xff\xff\xff'
      )

@aspects.Aspect(QueryMaster)
class QueryMasterEncryption(object):
   def connectionMade(self):
      yield aspects.proceed
      def writeWrap(self_transport, data):
         yield aspects.proceed(self_transport,
            # first byte ^ 0xec is hdr content length, second ^ 0xea is salt length
            struct.pack('!BxxB', 0xEC ^ 2, 0xEA ^ len(self.cipher.salt)) # 0 len hdr works too...
            + self.cipher.salt.tostring()
            + self.cipher.encrypt(data)
         )
      aspects.with_wrap(writeWrap, self.transport.write)

   def dataReceived(self, data):
      # everytime a request comes in, re-init the cipher
      msg = QueryMasterMessage.getMessage(data)
      self.cipher = CipherFactory(self.factory.gameName).getMasterCipher(msg['validate'])
      yield aspects.proceed

