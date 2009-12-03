import logging

from twisted.application.internet import SSLServer, TCPServer, UDPServer
from twisted.internet.protocol import ServerFactory
from twisted.application.service import MultiService

from ... import gamespy
from ... import util
from ..login import *
from ..db import *

gameId = 'redalert3pc'

class RedAlert3LoginServer(EaServer):
   theater = Theater.objects.get(name='ra3')
   def connectionMade(self):
      EaServer.connectionMade(self)
      self.log = util.getLogger('login.ra3', self)
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

   def connectionMade(self):
      ServerFactory.connectionMade(self)
      self.log = util.getLogger('gamespy.ra3Serv', self)

   def buildProtocol(self, addr):
      p = ServerFactory.buildProtocol(self, addr)
      p.theater = Theater.getTheater(gameId)
      return p

## TODO: should this really be game-specific?
class QueryMasterFactory(ServerFactory):
   protocol = gamespy.master.QueryMaster
   gameName = gameId

class Service(MultiService):
   def __init__(self, addresses=None):
      MultiService.__init__(self)
      sCtx = OpenSSLContextFactoryFactory.getFactory('fesl.ea.com')

      ## all port 80 services are currently merged into one server on 8001. apache must be set up to use rewriterules (for /u downloads)
      ## and name-based virtual hosting (for SOAP hosts) in order to redirect from port 80 to 8001
      self.addService(TCPServer(8001, gamespy.webServices.WebServer()))

      ## TODO: redalert3pc.natneg{1,2,3}.gamespy.com
      ## This is a pretty simple service that allows 2 endpoints to udp punch thru their NAT routers.
      ## Hosted on UDP port 27901.
      ## see gsnatneg.c by aluigi for details on implementation

      self.addService(UDPServer(27900, gamespy.master.HeartbeatMaster()))

      ## gsauth runs on a variety of ports in 99XY range
      self.addService(TCPServer(9955, gamespy.auth.GamespyAuthFactory()))

      address = ('cncra3-pc.fesl.ea.com', 18840)
      sFact = RedAlert3LoginFactory()
      #sFact = makeTLSFwdFactory('login.ra3cli', 'login.ra3srv')(*address)
      self.addService(SSLServer(addresses[0][1], sFact, sCtx))

      address = ('peerchat.gamespy.com', 6667)
      sFact = gamespy.peerchat.PeerchatFactory()
      #sFact = gamespy.peerchat.ProxyPeerchatServerFactory(gameId, *address)
      self.addService(TCPServer(address[1], sFact))

      from ...gamespy.cipher import getMsName
      address = (getMsName(gameId), 28910)
      sFact = QueryMasterFactory()
      #sFact = gamespy.master.ProxyMasterServerFactory(gameId, *address)
      self.addService(TCPServer(address[1], sFact))

      address = ('gpcm.gamespy.com', 29900)
      sFact = gamespy.gpcm.ComradeFactory()
      #sFact = makeTCPFwdFactory('gamespy.gpcm.client', 'gamespy.gpcm.server')(*address)
      self.addService(TCPServer(address[1], sFact))
