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

## TODO: should this really be game-specific?
class QueryMasterFactory(ServerFactory):
   protocol = gamespy.master.QueryMaster
   log = logging.getLogger('gamespy.ra3master')
   gameName = gameId

def fwdDRS(self, data):
   self.factory.log.debug('server received: %s', data)
   ProxyServer.dataReceived(self, data)
def fwdDRC(self, data):
   self.factory.log.debug('client received: %s', data)
   ProxyClient.dataReceived(self, data)

class Service(MultiService):
   def __init__(self, addresses=None):
      MultiService.__init__(self)
      sCtx = OpenSSLContextFactoryFactory.getFactory('EA')

      ## TODO: merge all port 80 services somehow? 1 handler that dispatches depending on request?
      self.addService(TCPServer(8001, gamespy.sake.SakeServer()))
      self.addService(TCPServer(8002, gamespy.downloads.DownloadsServerFactory()))
      ## TODO: psweb.games.py.com -- SOAP service that serves Clan-related requests
      ## TODO: redalert3services.gamespy.com -- HTTP GET requests that serve rank icons

      self.addService(UDPServer(27900, gamespy.master.HeartbeatMaster()))

      address = ('cncra3-pc.fesl.ea.com', 18840)
      sFact = RedAlert3LoginFactory()
      #sFact = makeTLSFwdFactory('login.ra3cli', 'login.ra3srv', fwdDRC, fwdDRS)(*address)
      self.addService(SSLServer(addresses[0][1], sFact, sCtx))

      address = ('peerchat.gamespy.com', 6667)
      sFact = gamespy.peerchat.PeerchatFactory()
      #sFact = gamespy.peerchat.ProxyPeerchatServerFactory(gameId, *address)
      self.addService(TCPServer(address[1], sFact))

      from gamespy.cipher import getMsName
      address = (getMsName(gameId), 28910)
      sFact = QueryMasterFactory()
      #sFact = gamespy.master.ProxyMasterServerFactory(gameId, *address)
      self.addService(TCPServer(address[1], sFact))

      address = ('gpcm.gamespy.com', 29900)
      sFact = gamespy.gpcm.ComradeFactory()
      #sFact = makeTCPFwdFactory('gamespy.gpcm.client', 'gamespy.gpcm.server', fwdDRC, fwdDRS)(*address)
      self.addService(TCPServer(address[1], sFact))
