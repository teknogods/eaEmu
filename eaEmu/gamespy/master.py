from __future__ import absolute_import
import logging
import threading
import re
import base64
import struct
from socket import inet_aton, inet_ntoa
from datetime import datetime, timedelta

from twisted.internet.protocol import Protocol, DatagramProtocol
from twisted.protocols.portforward import *
from twisted.internet.tcp import Server

from .cipher import CipherFactory
from ..db import *
from ..util import aspects, getLogger
from ..util.enum import Enum

class MasterMsg(Enum):
   CHALLENGE_RESPONSE = 0x01
   HEARTBEAT          = 0x03
   KEEPALIVE          = 0x08
   AVAILABLE          = 0x09
   RESPONSE_CORRECT   = 0x0A

class ResponseType(Enum):
   VALUE_MAP          = 0x01
   GAME_RESULT        = 0x02
   IP_UPDATE          = 0x04

class ResultType(Enum):
   ##                      x T P p c d
   FULL = ord('~')    ## 0b1 1 1 1 1 10 ## 18 traced ip,port, reported ip,port, private ip,port
   PARTIAL = ord('w') ## 0b1 1 1 0 1 11 ## 12 traced ip,port, reported ip,port
   HUNNHH = ord('\\') ## 0b1 0 1 1 1 00 ## 10 some ip, port, ip (search Twinblade) ips look like public/traced
   MINIMAL = ord('U') ## 0b1 0 1 0 1 01 ##  6 reported public ip,port follows
   ## (there could be more)
   ## this is prly a bitfield not an enum...

class HeartbeatMaster(DatagramProtocol):
   '''
   This fulfills the role of both redalert3pc.available.gamespy.com and redalert3pc.master.gamespy.com.
   Both of these real DNS addrs point to the same master.gamespy.com currently.

   I think the two master servs are separate in order to save
   bandwidth and CPU usage by running the heartbeat service as UDP. heartbeat packets can get dropped too.
   '''
   def datagramReceived(self, data, (host, port)):
      self.log = getLogger('gamespy.heartbeatMaster', host=host, port=port)
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
            self.log.debug('weird msg from {0}:{1} clientid={2} data={3}'.format(host, port, clientId, repr(data)))
            session = MasterGameSession.objects.get(clientId=clientId)
         else:
            try:
               ## HACK: grab old instance, if it exists
               session = MasterGameSession.objects.get(hostname=info['hostname'])
               session.clientId = clientId
            except MasterGameSession.DoesNotExist, ex:
               ## create new session
               session = MasterGameSession.objects.create(hostname=info['hostname'], clientId=clientId, channel=Channel.objects.get(id=info['groupid']))

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
   def connectionMade(self):
      ProxyClient.connectionMade(self)
      self.log = getLogger('gamespy.masterCli', self)

   def dataReceived(self, data):
      dec = self.peer.decoder.Decode(data)
      if dec:
         self.log.debug('decoded: '+ repr(dec))
         ''' print out ips embedded in msg
         if '~' in dec:
            tokens = dec.split(chr(ResultType.FULL))
            for sub in tokens[1:]:
               if len(sub) >= 16:
                  self.log.debug('ips: {0}'.format([inet_ntoa(x) for x in [sub[:4], sub[6:][:4], sub[12:][:4]]]))
         '''
      ProxyClient.dataReceived(self, data)

class ProxyMasterClientFactory(ProxyClientFactory):
   protocol = ProxyMasterClient

class ProxyMasterServer(ProxyServer):
   clientProtocolFactory = ProxyMasterClientFactory

   def connectionMade(self):
      ProxyServer.connectionMade(self)
      self.log = getLogger('gamespy.masterSrv', self)

   def dataReceived(self, data):
      self.log.debug('received: '+repr(data))
      ProxyServer.dataReceived(self, data)
      # everytime a request goes out, re-init the decoder
      validate = data[9:].split('\0')[2][:8]
      self.decoder = self.factory.cipherFactory.getMasterCipher(validate)

class ProxyMasterServerFactory(ProxyFactory):
   protocol = ProxyMasterServer

   def __init__(self, gameName, host, port):
      ProxyFactory.__init__(self, host, port)
      self.cipherFactory = CipherFactory(gameName)

def makeRecv(superClass, xor=False):
   def recv(self, data):
      self.log.debug('received: {0}'.format([x.data for x in parseMsgs(data, xor)]))
      superClass.dataReceived(self, data)
   return recv

def recvMasterCli(self, data):
   self.log.debug('received: {0}'.format(data))
   ProxyClient.dataReceived(self, data)

def recvMasterSrv(self, data):
   self.log.debug('received: {0}'.format(data))
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
   def connectionMade(self):
      Protocol.connectionMade(self)
      self.log = getLogger('gamespy.master', self)

   def dataReceived(self, data):
      # first 8 are binary with some nulls, so have to skip those manually before splitting
      msg = QueryMasterMessage.getMessage(data)
      #self.log.debug('received: {0}'.format(m))
      self.log.debug('received: request={0}'.format(msg['request']))
      self.handleRequest(msg)

   def sendMsg(self, msg):
      self.log.debug('sent: {0}'.format(repr(msg)))
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
      match = re.match(r'\(groupid=(.*?)\)', msg['request'])
      ep = self.transport.getPeer()
      response = inet_aton(ep.host) + struct.pack('!H', ep.port)
      response += self.makeFieldList([(f, 0) for f in msg['fields']])
      ## TODO: dynamically determine whether to use these and pick fields dynamically
      ## to do this, do select top 5 distinct col or something to find most frequent values among col
      response += '\0' ## TODO : use vals list
      if match:
         groupId = match.group(1)
         for session in MasterGameSession.objects.filter(channel__id=groupId):
            ## prune any stale entries that have had no updates for 2 mins
            if session.updated < datetime.now() - timedelta(minutes=2):
               session.delete()
               continue

            ## Use first class C ip as the local ip. This rule is guessed, but seems to always work.
            for ndx in range(4):
               localIp = getattr(session, 'localip{0}'.format(ndx))
               if localIp.startswith('192.168.') or localIp.startswith('10.'):
                  #print('selecting', localIp)
                  break
            ## This first part of a gamelobby entry is used to create the room name's hash.
            ## room name hash is based off of publicip, localip reported here (maybe ports too?)
            response += (chr(ResultType.FULL)
               ## game channel name is based off of some or all of this info!
               ## TODO: RE that hash

               + inet_aton(session.publicip)
               + struct.pack('!H', session.publicport)
               + inet_aton(localIp)
               + struct.pack('!H', session.localport)
               ## This 3rd ip is the the host farthest along the route.
               ## When all the hosts respond along the route, it's the same as the public ip.
               ## I don't know how/if this is actually used by the game.
               ## TODO: do a traceroute on publicip and put the farthest reachable host here
               + inet_aton(session.publicip)
             )
            #print('public={0} private={1}'.format((session.publicip, session.publicport), (localIp, session.localport)))
            response += ''.join('\xff{0}\x00'.format(getattr(session, f.rstrip('_'))) for f in msg['fields'])
         response += '\x00'
         response += '\xff'*4 ## terminator for first part of the response
         self.sendMsg(response)
         ## once this first response is sent, this server can continue to send
         ## results one-by-one. To do this, it first sends a hdr msg in the format of:
         ##   len of whole msg(BE-short),0x01,makeFieldList()-type list (this list always has more fields in it)

         ## This list is more complete than the one sent initially.
         ## These fields will be present in the GAME_ENTRY messages that
         ## are to follow.
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
         response = chr(ResponseType.VALUE_MAP) + self.makeFieldList([(f,0) for f in fields])
         response = struct.pack('!H', len(response) + 2) + response
         self.sendMsg(response)

         ## then entries in format:
         ##   BE-shortlen of whole msg,0x02,regular entry starting with '~...'
         ## these update lines must embed all strings (val list cannot be used as in first response)
         ##    -- embed state of values in field list seem to be ignored
         ## 02 short format is:
         ## 'w', lasttraced ip, port, privateip, privport, all fields in short form (byte values, nulls, or null-term'ed strings)
         ## 'U', publicip, publicport, all fields as above...
         ## these must be succeded with IP_UPDATE messeages
         for session in MasterGameSession.objects.filter(channel__id=groupId):
            ## TODO: merge with above into func
            response = (
               chr(ResponseType.GAME_RESULT)
               + chr(ResultType.FULL)
               + inet_aton(session.publicip)
               + struct.pack('!H', session.publicport)
               + inet_aton(localIp)
               + struct.pack('!H', session.localport)
               + inet_aton(session.publicip)
             )
            for field in fields:
               val = getattr(session, field)
               if type(val) in [int, long, type(None)]:
                  response += struct.pack('B', int(val or 0))
               elif type(val) in [str, unicode]:
                  response += str(val) + '\x00'
            response = struct.pack('!H', len(response) + 2) + response
            self.sendMsg(response)

         ''' should be done this way:
         with LoopingCall:
            result = getNextResult()
            result.addCallback(sendResult)

         .stop() call when new request comes in
         '''
         ## for now, just send what we currently have.

         ## msg type 0x04, it updates the missing ips of a game retrived by msg type 0x02 -- BElen,0x04,ip,port
         ## IP_UPDATE messages are for updating the farthest traced address the master server has reached as
         ## it proceeds. It corresponds to the last GAME_RESULT entry returned. Once the traced IP+port == reported ip+port,
         ## the client has enough info on that game and no longer needs these updates.
         ## TODO: Until tracerouting is implemented (I think it's only very rarely useful, so no time soon), These messages never
         ## need to be sent. Likewise, only ResultType.FULL need be returned in the first place.
         '''
         for ep in epList:
            response = chr(ResponseType.IP_UPDATE) + ep
            response = struct.pack('!H', len(response) + 2) + response
            self.sendMsg(response)
         '''

         ##TODO:dunno if real servs do this
         #self.transport.loseConnection()


   def handle_getRooms(self, msg):
      channels = Channel.objects.filter(game__name=self.factory.gameName, name__startswith='gpg')
      ep = self.transport.getPeer()
      self.sendMsg(
         inet_aton(ep.host)
         ## this is normally the peer's port (unneeded for room listing in gamespy's opinion, i guess)
         #+ struct.pack('!H', ep.port) ## this always 0 in real msgs
         + struct.pack('!H', 0)
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

## these aspects are kind of sloppy. Before, I was wrapping self.transport.write
## from within a wrapped connectionMade, but the problem was I was getting stack
## overflows because the wraps were never peeled back off. I tried adding this in,
## but got exceptions whenever I tried to peel off the last wrap. I figured it's better
## to only wrap once, anyway, so now I'm wrapping Server.write since that's what's
## always used as self.transport it seems.
@aspects.Aspect(Server)
class QueryMasterTransportEncryption(object):
   def write(self, bytes):
      ## TLS connections don't have the protocol attribute
      if hasattr(self, 'protocol') and isinstance(self.protocol, QueryMaster):
         bytes = (
            # first byte ^ 0xec is hdr content length, second ^ 0xea is salt length
            struct.pack('!BxxB', 0xEC ^ 2, 0xEA ^ len(self.protocol.cipher.salt)) # 0 len hdr works too...
            + self.protocol.cipher.salt.tostring()
            + self.protocol.cipher.encrypt(bytes)
         )
      yield aspects.proceed(self, bytes)

@aspects.Aspect(QueryMaster)
class QueryMasterEncryption(object):
   def dataReceived(self, data):
      # everytime a request comes in, re-init the cipher
      msg = QueryMasterMessage.getMessage(data)
      self.cipher = CipherFactory(self.factory.gameName).getMasterCipher(msg['validate'])
      yield aspects.proceed


# key server runs on udp port 29910 and accepts the following datagrams, xored with repeated string 'gamespy' (restarts at beginning of word every datagram):
# '\\ka\\'
# '\\auth\\\\pid\\3210\\ch\\ulgdjfnqgigyswtgnzcewpyoscwckhst\\resp\\86b626aaa89482d1a78fc9de7dc6f69f4a34604a0535c29ef94f148c167fdc9e10dad860\\ip\\1647773464\\skey\\917\\reqproof\\1\\'
# (those two typically form the request) the reply can be any of the following:
# '\\unok\\\\cd\\86b626aaa89482d1a78fc9de7dc6f69f\\skey\\917\\errmsg\\Your CD Key is disabled. Contact customer service.'
# see Luigi Auriemma's gskeycheck.c for reference on hash composition
