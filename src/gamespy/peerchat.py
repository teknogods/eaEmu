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
      self.ircUser, ip, host, cdkey = params
   
   def irc_NICK(self, prefix, params):
      # TODO: assert that this user has logged in to the main login server so that impersonation
      # isn't possible like it is for the real gamespy
      self.nick = params[0]
      # TODO: are personas available only for newer games?
      # solution is to just create 1 persona by default for each login
      self.user = db.Persona.objects.get(name=self.nick).user
      
      #HACKy way to maintain a list of all client connections
      if not hasattr(self.factory, 'conns'):
         self.factory.conns = {}
      self.factory.conns[self.user] = self
      
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
      # TODO? : support joining multiple channels
      chan = params[0]
      chanTokens = chan.split('!')
      if chanTokens[0] == '#GPG': # chat lobby
         chanId = chanTokens[1]
         self.channel = db.Channel.objects.get(id=chanId)
      elif chanTokens[0] == '#GSP': # we're joining a game lobby
         rSet = db.Channel.objects.filter(name=chan)
         if len(rSet) == 0:
            self.channel = db.Channel.objects.create(name=chan, prettyName=chan, game=db.Game.objects.get(name=chanTokens[1]))
         elif len(rSet) == 1:
            self.channel = rSet[0]
         else: # duplicate channels!!
            assert false
      self.channel.users.add(self.user)
      self.sendToChannel(self.channel, 'JOIN', ':'+self.channel.name) # notify everybody
      if chan.startswith('#GPG'):
         self.send_RPL_TOPIC('Click on the "Game Info" button at the top of your screen for '
                             'the latest information on patches, add-on files, interviews, '
                             'strategy guides and more!  It`s all there!')
         self.sendMessage('333', self.nick, chan, 'SERVER', '1245741924', prefix='s')
         # don't forget self in this list!
         self.send_RPL_NAMEREPLY((self.nick,))
      elif chan.startswith('#GSP'):
         self.send_RPL_NOTOPIC()
         #self.sendNamesList()
         self.send_RPL_NAMEREPLY(('@'+self.nick,))
      self.send_RPL_ENDOFNAMES()
      
   def sendToChannel(self, channel, *params):
      #TODO: this is probably a very inefficient way to do this...
      # grab all users that are in the given channel
      for user in channel.users.all():
         if user == self.user: # exclude self
            if params[0] == 'PRIVMSG':
               continue
         conn = self.factory.conns[user] # HACKy
         # send them the message
         conn.sendMessage(prefix=self.getClientPrefix(), *params)
         
   def getClientPrefix(self):
      # follows RFC prefix BNF
      return '{0}!{1}@*'.format(self.nick, self.ircUser)
         
   def irc_PART(self, prefix, params):
      chan = params[0]
      self.channel.users.remove(self.user)
      self.sendToChannel(self.channel, 'PART', self.channel.name, ':') # parting msg usually is trailing
   
   def irc_QUIT(self, prefix, params):
      pass
   
   def irc_MODE(self, prefix, params):
      self.send_RPL_CHANNELMODEIS(self.channel)
         
   def irc_UTM(self, prefix, params):
      if params and params[-1].startswith('MAP'):
         self.sendMessage('UTM', self.nick, prefix=self.getClientPrefix())
         
   def irc_TOPIC(self, prefix, params):
      pass # TODO: analyze and implement
         
   def irc_GETCKEY(self, prefix, params):
      chan, user, rId, zero, fields = params
      fields  = fields.split('\\')[1:]
      print fields
      # 702 = RPL_GETCKEY? -- not part of RFC 1459
      # TODO: query db for the requested fields and return, store them from SETCKEY
      if fields[0] == 'username':
         self.sendMessage('702', self.nick, chan, 'Keb', rId, ':\\{0}\\'.format(self.ircUser), prefix='s') # just return self
         self.sendMessage('702', self.nick, chan, 'pseudoUser', rId, ':\\{0}\\'.format('*|*'), prefix='s')
         self.sendMessage('703', self.nick, chan, rId, ':End of GETCKEY', prefix='s')
      elif fields[0] == 'b_clanName':
         self.sendMessage('702', self.nick, chan, 'Keb', rId, ':\\\\0\\0\\5\\3\\-1\\-1\\-1\\-1\\-1\\-1\\2', prefix='s')
         self.sendMessage('702', self.nick, chan, 'pseudoUser', rId, ':\\\\0\\0\\5\\3\\-1\\-1\\-1\\-1\\-1\\-1\\2', prefix='s')
         self.sendMessage('703', self.nick, chan, rId, ':End of GETCKEY', prefix='s')
                       
# client sends:
#'GETCKEY #GPG!2170 * 028 0 :\\username\\b_flags' # request for all (*) users, request id 28, username and b_flags are requested fields
#'SETCKEY #GPG!2170 Keb :\\b_clanName\\\\b_arenaTeamID\\0\\b_locale\\0\\b_wins\\0\\b_losses\\1\\b_rank1v1\\-1\\b_rank2v2\\-1\\b_clan1v1\\-1\\b_clan2v2\\-1\\b_elo1v1\\-1\\b_elo2v2\\-1\\b_onlineRank\\1'
#'GETCKEY #GPG!2170 * 029 0 :\\b_clanName\\b_arenaTeamID\\b_locale\\b_wins\\b_losses\\b_rank1v1\\b_rank2v2\\b_clan1v1\\b_clan2v2\\b_elo1v1\\b_elo2v2\\b_onlineRank'
   
#':s 702 Keb #GPG!2170 Keb 028 :\\Xs1pfFWvpX|165580976\\'
#':s 702 Keb #GPG!2170 WarlordSteve 028 :\\XlWG4vFs4X|219360647\\'
#':s 702 Keb #GPG!2170 antoinec 028 :\\Xa4uWslfGX|175086932\\'
#':s 702 Keb #GPG!2170 ChatMonitor-gs 028 :\\XaaaaaaaaX|25677635\\'
#':s 703 Keb #GPG!2170 028 :End of GETCKEY\n'

#':s 702 #GPG!2170 #GPG!2170 Keb BCAST :\\b_clanName\\\\b_arenaTeamID\\0\\b_locale\\0\\b_wins\\0\\b_losses\\1\\b_rank1v1\\-1\\b_rank2v2\\-1\\b_clan1v1\\-1\\b_clan2v2\\-1\\b_elo1v1\\-1\\b_elo2v2\\-1\\b_onlineRank\\1\n'
#':s 702 Keb #GPG!2170 Keb 029 :\\\\0\\0\\0\\1\\-1\\-1\\-1\\-1\\-1\\-1\\1'
#':s 702 Keb #GPG!2170 WarlordSteve 029 :\\\\0\\0\\5\\3\\-1\\-1\\-1\\-1\\-1\\-1\\2'
#':s 702 Keb #GPG!2170 antoinec 029 :\\\\0\\0\\19\\44\\-1\\3603\\-1\\-1\\-1\\986\\8'
#':s 702 Keb #GPG!2170 ChatMonitor-gs 029 :\\\\\\\\\\\\\\\\\\\\\\\\'
#':s 703 Keb #GPG!2170 029 :End of GETCKEY\n'
   
   
   
   
   def irc_SETCKEY(self, prefix, params):
      pass # TODO: analyze and implement
   
   def irc_PRIVMSG(self, prefix, params):
      # chan might be a comma separated list of users and/or channels
      receivers, msg = params
      for rcvr in receivers.split(','):
         if rcvr.startswith('#'): # channel
            # TODO? : support channel masks.
            self.sendToChannel(db.Channel.objects.get(name=rcvr), 'PRIVMSG', rcvr, ':'+msg)
         else: # user
            pass # TODO
   
   def send_RPL_NOTOPIC(self):
      self.sendMessage('331', self.nick, self.channel.name, ':No topic is set', prefix='s')
   def send_RPL_TOPIC(self, topic):
      self.sendMessage('332', self.nick, self.channel.name, ':'+topic, prefix='s')
   def send_RPL_NAMEREPLY(self, names):
      self.sendMessage('353', self.nick, '*', self.channel.name, ':'+' '.join(['pseudoUser'] + [x.persona_set.get(selected=True).name for x in self.channel.users.all()]), prefix='s')
   def send_RPL_ENDOFNAMES(self):
      self.sendMessage('366', self.nick, self.channel.name, ':End of NAMES list', prefix='s')
   def send_RPL_CHANNELMODEIS(self, channel):
      self.sendMessage('324', self.nick, channel.name, channel.flags, prefix='s')
      

class PeerchatFactory(ServerFactory):
   protocol = Peerchat
   
   def __init__(self,  gameName):
      self.gameName = gameName
      
   def buildProtocol(self, addr):
      inst = ServerFactory.buildProtocol(self, addr)
      inst.cipherFactory = PeerchatCipherFactory(db.Game.getKey(self.gameName))
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
      p.gamekey = db.Game.getKey(self.gameName)
      return p
   