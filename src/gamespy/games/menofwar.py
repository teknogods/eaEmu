import random
import string

from twisted.internet.protocol import ServerFactory
from twisted.application.service import MultiService

from matchmaking import *
from gamespy import *
from fwdserver import *

gameId = 'menofwarpc'

class MowLoginServer(gamespy.LoginServer):
   def cmd_login(self, msg):
      # [('login', ''), ('challenge', 'Qf7C8OnFz4HS9iK0HgNiebY5wamfYCJb'), ('uniquenick', 'MyEnemyMyFriend'),
      # ('partnerid', '0'), ('response', '15d07ddb2c74f03486391664a5cb5a13'), ('port', '6500'),
      # ('productid', '2544'), ('gamename', 'menofwarpcd'), ('namespaceid', '1'), ('sdkrevision', '11'),
      # ('quiet', '0'), ('id', '1')]
      user =  msg.map['uniquenick']
      pwd = 'pass'
      self.sendMsg(GamespyMessage([('blk', '0'), ('list', '')]))
      self.sendMsg(GamespyMessage([('bdy', '0'), ('list', '')]))
      self.sendMsg(GamespyMessage([
         ('lc', '2'),
         ('sesskey', str(random.getrandbits(32))),
         ('proof', gs_login_proof(pwd, user, msg.map['challenge'], self.sChal)),
         ('userid', str(random.getrandbits(32))),
         ('profileid', str(random.getrandbits(32))),
         ('uniquenick', user),         ('lt', 'XdR2LlH69XYzk3KCPYDkTY__'),
         ('id', '1')
      ]))
   
   def cmd_registercdkey(self, msg):
      #[[('registercdkey', ''), ('sesskey', '14734748'), ('cdkeyenc', 'VcuyoQaIr[Q1Ij2oe5[VOJYkMA__'), ('id', '2')]]
      self.sendMsg(GamespyMessage([('rc', ''), ('id', '2')]))
   
   def cmd_getprofile(self, msg):
      #[[('getprofile', ''), ('sesskey', '14734748'), ('profileid', '37347566'), ('id', '3')]
      self.sendMsg(GamespyMessage([
         ('pi', ''),
         ('profileid', '37347566'),
         ('nick', 'Ivarr Morthvargr'),
         ('userid', '32082456'), ('sig', 'addf62001720ffbac4459ec2f5005643'),
         ('uniquenick', 'IvarrMorthvargr'),
         ('p/d', '0'),
         ('firstname', 'Tim'),
         ('lastname', 'Myers II'),
         ('homepage', 'www.amalekite.com'),
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
   log = logging.getLogger('gamespy.mowServ')
   gameId = gameId
   
   def buildProtocol(self, addr):
      p = ServerFactory.buildProtocol(self, addr)
      p.theater = Theater.getTheater(self.gameId)
      return p
   
class MowService(MultiService):
   def __init__(self, address=None):
      MultiService.__init__(self)
      
      # login server gpcm.gamespy.com
      address = ('207.38.11.34', 29900)
      sFact = MowLoginServerFactory()
      #sFact = makeTCPFwdFactory('gamespy.gpcmCli', 'gamespy.gpcmSrv', makeRecv(ProxyClient), makeRecv(ProxyServer))(*address)
      self.addService(TCPServer(address[1], sFact))
      
      # ('menofwarpc.gamestats.gamespy.com', 29920),
      address = ('207.38.11.49', 29920)
      sFact = makeTCPFwdFactory('gamespy.stat1cli', 'gamespy.stat1srv', makeRecv(ProxyClient, True), makeRecv(ProxyServer, True))(*address)
      self.addService(TCPServer(address[1], sFact))
      
      # ('menofwarpc.master.gamespy.com', 29910), # 29910 is keycheck, 27900 for natneg
      address = ('207.38.11.14', 28910)
      #sFact = makeTCPFwdFactory('gamespy.masterCli', 'gamespy.masterSrv', recvMasterCli, recvMasterSrv)(*address)
      sFact = ProxyMasterServerFactory(gameId, *address)
      self.addService(TCPServer(address[1], sFact))

      # peerchat.gamespy.com
      address = ('207.38.11.136', 6667)
      sFact = ProxyPeerchatServerFactory(*address)
      self.addService(TCPServer(address[1], sFact))

      # ('menofwarpc.available.gamespy.com', 27900),
      #self.addService(TCPServer(80, DownloadsServerFactory()))
      self.addService(UDPServer(27900, AvailableServer()))