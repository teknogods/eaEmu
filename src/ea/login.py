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

from fwdserver import *
from ea.db import Session

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
   for msg in EaMessage.parseData(data):
      ep = '{0.host}:{0.port}'.format(self.transport.getPeer())
      msg.debugPrint(self.factory.log, 'server received (%s):' % ep)
      ProxyServer.dataReceived(self, str(msg))
def fwdDRC(self, data):
   for msg in EaMessage.parseData(data):
      ep = '{0.host}:{0.port}'.format(self.transport.getPeer())
      msg.debugPrint(self.factory.log, 'client received (%s):' % ep)
      ProxyClient.dataReceived(self, str(msg))

class EaMessage:
   def __init__(self, id='XXXX', flags=0, map=None, extraLines=None, transport=None):
      self.id = id
      self.flags = flags
      self.map = map or {} # remember, cant put mutable references as default arg!!
      self.extraLines = extraLines or []
      self.transport = transport
      self.unflatten()
   
   def send(self):
      if self.transport:
         self.transport.write(str(self))
      else:
         raise Exception('transport not provided')

   def __repr__(self):
      'representation of the message suitable for sending over the wire'
      self.flatten()
      body = '\n'.join(['{0}={1}'.format(k, self.quote(v)) for k, v in self.map.iteritems()] + self.extraLines) + '\0'
      self.unflatten()
      length = len(body) + 12 # length includes 12 byte header
      return self.id + struct.pack('!2L', self.flags, length) + body

   def flatten(self):
      fmt = '{0}.{1}'
      # TODO: simpler to write this to work in-place?
      def _flatten(name, obj):
         d = {}
         if isinstance(obj, dict):
            for k, sub in obj.items():
               key = fmt.format(name, k) if name else k
               d.update(_flatten(key, sub))
         elif type(obj) in [list, tuple]:
            d = {fmt.format(name, '[]'):len(obj)}
            for i, e in enumerate(obj):
               d.update(_flatten(fmt.format(name, i), e))
         else:
            d = {name:str(obj)}
         return d

      self.map = _flatten(None, self.map)

   # I'm ambivalent about True as the default for collapse,
   # since EA is inconsistent about it's data structures.
   # If dotted names arent dictionaries then they shouldnt appear as elements
   # of a list! Because of that I have to use a dict to store dotted names
   # in a list collapsed list, making the dict() type ambiguous. In practice,
   # when collapse is True, dictionaries that are not immediate children
   # of lists are EAMappings.
   #
   # TODO: make the msg class support access via msg['a.b'] or msg['a']['b'] or msg.a.b
   def unflatten(self, collapse=True):
      def _unflatten(map, collapse):
         for k, v in map.items():
            if '.' in k:
               name, rest = k.split('.', 1)
               if name not in map:
                  map[name] = {}
               map[name][rest] = v
               del map[k]
         for k, sub in map.items():
            if isinstance(sub, dict):
               _unflatten(sub, collapse)
               if '[]' in sub:
                  # convert to list object
                  map[k] = [sub[str(x)] for x in range(int(sub['[]']))]
               elif '{}' in sub:
                  # TODO: convert to EAmapping object
                  # right now, just prune all "{}" chars
                  #del sub['{}']
                  pass#map[k] = dict((x.strip('{}'), y) for x, y in sub.items())
                  # FIXME: HACKed out cuz it broke fwdServ
               elif collapse:
                  if '[]' not in map: # don't collapse dicts in lists
                     for sk in sub.keys():
                        map['.'.join([k, sk])] = sub[sk]
                     del map[k]
      _unflatten(self.map, collapse)

   # Url quotes a few characters. This seems to be a very selective url quote.
   # Also uses lowercase letters.
   def quote(self, s):
      s = str(s)
      # FIXME: hacked out cuz it broke fwdServ
      # Where was this originally used though? ra3 fesl somewhere i think...
      #s = s.replace(':', '%3a')
      s = s.replace('=', '%3d')
      return s

   def __str__(self):
      'pretty repersentation of the message'
      parts = [
         '({0} on {1.host}:{1.port})'.format(self.__class__.__name__, self.transport.getPeer()),
         'id={0}'.format(self.id),
         'flags={0:#010x}'.format(self.flags),
      ]
      m = self.map
      if 'decodedSize' in m and m['decodedSize'] > 100:
         m = m.copy()
         m['data'] = m['data'][:32] + '...'
      #parts.append('dict: {0}'.format(','.join('{0}={1}'.format(k, m[k]) for k in sorted(m.keys()))))
      parts.append('dict: {0}'.format(repr(m)))
      if self.extraLines:
         parts.append('extraLines: ' + ' '.join(self.extraLines))
      return ' '.join(parts)

   # i know mappings and dicts are the same but this one is for internal use
   # only because i only discovered the "mappings" with '{}' in the key names
   # later. I still want to treat dotted names as dicts, but need to support the
   # explicit {} kind as well. To add one of the latter, use addMapping()
   # 
   # for now i'm just treating "Mappings" the same as regular dicts, just with
   # goofy key names. Eventually it may be necessary to give them distinct
   # types, but prly not.
   def addMapping(self, name, contents):
      map = dict(('{{{0}}}'.format(k), v) for k, v in contents.items())
      map['{}'] = len(map)
      self.map[name] = map
      
   def makeReply(self, map=None):
      ''' subclass should make any appropriate changes to flags,contents after calling this supermethod '''
      reply = copy.copy(self)
      reply.map = {}
      if map: reply.map.update(map)
      return reply
   
   def getKey(self):
      return ''.join([self.id,])

class EaLoginMessage(EaMessage):
   def makeReply(self, map=None):
      reply = EaMessage.makeReply(self, map)
      # This seems to always hold true. The last byte(s?) is the message sequence id.
      # If an error is returned, I've seen the values 'ntfn' and 'ferr' occupy the flags field
      # Client always sends c0 as first byte.
      reply.flags = 0x80000000 | (self.flags & 0xFF) # how many bytes is sequence id??
      reply.map['TXN'] = self.map['TXN']
      return reply
   
   def getKey(self):
      return '{0}{1}'.format(self.map['TXN'], self.flags & 0xFF)
   
class MessageFactory:
   def __init__(self, transport, msgClass=EaMessage):
      self.transport = transport
      self.msgClass = msgClass
   
   def getMessages(self, data):
      messages = []
      while len(data):
         id, flags, length = struct.unpack('!4s2L', data[:12])
         # map takes format: "name=value\n... \0" (final [\n]\0 terminator)
         # HACK/FIXME:In burnout 08, sometimes the length is longer than len(data)
         # and msg is continued in next packet. This is currently unhandled.
         #msg.map = dict([urllib.unquote(x) for x in line.split('=', 1)] for line in data[12:msg.length].strip('\n\0').split('\n'))
         sep = '\n'
         if '\t' in data[12:length]: sep = '\t'#HACK? sometimes separator is tab char!! (burnout 3rd msg)
         map = {}
         extraLines = []
         for line in data[12:length].strip(sep+'\0').split(sep):
            if '=' in line:
               k, v = line.split('=', 1)
               map[k] = urllib.unquote(v)
               #if k == 'ADDR': msg.map[k] = '5.84.34.44'
            else:
               #print 'not a key-value pair: "{0}"'.format(line)
               extraLines.append(line)
         messages.append(self.msgClass(id, flags, map, extraLines, self.transport))
         data = data[length:]
      return messages
   

class MessageHandlerFactory:
   def __init__(self, server, prefix):
      self.server = server
      self.prefix = prefix
      
   def getHandler(self, msg):
      hlr = None
      try:
         if '.' in self.prefix:
            exec 'import {0}'.format(self.prefix.rsplit('.', 1)[0])
         hlr = eval('{0}_{1}'.format(self.prefix, msg.map['TXN']))(self.server, msg)
      except (NameError, AttributeError), e: #FIXME, catch only eval exception whatever that type is
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
