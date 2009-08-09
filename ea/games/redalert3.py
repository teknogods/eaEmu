import logging
import base64
import time

from twisted.application.internet import SSLServer, TCPServer, UDPServer
from twisted.internet.protocol import ServerFactory
from twisted.application.service import MultiService

import gamespy
from ea.login import *
from ea.db import *

# TODO: move to own module, conditional import
from dj.eaEmu.models import Channel, GamespyGame

gameId = 'redalert3pc'
personas = []

class RedAlert3LoginServer(EaServer):
   theater = Theater.objects.get(name='ra3')
   def connectionMade(self):
      EaServer.connectionMade(self)
      self.log = logging.getLogger('login.ra3')
      self.msgFactory = MessageFactory(self.transport, EaLoginMessage)
      self.hlrFactory = MessageHandlerFactory(self, 'ea.games.redalert3.Ra3MsgHlr')
      
class Ra3MsgHlr_Hello(EaMsgHlr_Hello):
   def makeReply(self):
      reply = EaMsgHlr_Hello.makeReply(self)
      reply.map.update({
         'domainPartition.domain':'eagames',
         'domainPartition.subDomain':'CNCRA3',
      })
      return reply

class Ra3MsgHlr_NuLogin(MessageHandler): # TODO this and mercs2 are almost identical, derive this from mercs one
   def makeReply(self):
      # dict:TXN=NuLogin,macAddr=$001bfcb369cb,nuid=xxxxxx,password=xxxxx,returnEncryptedInfo=1
      map = {
         'nuid': self.user.login,
         'userId': self.user.id,
         'profileId': self.user.id, # seems to be always the same as userId
         'lkey':self.server.session.key,
      }
      if int(self.msg.map['returnEncryptedInfo']):
         # the contents of this string are unknown. It may consist of 
         # what's in the other branch.
         # TODO: no clue on how this is encrypted. I bet the last 2 characters
         # end up being '==' because thisVal=encrypt(b64encode(plaintext))
         # The mystery is how does the client decrypt it??
         # See also 'lkey', above. -- Also ends in '.', b64 pad char ;)
         # It's not XORed with a 0x13 if you're wondering.
         
         #map['encryptedLoginInfo'] = 'Ciyvab0tregdVsBtboIpeChe4G6uzC1v5_-SIxmvSLJ82DtYgFUjObjCwJ2gbAnB4mmJn_A_J6tn0swNLggnaFOnewWkbq09MOpvpX-Eu19Ypu3s6gXxJ3CTLLkvB-9UKI6qh-nfrXHs3Ij9FBzMrQ..'
         map['encryptedLoginInfo'] = 'Ciyvab0tregdVsBtboIpeChe4G6uzC1v5_-SIxmvSLKqzcqC65kVfFSAEe3lLoY8ZEGkTOwgFM8xRqUuwICLMyhYLqhtMx2UYCllK0EZUodWU5w3jv7gny_kWfGnA6cKbRtwKAriv2OdJmPGsPDdGQ..'
      else:
         map['displayName'] = self.user.login
         map['entitledGameFeatureWrappers'] = [{
            'gameFeatureId':6014,
            'status':0,
            'message':'',
            'entitlementExpirationDate':'',
            'entitlementExpirationDays':-1,
         }]
      return self.msg.makeReply(map)
         
   def handle(self):
      m = self.msg
      self.user = self.server.session.Login(m.map['nuid'], m.map['password'])
      if self.user:
         self.Reply()
      else:
         # TODO send different reply here
         print 'TODO: user not found or bad pwd'

         
class Ra3MsgHlr_NuGetPersonas(MessageHandler):
   # dict:TXN=NuGetPersonas,namespace=
   def makeReply(self):
      return self.msg.makeReply({
            'personas':personas #HACK TODO
      })
      
class Ra3MsgHlr_NuAddPersona(MessageHandler):
   # dict:TXN=NuGetPersonas,namespace=
   def handle(self):
      # dict:TXN=NuAddPersona,name=PersonaName
      # TODO: haven't captured an actual response to this, but this works
      personas.append(self.msg.map['name']) #HACK TODO
      self.Reply()
      
class Ra3MsgHlr_NuLoginPersona(MessageHandler):
      # dict:TXN=NuLoginPersona,name=xxxxx
   def makeReply(self):
      #'SUeWiB5BVHH_cJooCn4oOAAAKD0.' #only middle part is diff from one returned in NuLogin
      return self.msg.makeReply({
         'lkey':self.server.session.key,
         'profileId':self.user.login,
         'userId':self.user.login,
      })
   def handle(self):
      self.user = User.GetUser(login=self.msg.map['name']) #FIXME: get persona, not user
      self.Reply()
      
class Ra3MsgHlr_NuEntitleGame(MessageHandler):
   # inputs are: 'password', 'nuid', 'key'
   # TODO: don't know what proper response is. This message can only be capture once per valid serial, i guess.
   # error is:  {'errorCode': '181', 'TXN': 'NuEntitleGame', 'errorContainer.[]': '0', 'localizedMessage': '"The code is not valid for registering this game"'}
   pass
   
class Ra3MsgHlr_GetTelemetryToken(MessageHandler):
   # no inputs
   def makeReply(self):
      return self.msg.makeReply({
         # These are all country codes it appears.
         'enabled':'CA,MX,PR,US,VI', #Canada, Mexico, Puerto Rico, United States, Virgin Islands
         'disabled':'AD,AF,AG,AI,AL,AM,AN,AO,AQ,AR,AS,AW,AX,AZ,BA,BB,BD,BF,BH,BI,BJ,BM,BN,BO,BR,BS,BT,BV,BW,BY,BZ,CC,CD,CF,CG,CI,CK,CL,CM,CN,CO,CR,CU,CV,CX,DJ,DM,DO,DZ,EC,EG,EH,ER,ET,FJ,FK,FM,FO,GA,GD,GE,GF,GG,GH,GI,GL,GM,GN,GP,GQ,GS,GT,GU,GW,GY,HM,HN,HT,ID,IL,IM,IN,IO,IQ,IR,IS,JE,JM,JO,KE,KG,KH,KI,KM,KN,KP,KR,KW,KY,KZ,LA,LB,LC,LI,LK,LR,LS,LY,MA,MC,MD,ME,MG,MH,ML,MM,MN,MO,MP,MQ,MR,MS,MU,MV,MW,MY,MZ,NA,NC,NE,NF,NG,NI,NP,NR,NU,OM,PA,PE,PF,PG,PH,PK,PM,PN,PS,PW,PY,QA,RE,RS,RW,SA,SB,SC,SD,SG,SH,SJ,SL,SM,SN,SO,SR,ST,SV,SY,SZ,TC,TD,TF,TG,TH,TJ,TK,TL,TM,TN,TO,TT,TV,TZ,UA,UG,UM,UY,UZ,VA,VC,VE,VG,VN,VU,WF,WS,YE,YT,ZM,ZW,ZZ', #every other country on the planet LAWL
         'filters':'',

         # A connection attempt is made to this ip,port but it's not
         # one of the regular hosts. Dunno what it is and dont have any
         # logs for it. All I see is an unACKed SYN being sent there.
         # Also, wtf is it called telemetry?? We're not launching rockets
         # into space here...
         'telemetryToken':base64.b64encode('159.153.244.83,9988,enFI,^\xf2\xf0\xbd\xaf\x88\xf8\xca\x94\x96\x9f\x96\xdd\xcd\xc6\x9b\xe9\xad\xd7\xa8\x8a\xb6\xec\xda\xb0\xec\xea\xcd\xe3\xc2\x84\x8c\x98\xb1\xc4\x99\x9b\xa6\xec\x8c\x9b\xb9\xc6\x89\xe3\xc2\x84\x8c\x98\xb0\xe0\xc0\x81\x83\x86\x8c\x98\xe1\xc6\xd1\xa9\x86\xa6\x8d\xb1\xac\x8a\x85\xba\x94\xa8\xd3\xa2\xd3\xde\x8c\xf2\xb4\xc8\xd4\xa0\xb3\xd8\xc4\x91\xb3\x86\xcc\x99\xb8\xe2\xc8\xb1\x83\x87\xcb\xb2\xee\x8c\xa5\x82\n'), # ip,port,encoding? (langCountry), ????? no clue about the rest
      })
   
class Ra3MsgHlr_GameSpyPreAuth(MessageHandler):
      # no inputs
   def makeReply(self):
      return self.msg.makeReply({
         'challenge':'gnbzlxhv', # dont know if/how this is used. If it is it's likely during the connection to gpcm.gamespy.com
         # this base64 string is incorrectly padded. lacks 1 base64 character it seems. Appears to be gibberish, so there must be some trick to decoding it. Or maybe not, it could just be a long hash??? doubtful tho.
         'ticket':'CCUBnHUPERml+OVgejfpuXqQS9VmzKBnBalrwEnQ8HBNvxOl/8qpukAzGCJ1HzTundOT8w6gFXNtNk4bDJnd0xtgw==', # this is the authToken that is sent to gpcm.gamespy.com soon after this transaction completes.
      })
      # TODO:ping once just for the hell of it
      #replies.append(self.messageClass('fsys', 0, {'TXN':'Ping'}))
        
class RedAlert3LoginFactory(ServerFactory):
   protocol = RedAlert3LoginServer
   
class Ra3GsLoginServer(gamespy.login.LoginServer):
   pass

class Ra3GsLoginServerFactory(ServerFactory):
   protocol = Ra3GsLoginServer
   log = logging.getLogger('gamespy.ra3Serv')
   
   def buildProtocol(self, addr):
      p = ServerFactory.buildProtocol(self, addr)
      p.theater = Theater.getTheater(gameId)
      return p

class MasterServer(Protocol):
   def dataReceived(self, data):
      # first 8 are binary with some nulls, so have to skip those manually before splitting
      m = {}
      (m['length'], m['headerRemainder']), data = struct.unpack('!H6s', data[:8]), data[9:] # 8, 9 skip the null in between
      m['gameName'], m['gameName2'], data = data.split('\0', 2)
      m['validate'], (m['request'], m['bodyRemainder']) = data[:8], data[9:].split('\0', 1) # skip null again
      #self.factory.log.debug('received: {0}'.format(m))
      self.factory.log.debug('received: request={0}'.format(m['request']))
      
      # everytime a request comes in, re-init the cipher
      self.cipher = gamespy.cipher.CipherFactory.getMasterCipher(gameId, m['validate'])
      self.handleRequest(m)
   
   def sendMsg(self, msg):
      self.factory.log.debug('sent: {0}'.format(msg))
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
         # TODO: these were duped in real msg, why??
         #'hostname' : 0,
         #'gamemode' : 0,
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
      '#\x00-117165505\x00'
      '0 100 10000 0 0 10 0 1 1 -1 0 -1 1 0 \x00'
      '0 100 10000 0 0 10 0 1 1 -1 0 -1 1 1 \x00'
      '0 100 10000 0 0 10 0 1 1 -1 0 -1 1 2 \x00'
      +'\0'.join(('0', '1', '2', '3', '4', '5', '6'))+'\0'
      'data/maps/official/map_mp_6_feasel3/map_mp_6_feasel3.map\x00'
      'data/maps/official/camp_a07_tokyoharbor_davis/camp_a07_tokyoharbor_davis.map\x00'
      'openstaging\x00data/maps/official/map_mp_4_feasel3/map_mp_4_feasel3.map\x00'
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
      channels = Channel.objects.filter(game__name=gameId, name__startswith='#GPG')
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
      + ''.join('@{0}\xff{1}\x00\x03\x15\x03\x07\x02'.format(struct.pack('!L', c.id), c.prettyName) for c in channels) +
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

class MasterServerFactory(ServerFactory):
   protocol = MasterServer
   log = logging.getLogger('gamespy.ra3master')
   
def fwdDRS(self, data):
   self.factory.log.debug('server received: %s', data)
   ProxyServer.dataReceived(self, data)
def fwdDRC(self, data):
   self.factory.log.debug('client received: %s', data)
   ProxyClient.dataReceived(self, data)

class RedAlert3Service(MultiService):
   def __init__(self, addresses=None):
      MultiService.__init__(self)
      sCtx = OpenSSLContextFactoryFactory.getFactory('EA')
      sFact = RedAlert3LoginFactory()
      #sFact = makeTLSFwdFactory('fesl.fwdCli', 'fesl.fwdSer', fwdDRC, fwdDRS)(*address)
      self.addService(SSLServer(addresses[0][1], sFact, sCtx))
      #self.addService(TCPServer(80, gamespy.DownloadsServerFactory()))
      
      self.addService(UDPServer(27900, gamespy.available.AvailableServer()))
      
      address = ('207.38.11.136', 6667)
      #self.addService(TCPServer(address[1], gamespy.ProxyPeerchatServerFactory(gameId, *address)))
      self.addService(TCPServer(6667, gamespy.peerchat.PeerchatFactory(gameId)))
      
      self.addService(TCPServer(8001, gamespy.sake.SakeServer()))
      
      address = ('207.38.11.14', 28910)
      #sFact = gamespy.ProxyMasterServerFactory(gameId, *address)
      sFact = MasterServerFactory()
      self.addService(TCPServer(address[1], sFact))
      
      address = ('gpcm.gamespy.com', 29900)
      sFact = makeTCPFwdFactory('gamespy.gpcm.client', 'gamespy.gpcm.server', fwdDRC, fwdDRS)(*address)
      self.addService(TCPServer(address[1], sFact))
 