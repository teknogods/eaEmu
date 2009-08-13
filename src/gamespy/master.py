import logging
import struct

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
      m['validate'], (m['request'], m['bodyRemainder']) = data[:8], data[8:].lstrip('\0').split('\0', 1) # sometimes theres a preceding null, sometimes not?? :P
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
      2009-07-27 22:32:55,703 - gamespy.masterSrv - received: "\x00\xd9\x00\x01\x03\x00\x00\x01\x00redalert3pc\x00redalert3pc\x00f99.qM3$(groupid=2167) AND (gamemode != 'closedplaying')\x00\\hostname\\gamemode\\hostname\\mapname\\gamemode\\vCRC\\iCRC\\cCRC\\pw\\obs\\rules\\pings\\numRPlyr\\maxRPlyr\\numObs\\mID\\mod\\modv\\name_\x00\x00\x00\x00\x04"
      2009-07-27 22:32:55,823 - gamespy.masterCli - decoded: '\x18\x07yO\x19d\x13\x00hostname\x00\x00gamemode\x00\x00hostname\x00\x00mapname\x00\x00gamemode\x00\x00vCRC\x00\x00iCRC\x00\x00cCRC\x00\x00pw\x00\x00obs\x00\x00rules\x00\x00pings\x00\x00numRPlyr\x00\x00maxRPlyr\x00\x00numObs\x00\x00mID\x00\x00mod\x00\x00modv\x00\x00name_\x00#\x00-117165505\x000 100 10000 0 0 10 0 1 1 -1 0 -1 1 0 \x000 100 10000 0 0 10 0 1 1 -1 0 -1 1 1 \x000 100 10000 0 0 10 0 1 1 -1 0 -1 1 2 \x000\x001\x002\x003\x004\x005\x006\x00data/maps/official/map_mp_6_feasel3/map_mp_6_feasel3.map\x00data/maps/official/camp_a07_tokyoharbor_davis/camp_a07_tokyoharbor_davis.map\x00openstaging\x00data/maps/official/map_mp_4_feasel3/map_mp_4_feasel3.map\x00data/maps/official/map_mp_6_ssmith2/map_mp_6_ssmith2.map\x003 100 10000 0 1 10 0 1 0 -1 0 -1 -1 1 \x003 100 40000 0 1 10 1 1 0 -1 0 -1 -1 1 \x00data/maps/official/map_mp_2_feasel4/map_mp_2_feasel4.map\x001.12.3444.25830\x00data/maps/official/map_mp_4_feasel6/map_mp_4_feasel6.map\x00data/maps/official/camp_s08_easterisland_stewart/camp_s08_easterisland_stewart.map\x00RA3\x00data/maps/official/camp_s06_iceland_bass/camp_s06_iceland_bass.map\x00data/maps/official/map_mp_6_feasel1/map_mp_6_feasel1.map\x000 100 10000 0 0 10 0 1 1 -1 0 -1 0 1 \x00data/maps/official/map_mp_4_black_xslice/map_mp_4_black_xslice.map\x00data/maps/official/camp_s09_newyork_rao/camp_s09_newyork_rao.map\x00data/maps/official/camp_s04_geneva_bass/camp_s04_geneva_bass.map\x00data/maps/official/map_mp_2_rao1/map_mp_2_rao1.map\x00251715600\x00data/maps/internal/tower_defence_v2.0_moded_by_joker/tower_defence_v2.0_moded_by_joker.map\x00data/maps/official/map_mp_6_feasel4/map_mp_6_feasel4.map\x00closedplaying\x00~c\xf3\xc1\\\x1a&\xc0\xa8\x00\xc2\x1a&E?\xf3\x1a\xffwongjac7 2v2 lets goooo!\x00\x0e\xffwongjac7 2v2 lets goooo!\x00\x1b\x0e\x14\x01\x1f\x05\x06\x11\x00\t\t\x05\x00\x17\x05\x00~\x18\xed\xc7\xa2\x19g\xc0\xa8\x01\x03\x19g\xd1\xa5\x80\x05\xffStormBringer13 jake\x00\x0e\xffStormBringer13 jake\x00\xffdata/maps/official/map_mp_3_feasel3/map_mp_3_feasel3.map\x00\x0e\x14\x01\x1f\x05\x06\x11\x00\x08\x08\x05\x00\x17\x05\x00\x00\xff\xff\xff\xff'
      2009-07-27 22:32:55,831 - gamespy.masterCli - decoded: '\x00\xa8\x01\x15\x00hostname\x00\x00mapname\x00\x01numplayers\x00\x01maxplayers\x00\x00gamemode\x00\x00vCRC\x00\x00iCRC\x00\x01pw\x00\x01obs\x00\x00rules\x00\x00pings\x00\x01numRPlyr\x00\x01maxRPlyr\x00\x01numObs\x00\x00name\x00\x00cCRC\x00\x00mID\x00\x00mod\x00\x00modv\x00\x01teamAuto\x00\x01joinable\x00'
      2009-07-27 22:32:56,200 - gamespy.chatCli - received: ':s 324 elitak #GPG!2167 +tnp \n'
      '''
      
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
         ('pw', 1),
         ('obs', 1),
         ('rules', 0),
         ('pings', 0),
         ('numRPlyr', 1),
         ('maxRPlyr', 1),
         ('numObs', 1),
         ('mID', 0),
         ('mod', 0),
         ('modv', 0),
         ('name_', 0),
      )
      self.sendMsg(
      '\x18\x07yO'
      '\x19d'
      + self.makeFieldList(fields) +
      '#\x00'
      '-117165505\x00'
      '0 100 10000 0 0 10 0 1 1 -1 0 -1 1 0 \x00'
      '0 100 10000 0 0 10 0 1 1 -1 0 -1 1 1 \x00'
      '0 100 10000 0 0 10 0 1 1 -1 0 -1 1 2 \x00'
      +'\0'.join(('0', '1', '2', '3', '4', '5', '6'))+'\0'
      'data/maps/official/map_mp_6_feasel3/map_mp_6_feasel3.map\x00'
      'data/maps/official/camp_a07_tokyoharbor_davis/camp_a07_tokyoharbor_davis.map\x00'
      'openstaging\x00'
      'data/maps/official/map_mp_4_feasel3/map_mp_4_feasel3.map\x00'
      'data/maps/official/map_mp_6_ssmith2/map_mp_6_ssmith2.map\x00'
      '3 100 10000 0 1 10 0 1 0 -1 0 -1 -1 1 \x00'
      '3 100 40000 0 1 10 1 1 0 -1 0 -1 -1 1 \x00'
      'data/maps/official/map_mp_2_feasel4/map_mp_2_feasel4.map\x00'
      '1.12.3444.25830\x00' # gameVer
      'data/maps/official/map_mp_4_feasel6/map_mp_4_feasel6.map\x00'
      'data/maps/official/camp_s08_easterisland_stewart/camp_s08_easterisland_stewart.map\x00'
      'RA3\x00data/maps/official/camp_s06_iceland_bass/camp_s06_iceland_bass.map\x00'
      'data/maps/official/map_mp_6_feasel1/map_mp_6_feasel1.map\x00'
      '0 100 10000 0 0 10 0 1 1 -1 0 -1 0 1 \x00'
      'data/maps/official/map_mp_4_black_xslice/map_mp_4_black_xslice.map\x00'
      'data/maps/official/camp_s09_newyork_rao/camp_s09_newyork_rao.map\x00'
      'data/maps/official/camp_s04_geneva_bass/camp_s04_geneva_bass.map\x00'
      'data/maps/official/map_mp_2_rao1/map_mp_2_rao1.map\x00251715600\x00'
      'data/maps/internal/tower_defence_v2.0_moded_by_joker/tower_defence_v2.0_moded_by_joker.map\x00'
      'data/maps/official/map_mp_6_feasel4/map_mp_6_feasel4.map\x00'
      'closedplaying\x00'
      '~c\xf3\xc1\\\x1a&\xc0\xa8\x00\xc2\x1a&E?\xf3\x1a\xff'
      'wongjac7 2v2 lets goooo!\x00'
      '\x0e\xffwongjac7 2v2 lets goooo!\x00'
      '\x1b\x0e\x14\x01\x1f\x05\x06\x11\x00\t\t\x05\x00\x17\x05\x00~\x18\xed\xc7\xa2\x19g\xc0\xa8\x01\x03\x19g\xd1\xa5\x80\x05\xff'
      'StormBringer13 jake\x00'
      '\x0e\xffStormBringer13 jake\x00\xff'
      'data/maps/official/map_mp_3_feasel3/map_mp_3_feasel3.map\x00'
      '\x0e\x14\x01\x1f\x05\x06\x11\x00\x08\x08\x05\x00\x17\x05\x00\x00\xff\xff\xff\xff'
      )
      
      fields = (
         ('hostname', 0),
         ('mapname', 0),
         ('numplayers', 1),
         ('maxplayers', 1),
         ('gamemode', 0),
         ('vCRC', 0),
         ('iCRC', 0),
         ('pw', 1),
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
      '\x18\x07yO'
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
      + ''.join('@{0}\xff{1}\x00'
                '\xff98\x00'
                '\x15'
                '\xff36\x00'
                '\x89\x02'
                #'\x03\x15\x03\x07\x02'
                .format(struct.pack('!L', c.id), c.prettyName) for c in channels) +
      #'@\x00\x00\x08v\xffLobbyRoom:1\x00\xff98\x00\x15\xff36\x00\x89\x02' 
      # TODO: figure out what 5 unknown bytes (last is always 0x02) represent
      # -maybe chanflags, or fields that were queried(first line)?
      # also, how does the channel:number notation work??
      # what are \xffnumnum for?
      #'@\x00\x00\x08\x87\xffLobbyRoom:10\x00\x03\x15\x03\x07\x02'
      #'@\x00\x00\t)\xffLobbyCoop:2\x00\x01\x15\x01\x00\x02'
      #'@\x00\x00\t(\xffLobbyCoop:1\x00\x03\x15\x03\x03\x02'
      #'@\x00\x00\t+\xffLobbyCoop:4\x00\x03\x15\x01\x00\x02'
      #'@\x00\x00\t-\xffLobbyRussian:1\x00\x02\x15\x01\x00\x02'
      #'@\x00\x00\x08~\xffLobbyGerman:1\x00\x02\x15\x03\x04\x02'
      #'@\x00\x00\x08\x81\xffChatRoom1\x00\x02\x15\x01\x00\x02'
      #'@\x00\x00\t*\xffLobbyCoop:3\x00\x01\x15\x01\x00\x02'
      #'@\x00\x00\x08\x80\xffLobbyRoom:6\x00\x03\x15\x01\x00\x02'
      #'@\x00\x00\x08\x93\xffLobbyCustomMap:2\x00\x07\x15\x03\x04\x02'
      #'@\x00\x00\x08}\xffLobbyGerman:2\x00\x03\x15\x02\x02\x02'
      #'@\x00\x00\x08\x96\xffChatRoom1\x00\x01\x15\x01\x00\x03'
      #'@\x00\x00\x08\x8e\xffLobbyBeginners:1\x00\x05\x15\x03\x04\x02'
      #'@\x00\x00\x08\x88\xffLobbyClan:1\x00\x03\x15\x01\x00\x02'
      #'@\x00\x00\x08z\xffLobbyRoom:5\x00\xff65\x00\x15\x0b\x11\x02'
      #'@\x00\x00\x08\x85\xffLobbyRoom:9\x00\x01\x15\x01\x00\x02'
      #'@\x00\x00\x08\x86\xffLobbyRoom:12\x00\x01\x15\x01\x00\x02'
      #'@\x00\x00\x08y\xffLobbyRoom:4\x00\n\x15\x13!\x02'
      #'@\x00\x00\x08\x8a\xffLobbyClan:2\x00\x01\x15\x01\x00\x02'
      #'@\x00\x00\x08\x8f\xffLobbyTournaments:1\x00\x03\x15\x01\x00\x02'
      #'@\x00\x00\x08x\xffLobbyRoom:3\x00\xff76\x00\x15\x12\x1e\x02'
      #'@\x00\x00\x08\x94\xffLobbyTournaments:2\x00\x02\x15\x02\x02\x02'
      #'@\x00\x00\x08\x8d\xffLobbyRoom:15\x00\x02\x15\x01\x00\x02'
      #'@\x00\x00\x08\x89\xffLobbyRoom:13\x00\x01\x15\x01\x00\x02'
      #'@\x00\x00\x08\x92\xffLobbyCustomMap:1\x00\x05\x15\x02\x02\x02'
      #'@\x00\x00\x08v\xffLobbyRoom:1\x00\xff98\x00\x15\xff36\x00\x89\x02' # ??? ff's here mean what?
      #'@\x00\x00\x08\x90\xffLobbyCompStomp:1\x00\x01\x15\x01\x00\x02'
      #'@\x00\x00\t%\xffLobbyRoom:19\x00\x01\x15\x01\x00\x02'
      #'@\x00\x00\x08\x8c\xffLobbyRoom:16\x00\x02\x15\x03\x03\x02'
      #'@\x00\x00\t&\xffLobbyRoom:20\x00\x01\x15\x01\x00\x02'
      #'@\x00\x00\x08w\xffLobbyRoom:2\x00\xff72\x00\x15\xff26\x00C\x02'
      #'@\x00\x00\x08\x91\xffLobbyHardcore:1\x00\x02\x15\x02\x02\x02'
      #'@\x00\x00\t\'\xffLobbyRoom:21\x00\x03\x15\x01\x00\x02'
      #'@\x00\x00\t#\xffLobbyRoom:17\x00\x01\x15\x01\x00\x02'
      #'@\x00\x00\t.\xffLobbyTaiwan:1\x00\x02\x15\x02\x02\x02'
      #'@\x00\x00\t$\xffLobbyRoom:18\x00\x01\x15\x01\x00\x02'
      #'@\x00\x00\t5\xffLobbySpanish:1\x00\x02\x15\x02\x04\x02'
      #'@\x00\x00\x08{\xffLobbyKorean:1\x00\xff35\x00\x15\x06\x0b\x02'
      #'@\x00\x00\x08\x8b\xffLobbyRoom:14\x00\x01\x15\x01\x00\x02'
      #'@\x00\x00\x08\x7f\xffLobbyBattlecast:1\x00\x01\x15\x01\x00\x02'
      #'@\x00\x00\x08|\xffLobbyFrench:1\x00\x10\x15\x05\x0c\x02'
      #'@\x00\x00\x08\x84\xffLobbyRoom:7\x00\x01\x15\x02\x02\x02'
      #'@\x00\x00\t,\xffLobbyCoop:5\x00\x01\x15\x01\x00\x02'
      #'@\x00\x00\x08\x82\xffLobbyRoom:8\x00\x01\x15\x01\x00\x02'
      #'@\x00\x00\x08\x83\xffLobbyRoom:11\x00\x01\x15\x01\x00\x02'
      '\x00\xff\xff\xff\xff'
      )
