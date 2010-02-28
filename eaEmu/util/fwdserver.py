from __future__ import absolute_import
from twisted.protocols.portforward import *
from twisted.internet import reactor
from twisted.internet.ssl import ClientContextFactory
from . import getLogger
from . import hexdump

def defDRClient(self, data):
   self.log.debug('upstream responded: \n{0}'.format(hexdump(data)))
   ProxyClient.dataReceived(self, data)

def defDRServer(self, data):
   self.log.debug('FwdServer received: \n{0}'.format(hexdump(data)))
   ProxyServer.dataReceived(self, data)

def makeTCPFwdFactory(clientLog, serverLog, clientRecv=defDRClient, serverRecv=defDRServer):
   class Client(ProxyClient):
      dataReceived = clientRecv
      def connectionMade(self):
         ProxyClient.connectionMade(self)
         self.log = getLogger(clientLog, self)
   class CF(ProxyClientFactory):
      protocol = Client
   class Serv(ProxyServer):
      clientProtocolFactory = CF
      dataReceived = serverRecv
      def connectionMade(self):
         ProxyServer.connectionMade(self)
         self.log = getLogger(serverLog, self)
   class SF(ProxyFactory):
      protocol = Serv
   return SF

def makeTLSFwdFactory(clientLog, serverLog, clientRecv=defDRClient, serverRecv=defDRServer):
   class Client(ProxyClient):
      dataReceived = clientRecv
      def connectionMade(self):
         ProxyClient.connectionMade(self)
         self.log = getLogger(clientLog, self)
   class CF(ProxyClientFactory):
      protocol = Client
   class Serv(ProxyServer):
      clientProtocolFactory = CF
      dataReceived = serverRecv
      def connectionMade(self):
         self.log = getLogger(serverLog, self)
         self.transport.pauseProducing()
         client = self.clientProtocolFactory()
         client.setServer(self)
         reactor.connectSSL(self.factory.host, self.factory.port, client, ClientContextFactory())
   class SF(ProxyFactory):
      protocol = Serv
   return SF
