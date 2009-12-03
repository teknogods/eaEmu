from __future__ import print_function
import logging
import re

from twisted.words.protocols import irc
from twisted.words.protocols.irc import lowQuote
from twisted.internet.protocol import ServerFactory
from twisted.protocols.portforward import *
from twisted.words.service import IRCUser, WordsRealm, IRCFactory, Group
from twisted.cred.portal import Portal
from twisted.cred.checkers import ICredentialsChecker, InMemoryUsernamePasswordDatabaseDontUse
from twisted.cred import credentials
from zope.interface import implements
from twisted.internet import defer, threads
from twisted.words import iwords
from twisted.python import failure

from . import db
from .cipher import *
from .. import util
from ..util import aspects2 as aspects
from ..util.timer import KeepaliveService


@util.AttachMethod(db.Stats)
def dumpFields(self, fields, withNames=False):
   fieldVals = {}
   for fld in fields:
      if fld == 'username':
         ## this is pretty HACKy, but needed cuz i dont want to do a db query for the DbUser version
         ## of this object
         fieldVals[fld] = DbUser.__dict__['getIrcUserString'](self.persona.user)
      elif fld == 'b_arenaTeamID':
         val = getattr(self, fld)
         fieldVals[fld] = val and val.id or 0 # use zero if field is null (very rare case)
      else:
         fieldVals[fld] =getattr(self, fld, None) or '' ## None's become ''

   return ':\\' + '\\'.join(sum(
                                [[k, str(fieldVals[k])] for k in fields] if withNames else
                                [[str(fieldVals[k])] for k in fields],
                                []
   ))

class Peerchat(IRCUser, object):
   def connectionMade(self):
      IRCUser.connectionMade(self)
      peer = self.transport.getPeer()
      self.log = util.getLogger('gamespy.peerchat', self)

      ## some HACKS for IRCUser compat
      self.name = '*' ## need this since user hasn't logged in yet
      self.password = '' ## FIXME, TODO: remove once auth process fixed
      self.hostname = 's'

      ## TODO actually require a PONG response rather than
      ## just any traffic
      def disconnect():
         self.log.info('PING timeout expired; closing connection.')
         self.transport.loseConnection()

      def sendPing():
         self.sendLine('PING :{0}'.format(self.hostname))

      self.pingService = KeepaliveService(sendPing, 90, disconnect)

   def connectionLost(self, reason):
      self.pingService.stopService()
      self.avatar.leaveAll()
      IRCUser.connectionLost(self, reason)

   def dataReceived(self, data):
      self.pingService.alive()
      for line in data.split('\n'):
         line = line.strip('\r')
         if line:
            self.log.debug('recv IRC: {0}'.format(repr(line)))
      super(type(self), self).dataReceived(data)

   def sendLine(self, line):
      self.log.debug('send IRC: {0}'.format(repr(line)))
      ## real peerchat doesn't send \r, as this does, but shouldn't matter
      super(type(self), self).sendLine(line)
      #self.transport.write(line + '\n')

   def irc_QUIT(self, prefix, params):
      ## TODO: handle the goodbye message and respond to this ?
      self.transport.loseConnection()

   # TODO: enumerate GS cmd ids and use more meaningful names
   def irc_CRYPT(self, prefix, params):
      pass ## this will be handled by aspects, if at all

   def irc_USRIP(self, prefix, params):
      self.sendMessage('302', '', ':=+@{0}'.format(self.transport.getPeer().host))

   def irc_USER(self, prefix, params):
      #'XflsaqOa9X|165580976' is encodedIp|GSProfileId aka persona, '127.0.0.1', 'peerchat.gamespy.com', 'a69b3a7a0837fdcd763fdeb0456e77cb' is cdkey
      user, ip, host, cdkey = params
      encIp, profileId = user.split('|')

      #self.avatar = DbUser.objects.get(id=db.Persona.objects.get(id=profileId).user.id) #HACKy XXX # TODO use deferred
      #assert self.avatar.getIrcUserString() == user

      ## NOTE: don't call supermethod here

   _welcomeMessages = [
        (irc.RPL_WELCOME, ":connected to Twisted IRC"),
        (irc.RPL_YOURHOST, ":Your host is %(serviceName)s, running version %(serviceVersion)s"),
        (irc.RPL_CREATED, ":This server was created on %(creationDate)s"),

        # "Bummer.  This server returned a worthless 004 numeric.
        #  I'll have to guess at all the values"
        #    -- epic
        (irc.RPL_MYINFO,
         # w and n are the currently supported channel and user modes
         # -- specify this better
         "%(serviceName)s %(serviceVersion)s w n"),
        ]

   def irc_NICK(self, prefix, params):
      # TODO: assert that this user has logged in to the main login server so that impersonation
      # isn't possible like it is for the real gamespy

      # TODO: are personas available only for newer games?
      # solution is to just create 1 persona by default for each login

      # Here is the fix for impersonation: use name found during USER command
      # TODO: remove this when new auth methods are plugged in
      #self.nick = db.Persona.objects.get(user=self.avatar, selected=True).name

      IRCUser.irc_NICK(self, prefix, params) ## sends _welcomeMessage

   ##TODO: support channel ops and make hosts ops in their lobby channels
   '''
   def names(self, user, channel, names):
      names = [('@'+n) if n == 'Jackalus' else n for n in names] ## SUPER HACK
      super(type(self), self).names(user, channel, names)
   '''

   def irc_CDKEY(self, prefix, params):
      self.sendMessage('706', '1', ':Authenticated')
      self.pingService.startService()

   def irc_PONG(self, prefix, params):
      self.pingService.alive()

   def irc_JOIN(self, prefix, params):
      ## TODO: make sure everything is send just like in original peerchat impl
      IRCUser.irc_JOIN(self, prefix, params)

   def irc_PART(self, prefix, params):
      ## TODO: delete gamelobby once empty
      IRCUser.irc_PART(self, prefix, params)

   ## IChatClient implementation
   def userJoined(self, group, client):
      self.join(
         client.avatar.getClientPrefix('JOIN'),
         '#' + group.name)


   def userLeft(self, group, client, reason=None):
      assert reason is None or isinstance(reason, unicode)
      self.part(
         client.avatar.getClientPrefix('PART'),
         '#' + group.name,
         (reason or u'').encode(self.encoding, 'replace'))

   def receive(self, sender, recipient, message):
      '''
      This is an override of the regular receive that always assumes
      it has been triggered by the PRIVMSG command. This one differs in that
      it checks for  the 'command' key in the message dict for UTM etc. and sends
      that command instead.

      Remember that sender and recipient are IChatClients, so use .user to get DbUser
      '''
      if iwords.IGroup.providedBy(recipient):
         recipientName = '#' + recipient.name
      else:
         recipientName = recipient.name

      text = message.get('text', '<an unrepresentable message>')
      for line in text.splitlines():
         if 'command' not in message:
            assert False, 'need key: "command"'
         prefix = message.get('prefix', sender.avatar.getClientPrefix(message['command']))
         self.sendLine(":{0} {1} {2} {3}".format(prefix, message['command'],
                                                 recipientName,
                                                 line if 'raw' in message else ':'+lowQuote(line)))

   def aliasOfPrivmsg(command):
      def method (self, prefix, params):
         try:
            targetName = params[0].decode(self.encoding)
         except UnicodeDecodeError:
            self.sendMessage(
               irc.ERR_NOSUCHNICK, targetName,
               ":No such nick/channel (could not decode your unicode!)")
            return

         messageText = params[-1]

         def cbTarget(targ):
            if targ is not None:
               msg = {'text':messageText, 'command':command}
               if command == 'UTM' and 'NAT' in messageText: ## a HACK that seems unnecessary
                  msg['prefix'] = self.avatar.getClientPrefix(short=False) ## send long prefix for UTM NAT commands
               return self.avatar.send(targ, msg)

         def ebTarget(err):
            self.sendMessage(
               irc.ERR_NOSUCHNICK, targetName,
               ":No such nick/channel.")

         if targetName.startswith('#'):
            self.realm.lookupGroup(targetName[1:]).addCallbacks(cbTarget, ebTarget)
         else:
            for name in targetName.split(','):
               self.realm.lookupUser(name).addCallback(lambda user: user.mind).addCallbacks(cbTarget, ebTarget)
      return method

   irc_PRIVMSG = aliasOfPrivmsg('PRIVMSG') ## just for consistency's sake, redefine here
   irc_UTM = aliasOfPrivmsg('UTM')
   irc_NOTICE = aliasOfPrivmsg('NOTICE') ## TODO: irc_NOTICE not defined in IRCUser though notice() is?!

   def irc_WHO(self, prefix, params):
      pass
      ## TODO
      '''
      'WHO daghros\r\n'
2009-08-23 18:50:03,828 - gamespy.masterCli - decoded: '\x00\xec\x02~G\xa8l\xbf\x19\xec\xc0\xa8\x01\x88\x19\xec@\xde\xa6mViciousPariah ViciousPariah-War Arena!\x00data/maps/internal/war_arena_v3.7_mando777/war_arena_v3.7_mando777.map\x00\x06\x06openstaging\x001.12.3444.25830\x00-117165505\x00\x00\x013 100 10000 0 1 10 0 1 0 -1 0 -1 -1 1 \x00\x00\x02\x04\x00\x00251715600\x00\x00RA3\x000\x00\x00\x00'
2009-08-23 18:50:03,898 - gamespy.chatCli - received: ':s 352 Jackalus * XsfqlGFW9X|182446558 * s daghros H :0 cea8ff6a8da628bcff9249151b46f53d\n'
'''

   def irc_GETCKEY(self, prefix, params):
      chan, nick, rId, zero, fields = params
      fields  = fields.split('\\')[1:]

      grp = unicode(chan[1:])

      def ebGroup(err):
         err.trap(ewords.NoSuchGroup)
         pass ## TODO

      def cbGroup(group):
         if nick == '*':
            #users = db.Channels.objects.get(name=group.name).users.filter(loginsession__isnull=False) ## HACK race condition here?
            users = group.iterusers()
         else:
            users = [db.Persona.objects.get(name=nick).user]

         for user in users:
            # TODO: add get_username getter to Stats, once properties are supported, to fetch the ircUser string
            #response = ''.join('\\{0}'.format(getattr(user.stats, x)) for x in fields) # only possible with getter-methods
            uName = user.getPersona().name
            stats = db.Stats.objects.get_or_create(persona=user.getPersona(), channel=db.Channel.objects.get(name=grp))[0] #TODO: defer
            response = stats.dumpFields(fields)
            self.sendMessage('702', chan, uName, rId, response)
         self.sendMessage('703', chan, rId, ':End of GETCKEY')
         # 702 = RPL_GETCKEY? -- not part of RFC 1459

      self.realm.lookupGroup(grp).addCallbacks(cbGroup, ebGroup)

   def irc_SETCKEY(self, prefix, params):
      chan, nick, fields = params
      assert nick == self.avatar.name
      tokens  = fields.split('\\')[1:]
      changes = dict(zip(tokens[::2], tokens[1::2]))
      changes = dict((k, v if v != '' else None) for k, v in changes.iteritems()) ## change blanks to nulls
      fields = tokens[::2] ## define this to maintain ordering

      grp = unicode(chan[1:])

      def saveToDb():
         if 'b_arenaTeamID' in changes:
            changes['b_arenaTeamID'] = db.ArenaTeam.objects.get_or_create(id=changes['b_arenaTeamID'])[0]
         stats = db.Stats.objects.get_or_create(persona=self.avatar.getPersona(), channel=db.Channel.objects.get(name=grp))[0]
         for k, v in changes.iteritems(): setattr(stats, k, v)
         stats.save()
         return stats


      def ebGroup(err):
         err.trap(ewords.NoSuchGroup)
         pass ## TODO

      def respond(results):
         successes = [x[0] for x in results]
         stats, group = [x[1] for x in results]
         if not all(successes):
            return ## TODO: log this / raise exc
         response = stats.dumpFields(fields, withNames=True)

         ## BCAST - broadcast the change
         ## general format of 702 message is:
         ## :s 702 <target chan> <scope of flags (chan)> <nick> <request id or BCAST> :<flags>
         ## TODO XXX : make func to send 702 results, separate from send() and receive(),
         ## those should be reserved for privmsg type commands
         msg = {'command':'702',
                'text':' '.join([chan, nick, 'BCAST', response]),
                'raw':True,
                'prefix':self.hostname,
               } ## very HACKy -- several spots for this hack
         self.avatar.send(group, msg)
         ## also send BCAST to self (group send normally excludes self)
         self.receive(self, group, msg)

      defer.DeferredList([threads.deferToThread(saveToDb),
                          self.realm.lookupGroup(grp).addErrback(ebGroup)]).addCallback(respond)


   def _sendTopic(self, group):
      '''
      Send the topic of the given group to this user, if it has one.
      '''
      topic = group.topic
      if topic:
         author = "<noone>" ## TODO
         date = 0
         self.topic(self.name, '#' + group.name, topic)
         self.topicAuthor(self.name, '#' + group.name, author, date)

   def _setTopic(self, channel, topic):
      def cbGroup(group):
         def ebSet(err):
            self.sendMessage(
               irc.ERR_CHANOPRIVSNEEDED,
               "#" + group.name,
               ":You need to be a channel operator to do that.")

         group.topic = topic
         group.save() ## TODO: defer
         return defer.succeed(None)

      def ebGroup(err):
         err.trap(ewords.NoSuchGroup)
         self.sendMessage(
            irc.ERR_NOSUCHCHANNEL, '=', channel,
            ":That channel doesn't exist.")

      self.realm.lookupGroup(channel).addCallbacks(cbGroup, ebGroup)

   def _channelMode(self, group, modes=None, *args): ## args is whatever's after flags (usually slots)
      if modes: ## TODO: check for op status
         ## TODO: is this the correct way to combine the changes?
         mode = group.mode.split(' ')[0].strip('+-')
         for match in re.finditer('([+-])(\w)', modes):
            sign, flag = match.groups()
            if sign == '+':
               mode = ''.join(set(mode + flag))
            else:
               mode = ''.join(set(mode) - set(flag))
         group.mode = '+'+' '.join((mode,) + args)
         group.save()
      #self.sendMessage( irc.ERR_UNKNOWNMODE, ":Unknown MODE flag.")
      self.channelMode(self.name, '#' + group.name, group.mode)

   def _userMode(self, user, modes=None):
      if modes:
         #self.sendMessage(
            #irc.ERR_UNKNOWNMODE,
            #":Unknown MODE flag.")
         pass ## TODO: actually implement? - not necessary since game clients only
      elif user is self.avatar:
         self.sendMessage(
            irc.RPL_UMODEIS,
            "+")
      else:
         self.sendMessage(
            irc.ERR_USERSDONTMATCH,
            ":You can't look at someone else's modes.")

class PeerchatFactory(IRCFactory):
   protocol = Peerchat

   def __init__(self):
      realm = PeerchatRealm()
      IRCFactory.__init__(self, realm, PeerchatPortal(realm))


## clear out static chans at startup
## TODO: move or redesign this
## maybe at DbGroup init build grp.users out of grp.clients?
for chan in db.Channel.objects.all():
   chan.users.clear()


## INTEGRAGTION TODO:
## follow naming, callback convention, db abstraction
## move all db stuff to DbGroup and DbUser
## delete old_ peerchat
## TODO:
## * all db access should use deferToThread
## * figure out deferred chain in addGroup

## TODO: check that interfac is fully implemented
class DbGroup(db.Channel):
   implements(iwords.IGroup)

   class Meta:
      proxy = True

   def __init__(self, *args, **kw):
      db.Channel.__init__(self, *args, **kw)

      ## FIXME: remove this HACK or at least find better way to check if a new chan
      if self.id is None: ## is this channel newly created (eg, gamelobby GSP chan)
         self.save() ## save so we can store clients in clientMap

      ## self.users is in the db and contains DbUser objects
      ## self.clients is a map from user.id to IRCUser instance
      ## these lists unfortunately have to be maintained separately :/
      ## TODO: handle this tracking better

   def _ebUserCall(self, err, client):
      return failure.Failure(Exception(client, err))

   def _cbUserCall(self, results):
      for (success, result) in results:
         if not success:
            clientuser, err = result.value # XXX <-- (not by elitak)
            self.remove(clientuser, err.getErrorMessage())

   def add(self, client):
      assert iwords.IChatClient.providedBy(client), "%r is not a chat client" % (client,)
      if client.avatar not in self.users.all():
         additions = []
         self.users.add(client.avatar) ## TODO: deferred
         ## notify other clients in this group
         for usr in self.users.exclude(id=client.avatar.id): ## better way to write this?
            usr = DbUser(id=usr.id) ##HACKY, dont like this, need to because User is returned with no 'mind' attr
            clt = usr.mind
            if clt is None:
               continue ## HACK: this skips clients that exit badly
            d = defer.maybeDeferred(clt.userJoined, self, client)
            d.addErrback(self._ebUserCall, client=clt)
            additions.append(d)
         ## callbacks for Deferreds in a DeferredList are fired only once all have completed
         defer.DeferredList(additions).addCallback(self._cbUserCall)
      return defer.succeed(None)

   def remove(self, client, reason=None):
      assert reason is None or isinstance(reason, unicode)
      if client.avatar in self.users.all():
         self.users.remove(client.avatar)
         removals = []
         for usr in self.users.exclude(id=client.avatar.id):
            usr = DbUser(id=usr.id) ##HACKY, dont like this, need to because User is returned with no 'mind' attr
            clt = usr.mind
            if clt is None:
               continue ## HACK: this is need for clients that exit badly
            d = defer.maybeDeferred(clt.userLeft, self, client, reason)
            d.addErrback(self._ebUserCall, client=clt)
            removals.append(d)
         defer.DeferredList(removals).addCallback(self._cbUserCall)
      return defer.succeed(None)

   def iterusers(self):
      ## TODO: deferToThread
      return iter(DbUser.objects.get(id=user.id) for user in self.users.all())

   def receive(self, sender, recipient, message):
      assert recipient is self
      receives = []
      for usr in self.users.exclude(id=sender.avatar.id):
         usr = DbUser.objects.get(id=usr.id) ##FIXME: should be no cast
         clt = usr.mind
         if clt is None:
            continue ## HACK: this is need for clients that exit badly
         d = defer.maybeDeferred(clt.receive, sender, self, message)
         d.addErrback(self._ebUserCall, client=clt)
         receives.append(d)
      defer.DeferredList(receives).addCallback(self._cbUserCall)
      return defer.succeed(None)


## TODO: check that interface is fully implemented
class DbUser(db.User):
   implements(iwords.IUser)

   # FIXME: these are not preserved in db
   realm = None # realm handles logins

   ## this gets wiped when the obj is constructed by a query
   #mind = None # 'mind' is really the IRCUser instance or 'client'
   ## so use this instead with a getter
   minds = {} # user id to client mapping

   class Meta:
      proxy = True

   @classmethod
   def getUser(cls, name):
      return DbUser.objects.get(id=db.Persona.objects.get(name=name).user.id)

   ## NOTE that we cant use this field in queries!
   def _get_name(self):
      return self.getPersona().name
   name = property(_get_name)

   def _get_mind(self):
      return DbUser.minds[self.id]
   def _set_mind(self, value):
      DbUser.minds[self.id] = value
   mind = property(_get_mind, _set_mind)

   def loggedIn(self, realm, mind):
      self.realm = realm
      DbUser.minds[self.id] = mind
      from time import time
      self.signOn = time()

   def join(self, group):
      return group.add(self.mind)

   def leave(self, group, reason=None):
      return group.remove(self.mind, reason)

   def leaveAll(self, reason=None):
      departures = []
      for chan in self.channel_set.all():
         group = DbGroup.objects.get(id=chan.id) ##FIXME this is essentially a cast
         departures.append(self.leave(group, reason))
      return defer.DeferredList(departures)

   def send(self, recipient, message):
      from time import time
      self.lastMessage = time()
      return recipient.receive(self.mind, recipient, message)

   def getIrcUserString(self):
      'returns the encoded ip and profile id of this user'
      # TODO: find better way to manage the active/selected persona. Account could get in a bad state this way (2 active, get()s fail)
      try:
         return '{0}|{1}'.format(IpEncode.encode(self.loginsession.extIp), self.getPersona().id)
      except self.DoesNotExist, ex:
         print('WARNING: could not find loginsession for user with login={0}, id={1}'.format(self.login, self.id))
         return '{0}|{1}'.format(IpEncode.encode('0.0.0.0'), self.getPersona().id)

   def getClientPrefix(self, command=None, short=True):
      '''
      follows RFC prefix BNF, but with encIp,gsProf
      '''
      if command in ['JOIN', 'PART']:
         short = False
      if short:
         ## sometimes this has '*' in place of 2nd and 3rd parts of string
         return '{0}!{1}@{2}'.format(self.getPersona().name, '*', '*')
      else:
         ## very rarely (JOIN msgs on same local net?) is the last param an ip address.
         ## most of the time it's just '*'
         #return '{0}!{1}@{2}'.format(self.getPersona().name, self.getIrcUserString(), '*')
         return '{0}!{1}@{2}'.format(self.getPersona().name, self.getIrcUserString(), self.mind.transport.getPeer().host)


class PeerchatRealm(WordsRealm):
   def __init__(self):
      WordsRealm.__init__(self, 's') ## 's' is what real peerchat uses (prly to save bandwidth)
      ## clean up channels from dirty exit
      for chan in DbGroup.objects.all():
         chan.users.clear()
         if chan.name.startswith('GSP'):
            chan.delete()

   def itergroups(self):
      return iter(DbGroup.objects)

   def addUser(self, user):
      raise NotImplementedError

   def addGroup(self, group):
      if not isinstance(group, DbGroup):
         return defer.fail() # TODO: return Failure obj as well

      ## TODO: try out this deferred chain
      #d = threads.deferToThread(group.save) ## this is all that should be needed, assuming obj is already setup
      #d.addCallback(lambda _: defer.succeed(group))
      #return d

      group.save()
      return defer.succeed(group)

   def lookupUser(self, name):
      assert isinstance(name, unicode)
      return threads.deferToThread(DbUser.getUser, name)

   def lookupGroup(self, name):
      assert isinstance(name, unicode)

      def getGroup(name):
         if name.startswith('GSP'):
            grp = DbGroup.objects.get_or_create(name=name, prettyName=name, game=db.Game.objects.get(name=name.split('!')[1]))[0] ## TODO:better way to provide game?
         else:
            grp = DbGroup.objects.get(name=name)
         return grp

      return threads.deferToThread(getGroup, name=name)

class PeerchatPortal(Portal):
   def __init__(self, realm):
      Portal.__init__(self, realm, [InsecureAccess()])

class InsecureAccess:
   '''
   TODO: fix this by checking that user is actually logged in on ealogin side.
   '''
   implements(ICredentialsChecker)
   credentialInterfaces = credentials.IUsernamePassword,

   def requestAvatarId(self, credentials):
      return defer.succeed(credentials.username)

   def checkPassword(self, password):
      return defer.succeed(True)

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
         unenc = re.sub(r'(:s 706 \S+) .*', r'\1 1 :Authenticated', unenc)
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
         util.getLogger('gamespy', self).debug(repr(data))
         sChal = data.split(' ')[-2].strip()
         cChal = data.split(' ')[-1].strip()
         self.cipher = CipherProxy(sChal, cChal, self.peer.gamekey)
      else:
         data = self.cipher.recvFromServer(data)
      ProxyClient.dataReceived(self, data)

class ProxyPeerchatClientFactory(ProxyClientFactory):
   protocol = ProxyPeerchatClient

   def connectionMade(self):
      ProxyClientFactory.connectionMade(self)
      self.log = util.getLogger('gamespy.chatCli', self)

class ProxyPeerchatServer(ProxyServer):
   clientProtocolFactory = ProxyPeerchatClientFactory
   def dataReceived(self, data):
      if self.peer.cipher:
         data = self.peer.cipher.recvFromClient(data)
      else:
         util.getLogger('gamespy', self).debug(repr(data))
      ProxyServer.dataReceived(self, data)

class ProxyPeerchatServerFactory(ProxyFactory):
   protocol = ProxyPeerchatServer

   def connectionMade(self):
      ProxyFactory.connectionMade(self)
      self.log = util.getLogger('gamespy.chatSrv', self)

   def __init__(self, gameName, host, port):
      ProxyFactory.__init__(self, host, port)
      self.gameName = gameName

   def buildProtocol(self, addr):
      p = ProxyFactory.buildProtocol(self, addr)
      p.gamekey = db.Game.getKey(self.gameName)
      return p

##TODO: make a generic logging aspect for all Protocol objects to capture receives and sends and log based on module name
@aspects.Aspect(Peerchat)
class PeerchatEncryption(object):
   def connectionMade(self):
      self.doCrypt = False
      yield aspects.proceed
      def writeWrap(self_transport, data):
         if self.doCrypt:
            data = self.sCipher.crypt(data)
         yield aspects.proceed(self_transport, data)
      aspects.with_wrap(writeWrap, self.transport.write)

   def dataReceived(self, data):
      if self.doCrypt:
         data = self.cCipher.crypt(data)
      yield aspects.proceed(self, data)

   def irc_CRYPT(self, prefix, params):
      # params are usually 'des', '1', 'redalertpc'
      self.cipherFactory = PeerchatCipherFactory(db.Game.getKey(params[2]))
      self.sCipher = self.cipherFactory.getCipher()
      self.cCipher = self.cipherFactory.getCipher()

      self.sendMessage('705', self.cCipher.challenge, self.sCipher.challenge)
      self.doCrypt = True ## encrypt traffic henceforth
      yield aspects.proceed
