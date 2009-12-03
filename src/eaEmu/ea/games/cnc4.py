import logging

from twisted.application.internet import SSLServer, TCPServer, UDPServer
from twisted.internet.protocol import ServerFactory
from twisted.application.service import MultiService

import gamespy
from ea.login import *
from ea.db import *
import util

#####
## TODO: lots still copied over from ra3 in here!!!!
#####

gameId = 'redalert3pc'

class RedAlert3LoginServer(EaServer):
   theater = Theater.objects.get(name='cnc4')
   def connectionMade(self):
      EaServer.connectionMade(self)
      self.log = util.getLogger('login.cnc4', self)
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

class RedAlert3LoginFactory(ServerFactory):
   protocol = RedAlert3LoginServer

class Ra3GsLoginServer(gamespy.login.LoginServer):
   pass

class Ra3GsLoginServerFactory(ServerFactory):
   protocol = Ra3GsLoginServer
   log = util.getLogger('gamespy.ra3Serv', self)

   def buildProtocol(self, addr):
      p = ServerFactory.buildProtocol(self, addr)
      p.theater = Theater.getTheater(gameId)
      return p

## TODO: should this really be game-specific?
class QueryMasterFactory(ServerFactory):
   protocol = gamespy.master.QueryMaster
   log = util.getLogger('gamespy.ra3master', self)
   gameName = gameId


def hexdump(src, length=32):
   result = []
   digits = 4 if isinstance(src, unicode) else 2
   for i in xrange(0, len(src), length):
      s = src[i:i+length]
      hexa = b' '.join(["%0*X" % (digits, ord(x))  for x in s])
      text = b''.join([x if 0x20 <= ord(x) < 0x7F else b'.'  for x in s])
      result.append( b"%04X   %-*s   %s" % (i, length*(digits + 1), hexa, text) )
   return b'\n'.join(result)

def fwd(self, data):
   self.factory.log.debug('received: %s', '\n' + hexdump(data))
   self.__class__.__bases__[0].dataReceived(self, data)

class Service(MultiService):
   def __init__(self, addresses=None):
      MultiService.__init__(self)

      ports = dict(addresses)

      name = 'prodgos28.ea.com'
      sCtx = OpenSSLContextFactoryFactory.getFactory(name)
      address = (name, ports[name])
      #sFact = RedAlert3LoginFactory()
      sFact = makeTLSFwdFactory('login.cnc4.client', 'login.cnc4.server', fwd, fwd)(*address)
      self.addService(SSLServer(address[1], sFact, sCtx))

