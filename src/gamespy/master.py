import logging
import re
import struct
from socket import inet_aton, inet_ntoa

from twisted.internet.protocol import Protocol
from twisted.protocols.portforward import *

import db
from cipher import CipherFactory

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
      self.decoder = self.factory.cipherFactory.getMasterCipher(validate)
      self.factory.log.debug('received: '+repr(data))
      ProxyServer.dataReceived(self, data)

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
class MasterServer(Protocol):
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
      ## TODO: dynamically determine whether to use these and pick fields dynamically
      immediateValueKeys = [
         'pw',
         'obs',
         'numRPlyr',
         'maxRPlyr',
         'numObs',
      ]
      match = re.match(r'\(groupid=(.*?)\)', msg['request'])
      ep = self.transport.getPeer()
      response = inet_aton(ep.host) + struct.pack('!H', ep.port)
      response += self.makeFieldList([(f, 0) for f in msg['fields']])
      response += '\0' ## TODO : use vals list
      if match:
         groupId = match.group(1)
         for session in db.MasterGameSession.objects.filter(channel__id=groupId):
            response += '~\x18\xed\xc7\xa2\x19g\xc0\xa8\x01\x03\x19g\xd1\xa5\x80\x05' #TODO
            response += ''.join('\xff{0}\x00'.format(getattr(session, f.rstrip('_'))) for f in msg['fields'])
         response += '\x00'
         response += '\xff'*4
         self.sendMsg(response)

   def _static_handle_getGames(self, msg):
      ## request:
      ## msg tags
      "\x00\xd9\x00\x01\x03\x00\x00\x01\x00redalert3pc\x00redalert3pc\x00f99.qM3$"
      ## request
      "(groupid=2167) AND (gamemode != 'closedplaying')\x00"
      ## fieldlist
      '\\hostname\\gamemode\\hostname\\mapname\\gamemode\\vCRC\\iCRC\\cCRC\\pw\\obs\\rules\\pings\\numRPlyr\\maxRPlyr\\numObs\\mID\\mod\\modv\\name_\x00'
      '\x00\x00\x00\x04' # big endian 4?

      ## in here, 0 signifies the value is a reference, 1 means it is a literal byte
      ## references can be replace with immediate values in the form of \xffa_string_you_want\x00
      fields = (
         ('hostname', 0),
         ('gamemode', 0),
         # TODO: why are these duped?
         ('hostname', 0),
         ('mapname', 0),
         ('gamemode', 0),
         ('vCRC', 0),
         ('iCRC', 0),
         ('cCRC', 0),
         ('pw', 0),
         ('obs', 0),
         ('rules', 0),
         ('pings', 0),
         ('numRPlyr', 0),
         ('maxRPlyr', 0),
         ('numObs', 0),
         ('mID', 0),
         ('mod', 0),
         ('modv', 0),
         ('name_', 0),
      )
      ep = self.transport.getPeer()
      self.sendMsg(
      inet_aton(ep.host) + struct.pack('!H', ep.port)
      + self.makeFieldList(fields) +
      '\0' # val list goes here normally
      #'~'
      #'c\xf3\xc1\\\x1a&'
      #'\xc0\xa8'
      #'\x00\xc2\x1a&E?\xf3\x1a'
      #'\xffTheHoster gameTitle\x00'
      #'\x0e\xffTheHoster2 gameTitle2\x00'
      #'\x1b'
      #'\x0e\x14\x01\x1f\x05\x06\x11\x00'
      #'\t\t'
      #'\x05\x00\x17\x05\x00'

      '~' ## start of game entry
      '\x18\xed\xc7\xa2\x19g'
      '\xc0\xa8'
      '\x01\x03\x19g\xd1\xa5\x80\x05'
      '\xffpseudo FakeGame\x00' ## hostname
      '\xffopenstaging\0' ## gamemode
      '\xffpseudo FakeGame\x00' ## hostname
      '\xffdata/maps/official/map_mp_3_feasel3/map_mp_3_feasel3.map\x00' ## mapname
      '\xffopenstaging\0' ## gamemode
      '\xff1.12.3444.25830\0' # vCRC
      '\xff-117165505\0' # iCRC
      '\xff251715600\0' # cCRC
      '\xff5\0' # pw
      '\xff6\0' # obs
      '\xff3 100 10000 0 1 10 0 1 0 -1 0 -1 -1 1 \0' # rules
      '\xff#\0' # pings
      '\xff10\0' ## numRPlyr always(?) mirrors next byte - maybe one val is # open, one total #
      '\xff10\0' ## maxRPlyr number of total slots for this game lobby
      '\xff2\0' ## numObs zero-based index of next open slot (i.e., numplayers-1) -- maybe no index since middle slots can be closed
      '\xff#\x00' # mID
      '\xffRA3\0' # mod
      '\xff0\x00' # modv
      '\xff#\xff' # name_

      '\x00' # extra null at end?
      '\xff\xff\xff\xff' # msg terminator?
      )

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



   def handle_getRooms(self, msg):
      nums = [ # TODO -- what are these??
         '500', '0', '1', '2', '3', '4', '5', '6', '7', '8', '71', '9', '77', '10', '11', '12', '13', '14', '15',
          '16', '250', '150', '20', '22', '24', '37', '200', '100', '50', '56', '60', '1000',
      ]
      channels = db.Channel.objects.filter(game__name=self.factory.gameName, name__startswith='#GPG')
      self.sendMsg(
      '\x18\x07yO' # IP
      '\x00\x00' + self.makeFieldList((
         ('hostname', 0),
         ('numwaiting', 0),
         ('maxwaiting', 0),
         ('numservers', 0),
         ('numplayers', 1),
         ('roomType', 0),
      ))
      + struct.pack('B', len(nums)) + '\0'.join(nums) + '\0'
      # end part of entry seems to be like this:
      # name,null,  (0x1-3 or 0xff,asciinums,null), 0x15,
      + ''.join(
                '@{0}' # room id
                '\xff{1}\x00' ##hostname (room name)
                '\xff98\x00' ##numwaiting
                '\x15' ## maxwaiting
                '\xff36\x00' ## numservers
                '\x89' ## numplayers
                '\x02' ## roomtype
                #'\x03\x15\x03\x07\x02'
                .format(struct.pack('!L', c.id), c.prettyName) for c in channels) +
      #'@\x00\x00\x08v\xffLobbyRoom:1\x00\xff98\x00\x15\xff36\x00\x89\x02'
      # TODO:
      # how does the channel:number notation work??
      # what are values of roomtype enum
      #'@\x00\x00\x08\x87\xffLobbyRoom:10\x00\x03\x15\x03\x07\x02'
      #'@\x00\x00\t)\xffLobbyCoop:2\x00\x01\x15\x01\x00\x02'
      #'@\x00\x00\t(\xffLobbyCoop:1\x00\x03\x15\x03\x03\x02'
      #'@\x00\x00\t+\xffLobbyCoop:4\x00\x03\x15\x01\x00\x02'
      #'@\x00\x00\t-\xffLobbyRussian:1\x00\x02\x15\x01\x00\x02'
      '\x00\xff\xff\xff\xff'
      )
