import logging
import re
import base64
import struct
from socket import inet_aton, inet_ntoa

from twisted.internet.protocol import Protocol, DatagramProtocol
from twisted.protocols.portforward import *

import db
from enum import Enum
from cipher import CipherFactory

class MasterMsg(Enum):
   CHALLENGE_RESPONSE = 1
   HEARTBEAT = 3
   KEEPALIVE = 8
   AVAILABLE = 9

class HeartbeatMaster(DatagramProtocol):
   '''
   This fulfills the role of both redalert3pc.available.gamespy.com and redalert3pc.master.gamespy.com.
   Both of these real DNS addrs point to the same master.gamespy.com currently.

   I think the two master servs are separate in order to save
   bandwidth and CPU usage by running the heartbeat service as UDP. heartbeat packets can get dropped too.
   '''
   log = logging.getLogger('gamespy.superMaster')

   def datagramReceived(self, data, (host, port)):
      msgId, clientId, body = ord(data[0]), data[1:][:4], data[5:]
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

         self.log.debug('recv: {0}'.format(repr(data)))
         self.log.debug('info: {0}'.format(repr(info)))
         self.log.debug('rem: {0}'.format(repr(remainder)))
         if info['publicip'] == '0':
            cFact = CipherFactory(info['gamename'])
            chall = cFact.getHeartbeatCipher().salt
            self.sendMsg(
               '\xfe\xfd\x01' + clientId + chall + base64.b16encode('\x00' + inet_aton(host) + struct.pack('!H',  port)) + '\0',
               (host, port)
            )
         ## TODO: better way to do this? i want to just do session.update(info)
         session = db.MasterGameSession.objects.get_or_create(channel=db.Channel.objects.get(id=info['groupid']), hostname=info['hostname'])[0]
         for k, v in info.iteritems():
            setattr(session, k, v)
         session.save()

      elif msgId == MasterMsg.CHALLENGE_RESPONSE:
         self.log.debug('recv: {0}'.format(repr(data)))
         self.log.debug('TODO: chall resp')
      elif msgId == MasterMsg.KEEPALIVE:
         self.log.debug('recv: {0}'.format(repr(data)))
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


# HACK, TODO: right now this depends on the factory having a gameName attr, see also Proxy verison above
class QueryMaster(Protocol):
   def dataReceived(self, data):
      # first 8 are binary with some nulls, so have to skip those manually before splitting
      m = {}
      (m['length'], m['headerRemainder']), data = struct.unpack('!H6s', data[:8]), data[9:] # 8, 9 skip the null in between
      m['gameName'], m['gameName2'], data = data.split('\0', 2)
      m['validate'], (m['request'], m['fields'], m['tail']) = data[:8], data[8:].lstrip('\0').split('\0', 2) # sometimes theres a preceding null, sometimes not?? :P
      m['fields'] = m['fields'].split('\\')[1:]
      #self.factory.log.debug('received: {0}'.format(m))
      self.factory.log.debug('received: request={0}'.format(m['request']))

      # everytime a request comes in, re-init the cipher
      self.cipher = CipherFactory(self.factory.gameName).getMasterCipher(m['validate'])
      self.handleRequest(m)

   def sendMsg(self, msg):
      self.factory.log.debug('sent: {0}'.format(repr(msg)))
      data = ( # TODO: move me into another class
         # first byte ^ 0xec is hdr content length, second ^ 0xea is salt length
         struct.pack('!BxxB', 0xEC ^ 2, 0xEA ^ len(self.cipher.salt)) # 0 len hdr works too...
         + self.cipher.salt.tostring()
         + self.cipher.encrypt(msg)
      )
      self.transport.write(data)

   def handleRequest(self, msg):
      # HACK, TODO: do this more intelligently
      if msg['request'].startswith('\\hostname'):
         self.handle_getRooms(msg)
      elif msg['request'].startswith('(groupid'):
         self.handle_getGames(msg)

   def makeFieldList(self, fields):
      '''
      Fields must always be returned in the order requested, so use list of tuples
      for 'fields'.
      '''
      return chr(len(fields)) + ''.join(chr(v)+k+'\0' for k, v in fields)


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

      ## TODO: handle this second query type as well as any others it might throw at
      ## us in the request string and field list: "( blash = val) and (blah2 = val2)"
      fields = (
         ('hostname', 0),
         ('mapname', 0),
         ('numplayers', 1),
         ('maxplayers', 1),
         ('gamemode', 0),
         ('vCRC', 0),
         ('iCRC', 0),
         ('pw', 1), # passworded?
         ('obs', 1),
         ('rules', 0),
         ('pings', 0),
         ('numRPlyr', 1),
         ('maxRPlyr', 1),
         ('numObs', 1),
         ('name', 0),
         ('cCRC', 0),
         ('mID', 0),
         ('mod', 0),
         ('modv', 0),
         ('teamAuto', 1),
         ('joinable', 1),
      )

      data = '\x01' + self.makeFieldList(fields)
      self.sendMsg(struct.pack('!H', len(data)) + data)

      '''
      ## TODO: dynamically determine whether to use these and pick fields dynamically
      ## to do this, do select top 5 distinct col or something to find most frequent values among col
      immediateValueKeys = [
         'pw', ## TODO: pwd is '0' for disabled? what does 5 mean??
         'obs',
         'numRPlyr',
         'maxRPlyr',
         'numObs',
         'teamAuto',
         'joinable',
      ]
      match = re.match(r'\(groupid=(.*?)\)', msg['request'])
      ep = self.transport.getPeer()
      response = inet_aton(ep.host) + struct.pack('!H', ep.port)
      response += self.makeFieldList([(f, 0) for f in msg['fields']])
      response += '\0' ## TODO : use vals list
      if match:
         groupId = match.group(1)
         for session in db.MasterGameSession.objects.filter(channel__id=groupId):
            response += ('~'
               ## game channel name is based off of some or all of this info!
               ## TODO: RE that hash

               + struct.pack('L', session.publicip) ## publicip is already a big endian long, so pack in host order
               + struct.pack('!H', session.publicport)
               ## FIXME?: local host and port determine the channel hash. is there always an ip3? pick highest if there isnt??
               ## this may depend on what the master knows about the client's internal addresses -- it provides  the first that matches?
               + inet_aton(session.localip1)
               + struct.pack('!H', session.localport)
               + struct.pack('L', session.publicip) ##  some other related external ip -- sometimes dupe of external
             )
            #response += '~\x18\xed\xc7\xa2\x19g\xc0\xa8\x01\x03\x19g\xd1\xa5\x80\x05' #TODO
            #response += '~c\xf3\xc1\\\x1a&\xc0\xa8\x00\xc2\x1a&E?\xf3\x1a'
            response += ''.join('\xff{0}\x00'.format(getattr(session, f.rstrip('_'))) for f in msg['fields'])
         response += '\x00'
         response += '\xff'*4
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
         # end part of entry seems to be like this:
         # name,null,  (0x1-3 or 0xff,asciinums,null), 0x15,
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
                   '\x00' ## numplayers
                   '\xff1\x00' ## roomtype
                   #'\x03\x15\x03\x07\x02'
                   .format(struct.pack('!L', c.id), c.prettyName) for c in channels) +
         '\x00\xff\xff\xff\xff'
      )
