import random
import string

from twisted.application.internet import TCPServer, UDPServer
from twisted.internet.protocol import ServerFactory
from twisted.application.service import MultiService
from twisted.protocols.portforward import ProxyClient, ProxyServer

from ..login import LoginServer
from ...util.fwdserver import makeTCPFwdFactory
from ..master import makeRecv, ProxyMasterServerFactory
from ..peerchat import ProxyPeerchatServerFactory
from ..message import GamespyMessage

gameId = 'menofwaras'

class MowLoginServer(LoginServer):
   def recv_registercdkey(self, msg):
      #[[('registercdkey', ''), ('sesskey', '14734748'), ('cdkeyenc', 'VcuyoQaIr[Q1Ij2oe5[VOJYkMA__'), ('id', '2')]]
      self.sendMsg(GamespyMessage([('rc', ''), ('id', '2')]))
   
   def recv_getprofile(self, msg):
      #[[('getprofile', ''), ('sesskey', '14734748'), ('profileid', '37347566'), ('id', '3')]
      self.sendMsg(GamespyMessage([
         ('pi', ''),
         ('profileid', '31317566'),
         ('nick', 'Dummy Nickname'),
         ('userid', '31081456'),
         ('sig', 'addf62001720ffbac4459ec2f5005643'),
         ('uniquenick', 'DummyUniqueNick'),
         ('p/d', '0'),
         ('firstname', 'John'),
         ('lastname', 'Public'),
         ('homepage', 'your.webpage.url'),
         ('zipcode', '97123'),
         ('countrycode', 'US'),
         ('birthday', '202115005'),
         ('sex', '0'),
         ('pmask', '-33'),
         ('conn', '5'),
         ('mp', '4'),
         ('lon', '0.000000'),
         ('lat', '0.000000'),
         ('loc', ''),
         ('id', '3'),
      ]))
      
class MowLoginServerFactory(ServerFactory):
   protocol = MowLoginServer
   gameId = gameId
   
class Service(MultiService):
   def __init__(self, **options):
      MultiService.__init__(self)

      address = ('gpcm.gamespy.com', 29900)
      sFact = MowLoginServerFactory()
      #sFact = makeTCPFwdFactory('gamespy.gpcmCli', 'gamespy.gpcmSrv', makeRecv(ProxyClient), makeRecv(ProxyServer))(*address)
      self.addService(TCPServer(address[1], sFact))
      
      address = ('peerchat.gamespy.com', 6667)
      sFact = ProxyPeerchatServerFactory(gameId, *address)
      #sFact = makeTCPFwdFactory('gamespy.peerCli', 'gamespy.peerSrv', makeRecv(ProxyClient, True), makeRecv(ProxyServer, True))(*address)
      self.addService(TCPServer(address[1], sFact))

      address = ('%s.gamestats.gamespy.com' % (gameId,), 29920)
      sFact = makeTCPFwdFactory('gamespy.stat1cli', 'gamespy.stat1srv', makeRecv(ProxyClient, True), makeRecv(ProxyServer, True))(*address)
      self.addService(TCPServer(address[1], sFact))
      
      # ('menofwarpc.master.gamespy.com', 29910), # 29910 UDP is keycheck ('gamespy' xor), 27900 for gameinfo/natneg(?)
      address = ('%s.master.gamespy.com' % (gameId,), 28910)
      sFact = makeTCPFwdFactory('gamespy.masterCli', 'gamespy.masterSrv', makeRecv(ProxyClient, True), makeRecv(ProxyServer, True))(*address)
      #sFact = ProxyMasterServerFactory(gameId, *address)
      self.addService(TCPServer(address[1], sFact))

      # ('menofwarpc.available.gamespy.com', 27900),
      #self.addService(TCPServer(80, DownloadsServerFactory()))
      #self.addService(UDPServer(27900, AvailableServer()))
