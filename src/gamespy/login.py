import random
import string

from twisted.internet.protocol import Protocol, ServerFactory

from message import MessageFactory

class LoginServer(Protocol):
   #def connectionMade(self):
      #Protocol.connectionMade(self)
      #self.session = self.theater.Connect()

   def makeChallenge(self):
      #return 'SCHALLENGE'
      return ''.join(random.choice(string.ascii_uppercase) for _ in range(10))

   def dataReceived(self, data):
      try:
         for msg in MessageFactory.getMessages(data):
            ep = '{0.host}:{0.port}'.format(self.transport.getPeer())
            self.factory.log.debug('received ({0}): {1}'.format(ep, msg.data))
            method = getattr(self, 'recv_{0}'.format(msg.data[0][0]), None)
            if method:
               method(msg)
            else:
               self.factory.log.debug('unhandled: {0}'.format(msg.data))
      except:
         raise

   def recv_ka(self, msg):
      # ka = Keep-Alive, but also used to trigger login
      # TODO: actually disconnect users that dont send this regularly
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
      user =  msg.map['uniquenick']
      pwd = 'pass'
      self.sendMsg(MessageFactory.getMessage([('blk', '0'), ('list', '')]))
      self.sendMsg(MessageFactory.getMessage([('bdy', '0'), ('list', '')])) ## buddy list
      self.sendMsg(MessageFactory.getMessage([
         ('lc', '2'),
         ('sesskey', str(random.getrandbits(32))),
         ('proof', gs_login_proof(pwd, user, msg.map['challenge'], self.sChal)),
         ('userid', str(random.getrandbits(32))),
         ('profileid', str(random.getrandbits(32))),
         ('uniquenick', user),         ('lt', 'XdR2LlH69XYzk3KCPYDkTY__'),
         ('id', '1')
      ]))

   def sendMsg(self, msg):
      self.factory.log.debug('sent: {0}'.format(msg.data))
      self.transport.write(repr(msg))
