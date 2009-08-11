from twisted.internet.protocol import Protocol, ServerFactory

class LoginServer(Protocol):
   def connectionMade(self):
      Protocol.connectionMade(self)
      self.session = self.theater.Connect()
      
   def dataReceived(self, data):
      try:
         for msg in parseMsgs(data):
            ep = '{0.host}:{0.port}'.format(self.transport.getPeer())
            self.factory.log.debug('received ({0}): {1}'.format(ep, msg.data))
            method = getattr(self, 'cmd_{0}'.format(msg.data[0][0]), None)
            if method:
               method(msg)
            else:
               self.factory.log.debug('unhandled: {0}'.format(msg.data))
      except:
         raise
      
   def cmd_ka(self, msg):
      self.sChal = ''.join(random.sample(string.ascii_uppercase, 10))
      self.sendMsg(GamespyMessage([
         ('lc', '1'),
         ('challenge', self.sChal),
         ('id', '1'),
      ]))
      
   def sendMsg(self, msg):
      self.factory.log.debug('sent: {0}'.format(msg.data))
      self.transport.write(repr(msg))
