from __future__ import absolute_import
from __future__ import print_function

from twisted.protocols.portforward import *
from twisted.application.service import MultiService
from twisted.application.internet import TCPServer

from ..db import Game
from .peerchat import *

class PeerchatProxyClient(ProxyClient):
   cipher = None ##a little HACKy

   def connectionMade(self):
      self.peer.setPeer(self)
      print('writing crypt')
      self.transport.write('CRYPT des 1 %s\n' % (self.peer.factory.gameName,))

   def dataReceived(self, data):
      print(repr(data))
      ## first receive should have challenges
      if not self.cipher:
         cryptInfo, data = data.split('\n', 1)
         sChal = cryptInfo.split(' ')[-2].strip()
         cChal = cryptInfo.split(' ')[-1].strip()
         self.cipher = CipherProxy(sChal, cChal, self.peer.factory.gameKey)
         ## only resume once crypt response was received
         self.peer.transport.resumeProducing()
      if data:
         data = self.cipher.serverIngress.crypt(data)
         print(repr(data))
         ProxyClient.dataReceived(self, data)

class PeerchatProxyClientFactory(ProxyClientFactory):
   protocol = PeerchatProxyClient

class PeerchatProxyServer(ProxyServer):
   clientProtocolFactory = PeerchatProxyClientFactory

   def connectionMade(self):
      self.transport.pauseProducing()
      client = self.clientProtocolFactory()
      client.setServer(self)

      from twisted.internet import reactor
      reactor.connectTCP(self.factory.host, self.factory.port, client)

   def dataReceived(self, data):
      print(repr(data))
      if self.peer.cipher:
         data = self.peer.cipher.clientEgress.crypt(data)
      ProxyServer.dataReceived(self, data)

class PeerchatProxyServerFactory(ProxyFactory):
   protocol = PeerchatProxyServer

   def __init__(self, gameName, host, port):
      ProxyFactory.__init__(self, host, port)
      self.gameName = gameName
      self.gameKey = Game.getKey(self.gameName)

class Service(MultiService):
   def __init__(self, **options):
      MultiService.__init__(self)
      self.addService(TCPServer(options['port'], PeerchatProxyServerFactory(options['game'], options['host'], 6667)))
