from __future__ import absolute_import
import random
import string

from twisted.internet.protocol import Protocol, ServerFactory

from .message import MessageFactory
from .cipher import gs_login_proof
from ..util.timer import KeepaliveService
from .. import util

class LoginServer(Protocol):
   def connectionMade(self):
      self.log = util.getLogger('gamespy.login', self)
      self.loggedIn = False
      def sendKa():
         self.sendMsg(MessageFactory.getMessage([
            ('ka', ''),
         ]))
         self.kaService.alive() ## expects no reply
      self.kaService = KeepaliveService(sendKa, 90, self.transport.loseConnection)
      Protocol.connectionMade(self)

   def connectionLost(self, reason):
      self.kaService.stopService()
      Protocol.connectionLost(self, reason)

   def makeChallenge(self):
      #return 'SCHALLENGE'
      return ''.join(random.choice(string.ascii_uppercase) for _ in range(10))

   def dataReceived(self, data):
      self.kaService.alive()
      try:
         for msg in MessageFactory.getMessages(data):
            ep = '{0.host}:{0.port}'.format(self.transport.getPeer())
            self.log.debug('received ({0}): {1}'.format(ep, msg))
            method = getattr(self, 'recv_{0}'.format(msg._pairs[0][0]), None)
            if method:
               method(msg)
            else:
               self.log.debug('unhandled: {0}'.format(msg))
      except:
         raise

   def recv_ka(self, msg):
      # ka = Keep-Alive, but also used to trigger login
      # TODO: actually disconnect users that dont send this regularly
      if self.loggedIn:
         self.kaService.alive()
      else:
         self.sChal = self.makeChallenge()
         self.sendMsg(MessageFactory.getMessage([
            ('lc', '1'),
            ('challenge', self.sChal),
            ('id', '1'),
         ]))

   def recv_login(self, msg):
      # [('login', ''), ('challenge', 'Qf7C8OnFz4HS9iK0HgNiebY5wamfYCJb'), ('uniquenick', 'MyEnemyMyFriend'),
      # ('partnerid', '0'), ('response', '15d07ddb2c74f03486391664a5cb5a13'), ('port', '6500'),
      # ('productid', '2544'), ('gamename', 'menofwarpcd'), ('namespaceid', '1'), ('sdkrevision', '11'),
      # ('quiet', '0'), ('id', '1')]
      user =  msg.uniquenick
      pwd = 'a' # HACK
      self.sendMsg(MessageFactory.getMessage([('blk', '0'), ('list', '')]))
      self.sendMsg(MessageFactory.getMessage([('bdy', '0'), ('list', '')])) ## buddy list
      self.sendMsg(MessageFactory.getMessage([
         ('lc', '2'),
         ('sesskey', str(random.getrandbits(32))),
         ('proof', gs_login_proof(pwd, user, msg.challenge, self.sChal)),
         ('userid', str(random.getrandbits(32))),
         ('profileid', str(random.getrandbits(32))),
         ('uniquenick', user),
         ('lt', 'XdR2LlH69XYzk3KCPYDkTY__'),
         ('id', '1')
      ]))

      self.loggedIn = True
      self.kaService.startService()

   def sendMsg(self, msg):
      self.log.debug('sent: {0}'.format(msg))
      self.transport.write(repr(msg))
