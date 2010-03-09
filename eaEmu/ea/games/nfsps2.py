import logging
import base64

from twisted.application.internet import SSLServer, TCPServer, UDPServer
from twisted.internet.protocol import ServerFactory
from twisted.application.service import MultiService

#from ea.login import OpenSSLContextFactoryFactory, EaServer, EaLoginMessage
from ea.login import *
from ea.message import MessageFactory
from ea.db import *
import util

from pcburnout08 import Burnout08TheaterServer

class LoginServer(EaServer):
   theater = Theater.getTheater('nfsps2')

   def connectionMade(self):
      EaServer.connectionMade(self)
      self.log = util.getLogger('login.nfsps2', self)
      self.msgFactory = MessageFactory(self.transport, EaLoginMessage)
      self.hlrFactory = MessageHandlerFactory(self, 'ea.games.redalert3.Ra3MsgHlr')


class LoginServerFactory(ServerFactory):
   protocol = LoginServer

class TheaterServer(Burnout08TheaterServer):#EaServer):
   theater = Theater.getTheater('nfsps2')
   log = util.getLogger('theater.nfsps2', self)

   def connectionMade(self):
      EaServer.connectionMade(self)

class TheaterServerFactory(ServerFactory):
   protocol = TheaterServer

def fwdDRS(self, data):
   self.factory.log.debug('server received: %s', data)
   ProxyServer.dataReceived(self, data)
def fwdDRC(self, data):
   self.factory.log.debug('client received: %s', data)
   ProxyClient.dataReceived(self, data)

class Service(MultiService):
   def __init__(self, addresses=None):
      MultiService.__init__(self)
      sCtx = OpenSSLContextFactoryFactory.getFactory('fesl.ea.com')

      addresses = dict(addresses)
      host = 'nfsps2-pc.fesl.ea.com'
      sFact = LoginServerFactory()
      #sFact = makeTLSFwdFactory('login.nfsps2.client', 'login.nfsps2.server', fwdDRC, fwdDRS)(*address)
      self.addService(SSLServer(addresses[host], sFact, sCtx))

      host = 'nfsps2-pc.theater.ea.com'
      sFact = TheaterServerFactory()
      self.addService(SSLServer(addresses[host], sFact, sCtx))

