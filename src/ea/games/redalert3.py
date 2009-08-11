import logging
import base64

from twisted.application.internet import SSLServer, TCPServer, UDPServer
from twisted.internet.protocol import ServerFactory
from twisted.application.service import MultiService

import gamespy
from ea.login import *
from ea.db import *

gameId = 'redalert3pc'

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
            'personas':self.server.session.user.getPersonas(),
      })
      
class Ra3MsgHlr_NuAddPersona(MessageHandler):
   # dict:TXN=NuGetPersonas,namespace=
   def handle(self):
      # dict:TXN=NuAddPersona,name=PersonaName
      self.server.session.user.addPersona(self.msg.map['name'])
      
      # TODO: haven't captured an actual response to this, but this works
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
      persona = Persona.objects.get(name=self.msg.map['name'])
      self.user = persona.user
      # dunno if this is the best way of managing the selected login
      self.user.persona_set.update(selected=False)
      persona.selected = True
      persona.save()
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


class MasterServerFactory(ServerFactory):
   protocol = gamespy.master.MasterServer
   log = logging.getLogger('gamespy.ra3master')
   gameName = gameId
   
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
      
      self.addService(UDPServer(27900, gamespy.available.AvailableServer()))
      self.addService(TCPServer(8001, gamespy.sake.SakeServer()))
      self.addService(TCPServer(8002, gamespy.downloads.DownloadsServerFactory()))
      
      address = ('207.38.11.136', 6667)
      sFact = gamespy.peerchat.PeerchatFactory(gameId)
      #sFact = gamespy.peerchat.ProxyPeerchatServerFactory(gameId, *address)
      self.addService(TCPServer(address[1], sFact))
      
      address = ('207.38.11.14', 28910)
      sFact = MasterServerFactory()
      #sFact = gamespy.master.ProxyMasterServerFactory(gameId, *address)
      self.addService(TCPServer(address[1], sFact))
      
      address = ('gpcm.gamespy.com', 29900)
      sFact = makeTCPFwdFactory('gamespy.gpcm.client', 'gamespy.gpcm.server', fwdDRC, fwdDRS)(*address)
      self.addService(TCPServer(address[1], sFact))
 