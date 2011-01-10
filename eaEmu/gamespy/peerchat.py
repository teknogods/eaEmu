from __future__ import absolute_import
from __future__ import print_function

from ..db import *
from .cipher import *
from .. import util
from ..util import aspects
from ..util.timer import KeepaliveService

from django.db import transaction

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
from twisted.internet.tcp import Server

import logging
import re

## TODO: all db access should go into Channel and User
## They should also all use Deferreds

class Peerchat(IRCUser, object):
   def connectionMade(self):
      IRCUser.connectionMade(self)
      peer = self.transport.getPeer()
      self.log = util.getLogger('gamespy.peerchat', self)

      ## some HACKS for IRCUser compat
      self.name = '*' ## need this since user hasn't logged in yet
      self.password = '' ## FIXME, TODO: remove once auth process fixed (used by irc_NICK currently to login)
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
      ## had to reimplement IRCUser.connectionLost to handled deferred logout
      if self.logout is not None:
         def cbLoggedOut(result):
            self.avatar = None
            return result
         defer.maybeDeferred(self.logout).addCallback(cbLoggedOut)



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
      self.sendMessage(irc.RPL_USERHOST, '', ':=+@{0}'.format(self.transport.getPeer().host))

   def irc_USER(self, prefix, params):
      #'XflsaqOa9X|165580976' is encodedIp|GSProfileId aka persona, '127.0.0.1', 'peerchat.gamespy.com', 'a69b3a7a0837fdcd763fdeb0456e77cb' is cdkey
      user, ip, host, self.cdKeyHash = params
      if '|' in user: ## should be true unless client is using a regular IRC client
         encIp, profileId = user.split('|')

      #self.avatar = User.objects.get(id=Persona.objects.get(id=profileId).user.id) #HACKy XXX # TODO use deferred
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
      #self.nick = Persona.objects.get(user=self.avatar, selected=True).name

      IRCUser.irc_NICK(self, prefix, params) ## sends _welcomeMessage

   def irc_CDKEY(self, prefix, params):
      self.sendMessage('706', '1', ':Authenticated')

      ## At this point, user is "logged in"

      self.pingService.startService()

      ## db initializations go here (TODO: move them)

      ## create user mode object
      info = UserIrcInfo.objects.get_or_create(user=self.avatar, channel=None)


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

      Remember that sender and recipient are IChatClients, so use .user to get User
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
      ## FIXME: in coop, joiner tends to WHO himself. I don't think this ever happens on real servers. Minor issue, but strange. Probably
      ## some info about the self is not being returned during the early login stages.
      nick = params[0]
      if nick == '*':
         pass ## TODO: ever happen? what's proper behavior?

      if nick.startswith('#'): ## only irc clients do this
         return

      def cbGotUser(user):
         self.sendMessage(irc.RPL_WHOREPLY, '*', user.getIrcUserString(), '*', self.hostname, nick, 'H', ':0 {0}'.format(self.cdKeyHash))
         self.sendMessage(irc.RPL_ENDOFWHO, nick, ':End of WHO list')

      #threads.deferToThread(User.getUser, nick).addCallback(cbGotUser)
      defer.maybeDeferred(User.getUser, nick).addCallback(cbGotUser)

   def irc_GETCKEY(self, prefix, params):
      chan, nick, rId, zero, fields = params
      fields  = fields.split('\\')[1:]

      grp = unicode(chan[1:])

      def ebGroup(err):
         err.trap(ewords.NoSuchGroup)
         pass ## TODO

      def cbGroup(group):
         if nick == '*':
            #users = Channel.objects.get(name__iexact=group.name).users.filter(loginsession__isnull=False) ## HACK race condition here?
            users = group.iterusers()
         else:
            users = [Persona.objects.get(name__iexact=nick).user]

         calls = []
         for user in users:
            # TODO: add get_username getter to Stats, once properties are supported, to fetch the ircUser string
            name = user.getPersona().name
            def cbStats(stats, name): ## name must be passed in, as it will change between callbacks!!
               response = stats.dumpFields(fields)
               self.sendMessage('702', chan, name, rId, response)

            calls.append(Stats.getStats(name, group.name))
            calls[-1].addCallback(cbStats, name)
            #objects.get_or_create(persona=user.getPersona(), channel=Channel.objects.get(name__iexact=grp))[0] #TODO: defer

         def cbDone(results):
            self.sendMessage('703', chan, rId, ':End of GETCKEY')
            # 702 = RPL_GETCKEY? -- not part of RFC 1459
         defer.DeferredList(calls).addCallback(cbDone)

      self.realm.lookupGroup(grp).addCallbacks(cbGroup, ebGroup)

   def irc_SETCKEY(self, prefix, params):
      params = [unicode(x) for x in params]
      chan, nick, fields = params
      assert nick == self.avatar.getPersona().name, 'nick={0} is not equal to personaName={1}'.format(nick, self.avatar.getPersona().name)
      tokens  = fields.split('\\')[1:]
      changes = dict(zip(tokens[::2], tokens[1::2]))
      changes = dict((k, v if v != '' else None) for k, v in changes.iteritems()) ## change blanks to nulls
      fields = tokens[::2] ## define this to maintain ordering

      grp = chan[1:]

      def ebGroup(err):
         err.trap(ewords.NoSuchGroup)
         print('Group not found')
         pass ## TODO

      def cbUpdateAndSave(stats):
         if 'b_arenaTeamID' in changes:
            changes['b_arenaTeamID'] = ArenaTeam.objects.get_or_create(id=changes['b_arenaTeamID'])[0]
         for k, v in changes.iteritems(): setattr(stats, k, v)
         def save():
            stats.save()
            return stats
         #return threads.deferToThread(save)
         return defer.maybeDeferred(save)

      def ebRespond(err):
         print('Error in sending response: probably either stats or group could not be retrieved')
         return err

      def cbRespond(results):
         stats, group = [x[1] for x in results]
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

      defer.DeferredList([
         Stats.getStats(self.name, grp).addCallback(cbUpdateAndSave),
         self.realm.lookupGroup(grp).addErrback(ebGroup),
      ]).addCallback(cbRespond).addErrback(ebRespond)

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


   ## TODO: this method and irc_NAMES (still broken)
   ## should call the same code.
   def irc_JOIN(self, prefix, params):
      try:
         groupName = params[0].decode(self.encoding)
      except UnicodeDecodeError:
         self.sendMessage(
            irc.IRC_NOSUCHCHANNEL, params[0],
            ":No such channel (could not decode your unicode!)")
         return

      if groupName.startswith('#'):
         groupName = groupName[1:]

      def cbGroup(group):
         def cbJoin(ign):
            self.userJoined(group, self)
            self.names(
               self.name,
               '#' + group.name,
               [('@' if 'o' in user.getChanMode(group) else '') + user.name for user in group.iterusers()])
            self._sendTopic(group)
         return self.avatar.join(group).addCallback(cbJoin)

      def ebGroup(err):
         self.sendMessage(
            irc.ERR_NOSUCHCHANNEL, '#' + groupName,
            ":No such channel.")

      self.realm.getGroup(groupName).addCallbacks(cbGroup, ebGroup)

class PeerchatFactory(IRCFactory):
   protocol = Peerchat

   def __init__(self):
      realm = PeerchatRealm()
      IRCFactory.__init__(self, realm, PeerchatPortal(realm))


## INTEGRAGTION TODO:
## follow naming, callback convention, db abstraction
## move all db stuff to Channel and User
## TODO:
## * all db access should use deferToThread
## * figure out deferred chain in addGroup
## * this class should be an Aspect of Group

## TODO: check that interfac is fully implemented
@aspects.Aspect(Channel)
class _Channel(object):
   implements(iwords.IGroup)

   def __init__(self, *args, **kw):
      yield aspects.proceed

      ## FIXME: remove this HACK or at least find better way to check if a new chan
      if self.id is None: ## is this channel newly created (eg, gamelobby GSP chan)
         self.save() ## save so we can store clients in clientMap

      ## self.users is in the db and contains User objects
      ## self.clients is a map from user.id to IRCUser instance
      ## these lists unfortunately have to be maintained separately :/
      ## TODO: handle this tracking better


   ## used by methods that rely on deferredlists to do something to all users
   def _ebUserCall(self, err, client):
      return failure.Failure(Exception(client, err))

   ## used by methods that rely on deferredlists to do something to all users
   def _cbUserCall(self, results):
      for (success, result) in results:
         if not success:
            ## remove the user from the channel
            clientuser, err = result.value
            self.remove(clientuser, err.getErrorMessage())

   def add(self, client):
      assert iwords.IChatClient.providedBy(client), "%r is not a chat client" % (client,)

      ## FIXME: I'm pretty sure the decorator here does nothing until I enforce uniqueness in the Stats table with:
      ##  class Meta:
      ##    unique_together = (('channel_id', 'user_id'),)
      ## this is probably because of bad db design :P
      @djangoAsync(self)
      @transaction.commit_on_success
      def dbOps():
         if client.avatar in list(self.users.all()):
            raise Exception('User already in channel.') ##FIXME: this is bad!!!!!! user will lock up

         ## set mode for user in this channel
         info = UserIrcInfo.objects.get_or_create(user=client.avatar, channel=self)[0]

         self.users.add(client.avatar)
         ## create corresponding stats object
         self.stats_set.create(persona=client.avatar.getPersona())

         if self.name.lower().startswith('gsp') and self.users.count() == 1:
            ## first in private chan, promote to op
            client.avatar.setChanMode(self, '+o')

      def cbNotify(result):
         users = self.users.exclude(id=client.avatar.id)
         calls = []
         for usr in users:
            dfr = defer.maybeDeferred(usr.mind.userJoined, self, client)
            dfr.addErrback(self._ebUserCall, client=usr.mind)
            calls.append(dfr)
         return defer.DeferredList(calls).addCallback(self._cbUserCall) ##prunes stale users

      return dbOps().addCallback(cbNotify) ##need eb

   def remove(self, client, reason=None):
      assert reason is None or isinstance(reason, unicode)

      @djangoAsync(self)
      @transaction.commit_on_success
      def dbOps():
         if client.avatar not in list(self.users.all()):
            ## this is legitly possible. an irc client can send multiple parts without first joining
            ## As long as there are no race conditions, we can just return.
            #raise Exception('User not in channel.')
            return
         self.users.remove(client.avatar)
         ## delete corresponding stats obj
         ## TODO: there may be a race condition here if this gets deleted before the PART is sent to other
         ## clients and they do a GETCKEY on that user.
         self.stats_set.get(persona__user=client.avatar).delete()

      def cbNotify(result):
         users = self.users.exclude(id=client.avatar.id)
         def cbUsersRemoved(results):
            if self.name.lower().startswith('gsp') and self.users.count() == 0:
               self.delete()
            return results

         calls = []
         for usr in users:
            dfr = defer.maybeDeferred(usr.mind.userLeft, self, client, reason)
            dfr.addErrback(self._ebUserCall, client=usr.mind)
            calls.append(dfr)
         return defer.DeferredList(calls).addCallback(cbUsersRemoved)

      ## XXX: can't seem to get deferToThread() to obey mutex locks in dbOps
      ## I think this is related to the "cant create public chans" bug as well -- deferToThread seems bugged
      return dbOps().addCallback(cbNotify) ##need eb

   def iterusers(self):
      ## TODO: deferToThread
      return self.users.all()

   def receive(self, sender, recipient, message):
      assert recipient is self
      receives = []
      for usr in self.users.exclude(id=sender.avatar.id):
         clt = usr.mind
         if clt is None:
            continue ## HACK: this is need for clients that exit badly
         d = defer.maybeDeferred(clt.receive, sender, self, message)
         d.addErrback(self._ebUserCall, client=clt)
         receives.append(d)
      defer.DeferredList(receives).addCallback(self._cbUserCall) ##prunes stale users
      return defer.succeed(None)


## TODO: check that interface is fully implemented
@aspects.Aspect(User)
class _User(object):
   implements(iwords.IUser)

   ## FIXME: these are not preserved in db
   realm = None # realm handles logins

   ## this gets wiped when the obj is constructed by a query
   #mind = None # 'mind' is really the IRCUser instance or 'client'
   ## so use this instead with a getter
   minds = {} # user id to client mapping

   @classmethod
   def getUser(cls, nick):
      return User.objects.get(id=Persona.objects.get(name__iexact=nick).user.id)

   ## NOTE that we cant use this field in queries!
   ## XXX: using this is misleading. really, user.login should be user.name, so this is bad... DEPRECATE.
   def _get_name(self):
      return self.getPersona().name
   name = property(_get_name)

   def _get_mind(self):
      return User.minds[self.id]
   def _set_mind(self, value):
      User.minds[self.id] = value
   mind = property(_get_mind, _set_mind)

   def loggedIn(self, realm, mind):
      self.realm = realm
      User.minds[self.id] = mind
      from time import time
      self.signOn = time()

   def join(self, group):
      return group.add(self.mind)

   def leave(self, group, reason=None):
      return group.remove(self.mind, reason)

   def leaveAll(self, reason=None):
      departures = []
      for chan in self.channel_set.all():
         group = Channel.objects.get(id=chan.id) ##FIXME this is essentially a cast
         departures.append(self.leave(group, reason))
      return defer.DeferredList(departures)

   ## this is called from IRCUser.connectionLost (after a bunch of redirection)
   def logout(self):
      return self.leaveAll()

   def send(self, recipient, message):
      from time import time
      self.lastMessage = time()
      return recipient.receive(self.mind, recipient, message)

   def getIrcUserString(self):
      'returns the encoded ip and profile id of this user'
      # TODO: find better way to manage the active/selected persona. Account could get in a bad state this way (2 active, get()s fail)
      try:
         return '{0}|{1}'.format(IpEncode.encode(self.loginsession.extIp), self.getPersona().id)
      except LoginSession.DoesNotExist, ex:
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
      for chan in Channel.objects.all():
         chan.users.clear()
         if chan.name.startswith('GSP'):
            chan.delete()


   ## for some reason WordsRealm does this syncronously, which leads to
   ## race conditions in my code
   def logoutFactory(self, avatar, facet):
      def logout():
         # XXX Deferred support here
         def cbLoggedOut(result):
            avatar.realm = avatar.mind = None
            return result
         return defer.maybeDeferred(getattr(facet, 'logout', lambda: None)).addCallback(cbLoggedOut)
      return logout

   def itergroups(self):
      return iter(Channel.objects)

   def addUser(self, user):
      raise NotImplementedError

   def addGroup(self, group):
      if not isinstance(group, Channel):
         return defer.fail() # TODO: return Failure obj as well

      ## TODO: try out this deferred chain
      #d = threads.deferToThread(group.save) ## this is all that should be needed, assuming obj is already setup
      #d.addCallback(lambda _: defer.succeed(group))
      #return d

      group.save()
      return defer.succeed(group)

   createUserOnRequest = False

   def lookupUser(self, name):
      assert isinstance(name, unicode)
      #return threads.deferToThread(User.getUser, name)
      return defer.maybeDeferred(User.getUser, name)

   ## getGroup in parent class will call createGroup
   createGroupOnRequest = True

   def getGroup(self, name):
      def ebGroup(err):
         ## supermethod only handles ewords.DuplicateGroup exceptions
         ## this will trap if user tried to make chan not starting with 'GSP'
         err.trap(Exception) ##TODO: make nopermstocreate exc
         return self.lookupGroup(name)

      return WordsRealm.getGroup(self, name).addErrback(ebGroup)

   def lookupGroup(self, name):
      assert isinstance(name, unicode)

      def dbCall():
         if name.lower().startswith('gsp'):
            game = Game.objects.get(name__iexact=name.split('!')[1]) ## TODO:better way to provide game?
            ## can't use __iexact in get_or_create!, btw (learned this before i split lookup/create)
            grp = Channel.objects.get(name__iexact=name, prettyName__iexact=name, game=game)
         else:
            grp = Channel.objects.get(name__iexact=name)
         return grp

      #return threads.deferToThread(dbCall)
      return defer.maybeDeferred(dbCall)

   def createGroup(self, name):
      assert isinstance(name, unicode)

      def dbCall():
         if name.lower().startswith('gsp'):
            game = Game.objects.get(name__iexact=name.split('!')[1]) ## TODO:better way to provide game?
            if Channel.objects.filter(name__iexact=name, prettyName__iexact=name, game=game).count():
               raise Exception('Tried to create private channel that already exists.')
            grp = Channel.objects.create(name=name, prettyName=name, game=game)
         else:
            raise Exception('Creation of public channels is disallowed.')
         return grp

      ## XXX: deferToThread seems bugged: errbacks added after this return don't get registered!?
      #return threads.deferToThread(dbCall)
      return defer.maybeDeferred(dbCall)


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
      if ':s 706' in unenc:
         unenc = re.sub(r'(:s 706 \S+) .*', r'\1 1 :Authenticated', unenc)
         log.debug('but sending this instead: %s', unenc)
      return self.serverEgress.crypt(unenc)

   def recvFromClient(self, data):
      unenc = self.clientIngress.crypt(data)
      log = logging.getLogger('gamespy.chatServ') #HACKy
      log.debug('received: '+repr(unenc))
      #patches follow
      return self.clientEgress.crypt(unenc)

## TODO: merge these with proxyPeerchat service
## I'm leaving them here for now in case i need to quickly
## capture some traffic.
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
      p.gamekey = Game.getKey(self.gameName)
      return p

##TODO: make a generic logging aspect for all Protocol objects to capture receives and sends and log based on module name

## these aspects are kind of sloppy. Before, I was wrapping self.transport.write
## from within a wrapped connectionMade, but the problem was I was getting stack
## overflows because the wraps were never peeled back off. I tried adding this in,
## but got exceptions whenever I tried to peel off the last wrap. I figured it's better
## to only wrap once, anyway, so now I'm wrapping Server.write since that's what's
## always used as self.transport it seems.
@aspects.Aspect(Server)
class PeerchatTransportEncryption(object):
   def write(self, bytes):
      ## TLS connections don't have the protocol attribute
      if hasattr(self, 'protocol') and isinstance(self.protocol, Peerchat):
         if self.protocol.doCrypt:
            bytes = self.protocol.sCipher.crypt(bytes)
      yield aspects.proceed(self, bytes)

@aspects.Aspect(Peerchat)
class PeerchatEncryption(object):
   def connectionMade(self):
      self.doCrypt = False
      yield aspects.proceed

   def dataReceived(self, data):
      if self.doCrypt:
         data = self.cCipher.crypt(data)
      yield aspects.proceed(self, data)

   def irc_CRYPT(self, prefix, params):
      # params are usually 'des', '1', 'redalertpc'
      self.cipherFactory = PeerchatCipherFactory(Game.getKey(params[2]))
      self.sCipher = self.cipherFactory.getCipher()
      self.cCipher = self.cipherFactory.getCipher()

      self.sendMessage('705', self.cCipher.challenge, self.sCipher.challenge)
      self.doCrypt = True ## encrypt traffic henceforth
      yield aspects.proceed


