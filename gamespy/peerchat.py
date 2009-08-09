import logging

from twisted.words.protocols.irc import IRC
from twisted.internet.protocol import ServerFactory
from twisted.protocols.portforward import *

import db
from cipher import *

class Peerchat(IRC):
   def connectionMade(self):
      IRC.connectionMade(self)
      self.sCipher = self.cipherFactory.getCipher()
      self.cCipher = self.cipherFactory.getCipher()
      self.doCrypt = False
      self.log  = logging.getLogger('gamespy.peerchat.{0}'.format(self.factory.gameName))

   def dataReceived(self, data):
      if self.doCrypt:
         data = self.cCipher.crypt(data)
      self.log.debug('recv IRC: {0}'.format(repr(data)))
      IRC.dataReceived(self, data)
   
   def sendLine(self, line):
      data = line + '\n' # peerchat doesn't send \r
      self.log.debug('send IRC: {0}'.format(repr(data)))
      if self.doCrypt:
         data = self.sCipher.crypt(data)
      #IRC.sendLine(self, line) # NONO! \r\n won't get encrypted!!
      self.transport.write(data)
      
   # TODO: enumerate cmd ids and use more meaningful names
   
   # note that trailing params come as last element in 'params'
   
   def irc_CRYPT(self, prefix, params):
      self.sendMessage('705', '*', self.cCipher.challenge, self.sCipher.challenge, prefix='s')
      self.doCrypt = True
      
   def irc_USRIP(self, prefix, params):
         self.sendMessage('302', '', ':=+@{0}'.format(self.transport.getPeer().host), prefix='s')
   
   def irc_USER(self, prefix, params):
      #'XflsaqOa9X|165580976' is encodedIp|GSProfileId aka user, '127.0.0.1', 'peerchat.gamespy.com', 'a69b3a7a0837fdcd763fdeb0456e77cb' is cdkey
      self.user, ip, host, cdkey = params
   
   def irc_NICK(self, prefix, params):
      self.nick = params[0]
      self.sendMessage('001', self.nick, ':Welcome to the Matrix {0}'.format(self.nick))
      self.sendMessage('002', self.nick, ':Your host is xs5, running version 1.0') # TODO
      self.sendMessage('003', self.nick, ':This server was created Fri Oct 19 1979 at 21:50:00 PDT') # TODO
      self.sendMessage('004', self.nick, 's 1.0 iq biklmnopqustvhe')
      self.sendMessage('375', self.nick, ':(M) Message of the day -')
      self.sendMessage('372', self.nick, ':Welcome to GameSpy')
      self.sendMessage('376', self.nick, ':End of MOTD command')
      
   def irc_CDKEY(self, prefix, params):
      self.sendMessage('706', self.nick, '1', ':Authenticated')
      
   def irc_JOIN(self, prefix, params):
      chan = params[0]
      chanTokens = chan.split('!')
      if chanTokens[0] == '#GPG': # chat lobby
         chanId = chanTokens[1]
         self.channel = db.getChannel(id=chanId)
         self.sendMessage('JOIN', ':#GPG!{0}'.format(chanId), prefix=self.getClientPrefix())
      elif chanTokens[0] == '#GSP': # we're joining a game lobby
         self.channel = db.createChannel(name=chan, prettyName=chan, game=db.getGameInfo(name=chanTokens[1]))
         self.sendMessage('JOIN', ':'+params[0], prefix=self.getClientPrefix())
         
   def getClientPrefix(self):
      # follows RFC prefix BNF
      return '{0}!{1}@*'.format(self.nick, self.user)
         
   def irc_PART(self, prefix, params):
      pass
   
   def irc_QUIT(self, prefix, params):
      pass
   
   def irc_MODE(self, prefix, params):
      chan = self.channel.name
      if chan.startswith('#GPG'):
         self.send_RPL_TOPIC('Click on the "Game Info" button at the top of your screen for '
                             'the latest information on patches, add-on files, interviews, '
                             'strategy guides and more!  It`s all there!')
         self.sendMessage('333', self.nick, chan, 'SERVER', '1245741924', prefix='s')
         # don't forget self in this list!
         self.send_RPL_NAMEREPLY((self.nick,))
         self.send_RPL_ENDOFNAMES()
      elif chan.startswith('#GSP'):
         self.send_RPL_NOTOPIC()
         #self.sendNamesList()
         self.send_RPL_NAMEREPLY(('@'+self.nick,))
         self.send_RPL_ENDOFNAMES()
         
   def irc_UTM(self, prefix, params):
      if params and params[-1].startswith('MAP'):
         self.sendMessage('UTM', self.nick, prefix=self.getClientPrefix())
         
   def irc_TOPIC(self, prefix, params):
      pass # TODO: analyze and implement
         
   def irc_GETCKEY(self, prefix, params):
      pass # TODO: analyze and implement
   
   def irc_SETCKEY(self, prefix, params):
      pass # TODO: analyze and implement
   
   def send_RPL_NOTOPIC(self):
         self.sendMessage('331', self.nick, self.channel.name, ':No topic is set', prefix='s')
   def send_RPL_TOPIC(self, topic):
         self.sendMessage('332', self.nick, self.channel.name, ':'+topic, prefix='s')
   def send_RPL_NAMEREPLY(self, names):
         self.sendMessage('353', self.nick, '*', self.channel.name, ':'+' '.join(names), prefix='s')
   def send_RPL_ENDOFNAMES(self):
         self.sendMessage('366', self.nick, self.channel.name, ':End of NAMES list', prefix='s')
      

class PeerchatFactory(ServerFactory):
   protocol = Peerchat
   
   def __init__(self,  gameName):
      self.gameName = gameName
      
   def buildProtocol(self, addr):
      inst = ServerFactory.buildProtocol(self, addr)
      inst.cipherFactory = PeerchatCipherFactory(db.getGameKey(self.gameName))
      return inst
   
#---------- PROXY CLASSES --------
class CipherProxy:
   def __init__(self, server, client, gamekey):
      self.clientIngress = PeerchatCipher(server, gamekey)
      self.clientEgress = PeerchatCipher(server, gamekey)
      self.serverIngress = PeerchatCipher(client ,gamekey)
      self.serverEgress = PeerchatCipher(client ,gamekey)
   
   def recvFromServer(self, data):
      unenc = self.serverIngress.crypt(data)
      log = logging.getLogger('gamespy.chatCli') #HACKy
      log.debug('received: '+repr(unenc))
      if 'Unknown CD Key' in unenc:
         unenc = re.sub(r'(:s 706 \w+) .*', r'\1 1 :Authenticated', unenc)
         log.debug('but sending this instead: %s', unenc)
      return self.serverEgress.crypt(unenc)
   
   def recvFromClient(self, data):
      unenc = self.clientIngress.crypt(data)
      log = logging.getLogger('gamespy.chatServ') #HACKy
      log.debug('received: '+repr(unenc))
      #patches follow
      return self.clientEgress.crypt(unenc)

class ProxyPeerchatClient(ProxyClient):
   cipher = None #a little HACKy
   def dataReceived(self, data):
      # first receive should have challenges
      if not self.cipher:
         logging.getLogger('gamespy').debug(repr(data))
         sChal = data.split(' ')[-2].strip()
         cChal = data.split(' ')[-1].strip()
         self.cipher = CipherProxy(sChal, cChal, self.peer.gamekey)
      else:
         data = self.cipher.recvFromServer(data)
      ProxyClient.dataReceived(self, data)
   
class ProxyPeerchatClientFactory(ProxyClientFactory):
   protocol = ProxyPeerchatClient
   log = logging.getLogger('gamespy.chatCli')
   
class ProxyPeerchatServer(ProxyServer):
   clientProtocolFactory = ProxyPeerchatClientFactory
   def dataReceived(self, data):
      if self.peer.cipher:
         data = self.peer.cipher.recvFromClient(data)
      else:
         logging.getLogger('gamespy').debug(repr(data))
      ProxyServer.dataReceived(self, data)

class ProxyPeerchatServerFactory(ProxyFactory):
   protocol = ProxyPeerchatServer
   log = logging.getLogger('gamespy.chatSrv')
   
   def __init__(self, gameName, host, port):
      ProxyFactory.__init__(self, host, port)
      self.gameName = gameName
      
   def buildProtocol(self, addr):
      p = ProxyFactory.buildProtocol(self, addr)
      p.gamekey = db.getGameKey(self.gameName)
      return p
   