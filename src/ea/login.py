# TODO: enforce unique personas and give appropriate reply if a name is unavailable


# FESL stands for:
# Federated Ea Server Login?
# FEderated Server Login?
import struct
import logging
import urllib
import random
import copy
import time

import OpenSSL
from twisted.internet.protocol import Protocol
from twisted.internet.ssl import DefaultOpenSSLContextFactory
from twisted.internet.defer import Deferred

from message import Message, MessageFactory
from fwdserver import *
from db import *

class StringLoadingOpenSSLContextFactory(DefaultOpenSSLContextFactory):
   # This is a hacky copy from twisted.internet.ssl.DefaultOpenSSLContextFactory.
   # The only change is the 2 methods that loaded files now load x509objects.
   def cacheContext(self):
      ctx = OpenSSL.SSL.Context(self.sslmethod)
      # Here, self.cert/privFileName are the wrong names. I didn't want to reimplement
      # __init__ so I reused them. The strings contain the data rather than
      # the names of files containing the data.
      cert = OpenSSL.crypto.load_certificate(OpenSSL.crypto.FILETYPE_PEM, self.certificateFileName)
      key = OpenSSL.crypto.load_privatekey(OpenSSL.crypto.FILETYPE_PEM, self.privateKeyFileName)
      ctx.use_certificate(cert)
      ctx.use_privatekey(key)
      self._context = ctx

class OpenSSLContextFactoryFactory:
   EA = (
'''-----BEGIN RSA PRIVATE KEY-----
MIIBOwIBAAJBANnZdpfwsaidD/HXgQN6aI/hkJFuVhZxdMjFGRDbsHQCih+tjZCy
Yl7rBefxvOkgeleSANB+hxbxBMOW6udWqpsCAwEAAQJAf1d72GMtJnfxCxhC5OqX
1osu+6P4lJPrhTSZa15P7e89yW9i+DojDNVjaAlFrRdkvWFb59vd44Jl0ZjSpX/X
iQIhAPW+0PFasaMLIbGzs9mu/+7U4aNXHB9cNwyEDVhd70hdAiEA4vCl5CMmnzfS
7GN4Gc6sCWI2F+2Kir/4ZT1mwUPsL1cCIQDsDWbW769CVib/cwaHSzo8R/CV3c79
sK6QLyhCgbifYQIgI25e+Bdk2Ebm73E4Nw9FXNGwkFvN3YvLREMp39Ky9VECIQC0
W4I6GWlJLLa4pswGt4yDBxKiSJjEl3OOgAJgIX9WLg==
-----END RSA PRIVATE KEY-----''',
'''-----BEGIN CERTIFICATE-----
MIIDnDCCAwWgAwIBAgIBNzANBgkqhkiG9w0BAQQFADCByTELMAkGA1UEBhMCVVMx
EzARBgNVBAgTCkNhbGlmb3JuaWExFTATBgNVBAcTDFJlZHdvb2QgQ2l0eTEeMBwG
A1UEChMVRWxlY3Ryb25pYyBBcnRzLCBJbmMuMSAwHgYDVQQLExdPbmxpbmUgVGVj
aG5vbG9neSBHcm91cDEjMCEGA1UEAxMaT1RHMyBDZXJ0aWZpY2F0ZSBBdXRob3Jp
dHkxJzAlBgkqhkiG9w0BCQEWGGRpcnR5c29jay1jb250YWN0QGVhLmNvbTAeFw0w
ODEyMTUwOTE2NDdaFw0yNDEwMjUyMzUxMjdaMHoxCzAJBgNVBAYTAlVTMRMwEQYD
VQQIEwpDYWxpZm9ybmlhMR4wHAYDVQQKExVFbGVjdHJvbmljIEFydHMsIEluYy4x
IDAeBgNVBAsTF09ubGluZSBUZWNobm9sb2d5IEdyb3VwMRQwEgYDVQQDEwtmZXNs
LmVhLmNvbTBcMA0GCSqGSIb3DQEBAQUAA0sAMEgCQQDZ2XaX8LGonQ/x14EDemiP
4ZCRblYWcXTIxRkQ27B0AoofrY2QsmJe6wXn8bzpIHpXkgDQfocW8QTDlurnVqqb
AgMBAAGjggEkMIIBIDAdBgNVHQ4EFgQUI1ulT6Nm7CErX5M7gOBdWl+DsxQwgf4G
A1UdIwSB9jCB84AU78aQGIaM1OgJTIVSHFadZsBwQZOhgc+kgcwwgckxCzAJBgNV
BAYTAlVTMRMwEQYDVQQIEwpDYWxpZm9ybmlhMRUwEwYDVQQHEwxSZWR3b29kIENp
dHkxHjAcBgNVBAoTFUVsZWN0cm9uaWMgQXJ0cywgSW5jLjEgMB4GA1UECxMXT25s
aW5lIFRlY2hub2xvZ3kgR3JvdXAxIzAhBgNVBAMTGk9URzMgQ2VydGlmaWNhdGUg
QXV0aG9yaXR5MScwJQYJKoZIhvcNAQkBFhhkaXJ0eXNvY2stY29udGFjdEBlYS5j
b22CCQCi7jUm+wibPDANBgkqhkiG9w0BAQQFAAOBgQBT52x180JiKDHpsj7sEr0o
YUjrZOseRTAEMxP7fVG0k9l8nUYfA1dYaiGGNc0d+EAsv606hKWj0nwGET99vsk8
XO6kqG+dGaL7myi2PxyTGle4PfpcPCbpOQmGamAkLlS1L+Ccu2zriE7CtQsNMCtC
tS2IQaAocINiUsFPKA8Lhw==
-----END CERTIFICATE-----''')
   @classmethod
   def getFactory(self, name):
      if hasattr(self, name):
         return StringLoadingOpenSSLContextFactory(*getattr(self, name))

class EaSession(Session): # TODO separate this 'connection' from db object 'session'
   # TODO turn into handler
   def _todo_HandleGoodbye(self, msg):
      # dict:TXN=Goodbye,message="ErrType%3d0 ErrCode%3d0",reason=GOODBYE_CLIENT_NORMAL
      pass
      # no reply needed, just stop ping service
      #self.pingSvc.stopService()
      #self.memChkSvc.stopService()

def toEAMapping(map):
   d = dict(('{%s}'%k, v) for k, v in map.iteritems())
   d['{}'] = len(d)
   return d

def fwdDRS(self, data):
   for msg in Message.parseData(data):
      ep = '{0.host}:{0.port}'.format(self.transport.getPeer())
      msg.debugPrint(self.factory.log, 'server received (%s):' % ep)
      ProxyServer.dataReceived(self, str(msg))
def fwdDRC(self, data):
   for msg in Message.parseData(data):
      ep = '{0.host}:{0.port}'.format(self.transport.getPeer())
      msg.debugPrint(self.factory.log, 'client received (%s):' % ep)
      ProxyClient.dataReceived(self, str(msg))

class EaLoginMessage(Message):
   def makeReply(self, map=None):
      reply = Message.makeReply(self, map)
      # This seems to always hold true. The last byte(s?) is the message sequence id.
      # If an error is returned, I've seen the values 'ntfn' and 'ferr' occupy the flags field
      # Client always sends c0 as first byte.
      reply.flags = 0x80000000 | (self.flags & 0xFF) # how many bytes is sequence id??
      reply.map['TXN'] = self.map['TXN']
      return reply

   def getKey(self):
      return '{0}{1}'.format(self.map['TXN'], self.flags & 0xFF)

class MessageHandlerFactory:
   def __init__(self, server, prefix):
      self.server = server
      self.prefix = prefix

   def getHandler(self, msg):
      hlr = None
      if '.' in self.prefix:
         exec 'import {0}'.format(self.prefix.rsplit('.', 1)[0])
      for prefix in [self.prefix.split('.')[-1], 'EaMsgHlr']:
         try:
            hlr = eval('{0}_{1}'.format(prefix, msg.map['TXN']))(self.server, msg)
            break
         except (NameError, AttributeError), ex:
            pass
      return hlr

class MessageHandler:
   def __init__(self, server, msg):
      self.server = server
      self.msg = msg

   def makeReply(self):
      return self.msg.makeReply()

   def Reply(self):
      reply = self.makeReply() # abstract method
      self.server.sendMessage(reply)

   def handle(self):
      self.Reply()

class Command:
   def __init__(self, server):
      self.server = server

class EaCmd_MemCheck(Command):
   def getResponse(self):
      msg = EaLoginMessage('fsys', 0x80000000, {
         'TXN':'MemCheck',
         'salt':random.getrandbits(32), # pretty sure this is just random int32
         'type':0,
         'memcheck':[],
         }, transport=self.server.transport) # TODO: transport only needed for debug print

      self.response = self.server.getResponse(msg)
      self.response.addCallback(self.receiveResponse)
      # TODO: setTimeout on deferreds to drop connections that dont reply
      return self.response

   def receiveResponse(self, msg):
      pass

class EaCmd_Ping:
   def getResponse(self):
      msg = EaLoginMessage('fsys', 0, {'TXN':'Ping'}, transport=self.server.transport)

      self.response = self.server.sendMessage(msg)
      # TODO: setTimeout on deferreds to drop connections that dont reply
      return self.response

class EaServer(Protocol):
   '''
   Abstract superclass of every EA game server
   '''
   def connectionMade(self):
      ep = self.transport.getPeer()
      self.session = self.theater.CreateSession(ep.host, ep.port)
      self.msgFactory = MessageFactory(self.transport)
      self.responses = {}

      # subclasses should call the supermethod then reassign these
      self.hlrFactory = MessageHandlerFactory(self, 'EaMsgHlr')
      self.log = logging.getLogger('login.{0.host}:{0.port}'.format(ep))

   def connectionLost(self, *args):
      ep = self.transport.getPeer()
      self.session = self.theater.DeleteSession(ep.host, ep.port)
      Protocol.connectionLost(self, *args)


   def dataReceived(self, data):
      for msg in self.msgFactory.getMessages(data):
         self.log.debug('got  {0}'.format(msg))
         k = msg.getKey()
         if k in self.responses:
            self.responses[k].callback(msg)
            del self.responses[k]
         else:
            try:
               hlr = self.hlrFactory.getHandler(msg)
               if hlr:
                  hlr.handle()
               else:
                  # TODO: move these log message elsewhere? ideally this function should just pass the messages to the handler
                  self.log.error('unhandled request {0}'.format(msg))
            except Exception, e:
               raise # put your breakpoint here for client-thread exceptions

   def sendMessage(self, msg):
      self.log.debug('sent {0}'.format(msg))
      #self.log.debug('sent {0}'.format(repr(repr(msg))))
      self.transport.write(repr(msg))

   # TODO: move to own abstract class for multiple inheritance??
   def getResponse(self, msg):
      '''Sends a message and returns the response to it.'''
      response = Deferred()
      self.responses[msg.getKey()] = response # TODO: what if we send more than one with same key?
      self.sendMessage(msg)
      return response

   def Reply(self, msg, repMap=None):
      repMap = repMap or {}
      map = repMap.copy()
      flags = msg.flags
      if 'TXN' in msg.map:
         flags = 0x80000000 | (msg.flags & 0xFF) # how many bytes is sequence id??
         map['TXN'] = msg.map['TXN']

      self.SendMsg(msg.id, flags, map)

   def SendMsg(self, id, flags=0, map=None):
      map = map or {}
      msg = self.messageClass(id, flags, map)
      ep = '{0.host}:{0.port}'.format(self.transport.getPeer())
      msg.debugPrint(self.factory.log, 'server sent (%s):' % ep)
      self.transport.write(repr(msg))

   # maybe only mercs2?
   def SendStatus(self, map):
      map = map.copy()
      map.update({'TXN':'Status'})
      self.SendMsg('pnow', 0x80000000, map)

   def SendPing(self):
      self.SendMsg('fsys', 0, {'TXN':'Ping'})

class EaMsgHlr_Hello(MessageHandler):
   def makeReply(self):
      ep = self.server.transport.getHost()
      return self.msg.makeReply({
         'activityTimeoutSecs':0,
         'curTime':time.strftime('"%b-%d-%Y %H:%M:%S UTC"', time.gmtime()),
         'messengerIp':'messaging.ea.com',
         'messengerPort':13505,
         'theaterIp':ep.host,
         'theaterPort':ep.port + 1,
         #'domainPartition.domain':'eagames',
         #'domainPartition.subDomain':'MERCS2',
      })

   def handle(self):
      self.Reply() #send initial reply

      # send memcheck
      d = EaCmd_MemCheck(self.server).getResponse()

      #TODO: replace with service
      #svc = TimerService(120, EaCmd_MemCheck(self.session).send)
      #FIXME!!!!#self.session.services.append(svc)
      #svc.startService()

class EaMsgHlr_NuLogin(MessageHandler): # TODO this and mercs2 are almost identical, derive this from mercs one
   def makeReply(self):
      # dict:TXN=NuLogin,macAddr=$001bfcb369cb,nuid=xxxxxx,password=xxxxx,returnEncryptedInfo=1
      map = {
         'nuid': self.user.login,
         'userId': self.user.id,
         'profileId': self.user.id, # seems to be always the same as userId
         'lkey':self.server.session.key,
      }
      if int(self.msg.returnEncryptedInfo):
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
      # TODO: handle bad logins with proper messages
      m = self.msg
      self.user = self.server.session.Login(m.nuid, m.password)
      if self.user:
         self.Reply()
      else:
         # TODO send different reply here
         print 'TODO: user not found or bad pwd'


class EaMsgHlr_NuGetPersonas(MessageHandler):
   # dict:TXN=NuGetPersonas,namespace=
   def makeReply(self):
      return self.msg.makeReply({
            'personas':self.server.session.user.getPersonas(),
      })

class EaMsgHlr_NuAddPersona(MessageHandler):
   # dict:TXN=NuGetPersonas,namespace=
   def handle(self):
      # dict:TXN=NuAddPersona,name=PersonaName
      self.server.session.user.addPersona(self.msg.map['name'])

      # TODO: haven't captured an actual response to this, but this works
      self.Reply()

class EaMsgHlr_NuLoginPersona(MessageHandler):
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

class EaMsgHlr_NuEntitleGame(MessageHandler):
   # inputs are: 'password', 'nuid', 'key'
   # TODO: don't know what proper response is. This message can only be capture once per valid serial, i guess.
   # error is:  {'errorCode': '181', 'TXN': 'NuEntitleGame', 'errorContainer.[]': '0', 'localizedMessage': '"The code is not valid for registering this game"'}
   pass

class EaMsgHlr_GetTelemetryToken(MessageHandler):
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

class EaMsgHlr_GameSpyPreAuth(MessageHandler):
      # no inputs
   def makeReply(self):
      import random, string
      chal = ''.join(random.choice(string.ascii_lowercase) for _ in range(8))
      chal = 'rkoqlbdc' # paired with ticket
      self.server.session.key = chal
      self.server.session.save()
      return self.msg.makeReply({
         'challenge': chal,
         # this base64 string is incorrectly padded -- lacks 1 base64 character it seems.
         # this is the authToken that the client will send to gpcm.gamespy.com soon after this transaction completes.
         # it may or may not be decodable by or meaningful to the client
         #'ticket':'CCUNTxOjYkDHJuDB9h0fw/skLy+s9DUCol1LFKmjk7Rc6/suwmWbFsKXbdZ1uZoEoQo7jHwlW7ZVw5FidVhdX8Yaw==',
         ## HACK, TODO: use login name instead of ticket so that gpcm knows who we are:
         ## this is vulnerable to impersonation since we trust the gpcm login msg isnt spoofed
         'ticket':self.server.session.user.login,
      })
      # TODO:ping once just for the hell of it
      #replies.append(self.messageClass('fsys', 0, {'TXN':'Ping'}))



      #server received: \ka\\final\
      #client received: \lc\1\challenge\UKVDJNGEJQ\id\1\final\
      #server received:
      # \login\
      # \challenge\mN98JpKlhYpAbZXTBulJgUPNrq02irCk
      # \authtoken\CCUBnHUPERml+OVgejfpuXqQS9VmzKBnBalrwEnQ8HBNvxOl/8qpukAzGCJ1HzTundOT8w6gFXNtNk4bDJnd0xtgw==
      # \partnerid\0
      # \response\07174621471b61c2d69615e3169823da
      # \firewall\1
      # \port\0
      # \productid\11419
      # \gamename\redalert3pc
      # \namespaceid\1
      # \sdkrevision\11
      # \quiet\0
      # \id\1
      # \final\
      #client received: \blk\0\list\\final\
      #client received:
      # \bdy\3
      # \list\165597618,165742653,166045609
      # \final\
      # \lc\2
      # \sesskey\15613082
      # \proof\c18335aebee349df74aab1534515ef14
      # \userid\145371602
      # \profileid\165580976
      # \uniquenick\Jackalus
      # \lt\VX2r6Kx2syZJKROlc6fPID__ # login token - this changes each time
      # \id\1
      # \final\
      #server received: \status\1\sesskey\15613082\statstring\Online\locstring\\final\
