from __future__ import absolute_import
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
import string

import OpenSSL
from twisted.internet.protocol import Protocol
from twisted.internet.ssl import DefaultOpenSSLContextFactory
from twisted.internet.defer import Deferred

from .message import Message, MessageFactory
from ..db import *
from .. import util
from ..util.fwdserver import *
from ..util.timer import KeepaliveService
from . import errors

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

_commonKey = '''-----BEGIN RSA PRIVATE KEY-----
MIIBOwIBAAJBANnZdpfwsaidD/HXgQN6aI/hkJFuVhZxdMjFGRDbsHQCih+tjZCy
Yl7rBefxvOkgeleSANB+hxbxBMOW6udWqpsCAwEAAQJAf1d72GMtJnfxCxhC5OqX
1osu+6P4lJPrhTSZa15P7e89yW9i+DojDNVjaAlFrRdkvWFb59vd44Jl0ZjSpX/X
iQIhAPW+0PFasaMLIbGzs9mu/+7U4aNXHB9cNwyEDVhd70hdAiEA4vCl5CMmnzfS
7GN4Gc6sCWI2F+2Kir/4ZT1mwUPsL1cCIQDsDWbW769CVib/cwaHSzo8R/CV3c79
sK6QLyhCgbifYQIgI25e+Bdk2Ebm73E4Nw9FXNGwkFvN3YvLREMp39Ky9VECIQC0
W4I6GWlJLLa4pswGt4yDBxKiSJjEl3OOgAJgIX9WLg==
-----END RSA PRIVATE KEY-----'''

class OpenSSLContextFactoryFactory:
   _certs = {
      'fesl.ea.com': (_commonKey,
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
-----END CERTIFICATE-----'''),
      'prodgos28.ea.com': (_commonKey,
'''-----BEGIN CERTIFICATE-----
MIIDoTCCAwqgAwIBAgIBOTANBgkqhkiG9w0BAQQFADCByTELMAkGA1UEBhMCVVMx
EzARBgNVBAgTCkNhbGlmb3JuaWExFTATBgNVBAcTDFJlZHdvb2QgQ2l0eTEeMBwG
A1UEChMVRWxlY3Ryb25pYyBBcnRzLCBJbmMuMSAwHgYDVQQLExdPbmxpbmUgVGVj
aG5vbG9neSBHcm91cDEjMCEGA1UEAxMaT1RHMyBDZXJ0aWZpY2F0ZSBBdXRob3Jp
dHkxJzAlBgkqhkiG9w0BCQEWGGRpcnR5c29jay1jb250YWN0QGVhLmNvbTAeFw0w
OTExMjMwNzMzMDFaFw0yNTEwMDMyMjA3NDFaMH8xCzAJBgNVBAYTAlVTMRMwEQYD
VQQIEwpDYWxpZm9ybmlhMR4wHAYDVQQKExVFbGVjdHJvbmljIEFydHMsIEluYy4x
IDAeBgNVBAsTF09ubGluZSBUZWNobm9sb2d5IEdyb3VwMRkwFwYDVQQDExBwcm9k
Z29zMjguZWEuY29tMFwwDQYJKoZIhvcNAQEBBQADSwAwSAJBANnZdpfwsaidD/HX
gQN6aI/hkJFuVhZxdMjFGRDbsHQCih+tjZCyYl7rBefxvOkgeleSANB+hxbxBMOW
6udWqpsCAwEAAaOCASQwggEgMB0GA1UdDgQWBBQjW6VPo2bsIStfkzuA4F1aX4Oz
FDCB/gYDVR0jBIH2MIHzgBTvxpAYhozU6AlMhVIcVp1mwHBBk6GBz6SBzDCByTEL
MAkGA1UEBhMCVVMxEzARBgNVBAgTCkNhbGlmb3JuaWExFTATBgNVBAcTDFJlZHdv
b2QgQ2l0eTEeMBwGA1UEChMVRWxlY3Ryb25pYyBBcnRzLCBJbmMuMSAwHgYDVQQL
ExdPbmxpbmUgVGVjaG5vbG9neSBHcm91cDEjMCEGA1UEAxMaT1RHMyBDZXJ0aWZp
Y2F0ZSBBdXRob3JpdHkxJzAlBgkqhkiG9w0BCQEWGGRpcnR5c29jay1jb250YWN0
QGVhLmNvbYIJAKLuNSb7CJs8MA0GCSqGSIb3DQEBBAUAA4GBAHdtAWaknS4W2bKU
o1L4QdO2O6sMaAqsvDaCxF27rj4c53shwgqtZWkZqFZGGMzr2efEZAI4qn2EquuT
rW9ALbXAQURGVYU7PDc9bM8loyj4Wvah9LeKFBc9walR0cUdAaIJDzh5hdyL8be4
D10MY+OsEQ14IDG7+CKm8sUApxrU
-----END CERTIFICATE-----'''),
   }
   @classmethod
   def getFactory(self, name):
      return StringLoadingOpenSSLContextFactory(*self._certs[name])

## TODO: handle goodbye

def toEAMapping(map):
   d = dict(('{%s}'%k, v) for k, v in map.iteritems())
   d['{}'] = len(d)
   return d

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
      self.svc.alive()

   def startLoop(self):
      self.svc = KeepaliveService(self.getResponse, 120, self.server.transport.loseConnection)
      self.svc.startService()
      #FIXME!!!!#self.session.services.append(svc)

class EaCmd_Ping(Command):
   def getResponse(self):
      msg = EaLoginMessage('fsys', 0, {'TXN':'Ping'}, transport=self.server.transport)

      self.response = self.server.getResponse(msg)
      self.response.addCallback(self.receiveResponse)
      # TODO: setTimeout on deferreds to drop connections that dont reply
      return self.response

   def receiveResponse(self, msg):
      self.svc.alive()

   def startLoop(self):
      self.svc = KeepaliveService(self.getResponse, 120, self.server.transport.loseConnection)
      self.svc.startService()
      #FIXME!!!!#self.session.services.append(svc)

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
      self.log = util.getLogger('login', self)

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
      #self.log.debug('sent {0}\n'.format(hexdump(repr(msg))))
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
         'theaterPort':ep.port + 5, ##HACK, don't hardcode this port here, tight coupling
         #'domainPartition.domain':'eagames',
         #'domainPartition.subDomain':'MERCS2',
      })

   def handle(self):
      self.Reply() #send initial reply

      ## start memcheck svc
      EaCmd_MemCheck(self.server).startLoop()

class EaMsgHlr_NuLogin(MessageHandler): # TODO this and mercs2 are almost identical, derive this from mercs one
   def makeReply(self):
      return self.msg.makeReply(self.replyMap)

   def handle(self):
      def cbUser(user):
         # dict:TXN=NuLogin,macAddr=$001bfcb369cb,nuid=xxxxxx,password=xxxxx,returnEncryptedInfo=1
         self.replyMap = {
            'nuid': user.login_dirty,
            'userId': user.id,
            'profileId': user.id, # seems to be always the same as userId
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

            #self.replyMap['encryptedLoginInfo'] = 'Ciyvab0tregdVsBtboIpeChe4G6uzC1v5_-SIxmvSLJ82DtYgFUjObjCwJ2gbAnB4mmJn_A_J6tn0swNLggnaFOnewWkbq09MOpvpX-Eu19Ypu3s6gXxJ3CTLLkvB-9UKI6qh-nfrXHs3Ij9FBzMrQ..'
            self.replyMap['encryptedLoginInfo'] = 'Ciyvab0tregdVsBtboIpeChe4G6uzC1v5_-SIxmvSLKqzcqC65kVfFSAEe3lLoY8ZEGkTOwgFM8xRqUuwICLMyhYLqhtMx2UYCllK0EZUodWU5w3jv7gny_kWfGnA6cKbRtwKAriv2OdJmPGsPDdGQ..'
         else:
            self.replyMap['displayName'] = user.login_dirty
            self.replyMap['entitledGameFeatureWrappers'] = [{
               'gameFeatureId':6014,
               'status':0,
               'message':'',
               'entitlementExpirationDate':'',
               'entitlementExpirationDays':-1,
            }]
         self.Reply()

      def ebUser(err):
         self.server.session.delete()
         err.trap(errors.EaError)
         self.replyMap = {
            'localizedMessage' : '"{0}"'.format(err.value.text),
            'errorContainer' : [],
            'errorCode' : err.value.id,
         }
         self.Reply()
      username = self.msg.nuid.strip('"')
      dfr = self.server.session.Login(username, self.msg.password)
      dfr.addCallbacks(cbUser, ebUser)

class EaMsgHlr_NuGetPersonas(MessageHandler):
   # dict:TXN=NuGetPersonas,namespace=
   def makeReply(self):
      return self.msg.makeReply({
            'personas':self.server.session.user.getPersonas(),
      })

##TODO:
## newpersona too short
## newpersona already taken

class EaMsgHlr_NuAddPersona(MessageHandler):
   def makeReply(self):
      return self.msg.makeReply(self.replyMap)

   # dict:TXN=NuGetPersonas,namespace=
   def handle(self):
      # dict:TXN=NuAddPersona,name=PersonaName
      def cbPersona(persona):
         self.replyMap = {}
         self.Reply()

      def ebPersona(err):
         err.trap(errors.EaError)
         self.replyMap = {
            'localizedMessage' : '"{0}"'.format(err.value.text),
            'errorContainer' : [],
            'errorCode' : err.value.id,
         }
         self.Reply()

      ## FIXME: blanks result in 'name in use' error
      name = self.msg.map['name'].strip('"')
      dfr = self.server.session.user.addPersona(name)
      dfr.addCallbacks(cbPersona, ebPersona)

class EaMsgHlr_NuLoginPersona(MessageHandler):
      # dict:TXN=NuLoginPersona,name=xxxxx
   def makeReply(self):
      #'SUeWiB5BVHH_cJooCn4oOAAAKD0.' #only middle part is diff from one returned in NuLogin
      return self.msg.makeReply({
         'lkey':self.server.session.key,
         'profileId':self.user.login_dirty,
         'userId':self.user.login_dirty,
      })
   def handle(self):
      name = self.msg.map['name'].strip('"')
      persona = Persona.objects.get(name=name)
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
      ## these random bytes must be >= 0x80 so they dont interfere with msg format
      randBytes = ''.join(chr(random.getrandbits(7)|0x80) for _ in range(100))
      return self.msg.makeReply({
         # These are all country codes it appears.
         'enabled' : 'CA,MX,PR,US,VI', #Canada, Mexico, Puerto Rico, United States, Virgin Islands
         'disabled' : 'AD,AF,AG,AI,AL,AM,AN,AO,AQ,AR,AS,AW,AX,AZ,BA,BB,BD,BF,BH,BI,BJ,BM,BN,BO,BR,BS,BT,BV,BW,BY,BZ,CC,CD,CF,CG,CI,CK,CL,CM,CN,CO,CR,CU,CV,CX,DJ,DM,DO,DZ,EC,EG,EH,ER,ET,FJ,FK,FM,FO,GA,GD,GE,GF,GG,GH,GI,GL,GM,GN,GP,GQ,GS,GT,GU,GW,GY,HM,HN,HT,ID,IL,IM,IN,IO,IQ,IR,IS,JE,JM,JO,KE,KG,KH,KI,KM,KN,KP,KR,KW,KY,KZ,LA,LB,LC,LI,LK,LR,LS,LY,MA,MC,MD,ME,MG,MH,ML,MM,MN,MO,MP,MQ,MR,MS,MU,MV,MW,MY,MZ,NA,NC,NE,NF,NG,NI,NP,NR,NU,OM,PA,PE,PF,PG,PH,PK,PM,PN,PS,PW,PY,QA,RE,RS,RW,SA,SB,SC,SD,SG,SH,SJ,SL,SM,SN,SO,SR,ST,SV,SY,SZ,TC,TD,TF,TG,TH,TJ,TK,TL,TM,TN,TO,TT,TV,TZ,UA,UG,UM,UY,UZ,VA,VC,VE,VG,VN,VU,WF,WS,YE,YT,ZM,ZW,ZZ', #every other country on the planet LAWL
         'filters' : '',

         ## why is it called telemetry?? We're not launching rockets
         ## into space here...
         ## ip,port,encoding? (langCountry), 100 bytes (random?) keydata sent to given ip
         'telemetryToken' : base64.b64encode('{0},{1},enUS,^{2}\n'.format(self.server.transport.getHost().host, 9955, randBytes)),
      })

class EaMsgHlr_GameSpyPreAuth(MessageHandler):
      # no inputs
   def makeReply(self):
      import random, string
      chal = ''.join(random.choice(string.ascii_lowercase) for _ in range(8))
      #chal = 'rkoqlbdc' ## paired with ticket, below
      self.server.session.key = chal
      self.server.session.save()
      return self.msg.makeReply({
         'challenge': chal,
         ## this base64 string is incorrectly padded -- lacks 1 base64 character it seems.
         ## this is the authToken that the client will send to gpcm.gamespy.com soon after this transaction completes.
         ## it may or may not be decodable by or meaningful to the client
         #'ticket':'CCUNTxOjYkDHJuDB9h0fw/skLy+s9DUCol1LFKmjk7Rc6/suwmWbFsKXbdZ1uZoEoQo7jHwlW7ZVw5FidVhdX8Yaw==',
         ## HACK, TODO: use login name instead of ticket so that gpcm knows who we are:
         ## this is vulnerable to impersonation since we trust the gpcm login msg isnt spoofed
         'ticket':self.server.session.user.login_dirty, ## this is sent as 'authtoken' to gpcm
      })

   def handle(self):
      self.Reply()

      ## start ping service now that we're successfully logged in
      EaCmd_Ping(self.server).startLoop()

