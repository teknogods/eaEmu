from twisted.protocols.portforward import *
from twisted.internet import reactor
from twisted.internet.ssl import ClientContextFactory

import util

def defDRClient(self, data):
   self.factory.log.debug('upstream responded: "{0}"'.format(data))
   ProxyClient.dataReceived(self, data)

def defDRServer(self, data):
   self.factory.log.debug('FwdServer received: "{0}"'.format(data))
   ProxyServer.dataReceived(self, data)

def makeTCPFwdFactory(clientLog, serverLog, clientRecv=defDRClient, serverRecv=defDRServer):
   class Client(ProxyClient):
      dataReceived = clientRecv
   class CF(ProxyClientFactory):
      protocol = Client
      def connectionMade(self):
         ProxyClientFactory.connectionMade(self)
         self.log = util.getLogger(clientLog, self)
   class Serv(ProxyServer):
      clientProtocolFactory = CF
      dataReceived = serverRecv
   class SF(ProxyFactory):
      protocol = Serv
      def connectionMade(self):
         ProxyFactory.connectionMade(self)
         self.log = util.getLogger(serverLog, self)
   return SF

def makeTLSFwdFactory(clientLog, serverLog, clientRecv=defDRClient, serverRecv=defDRServer):
   class Client(ProxyClient):
      dataReceived = clientRecv
   class CF(ProxyClientFactory):
      protocol = Client
      def connectionMade(self):
         ProxyClientFactory.connectionMade(self)
         self.log = util.getLogger(clientLog, self)
   class Serv(ProxyServer):
      clientProtocolFactory = CF
      dataReceived = serverRecv
      def connectionMade(self):
         self.transport.pauseProducing()
         client = self.clientProtocolFactory()
         client.setServer(self)
         reactor.connectSSL(self.factory.host, self.factory.port, client, ClientContextFactory())
   class SF(ProxyFactory):
      protocol = Serv
      def connectionMade(self):
         ProxyFactory.connectionMade(self)
         self.log = util.getLogger(serverLog, self)
   return SF
