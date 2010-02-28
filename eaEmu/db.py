from __future__ import absolute_import

from . import config
try:
   import django.conf
   if not django.conf.settings.configured:
      django.conf.settings.configure(**config['django'])
   from django.db.models import Q, signals
   from .models import *
except Exception, e:
   print 'Exception while importing django modules:', e
   import traceback
   traceback.print_exc()
   ## generate dummy classes here so we can at least load up
   import new
   def makeMod(modname):
      for i in reversed(range(len(modname.split('.')))):
         exec '{0} = new.module("{0}")'.format(modname.rsplit('.', i)[0])
      globals()[modname.split('.')[0]] = eval(modname.split('.')[0])

   def makeClasses(modname, classes):
      makeMod(modname)
      for c in classes:
         exec '{0}.{1} = new.classobj("{1}", (), {{}})'.format(modname, c)

   makeClasses('django.db.models.base', ['ModelBase'])
   makeClasses('models', ['Game'])
   #FIXME
from .gamespy.cipher import *
from .util.password import *
from .util import aspects
from .ea import errors

from twisted.internet import defer
from twisted.internet import threads

import random
import base64
from datetime import datetime

# TODO: use class method assignment rather than metaclasses??

#class Partition: # unused
#   lists = [] # gamelists in this partition
#   id = ''
#   name = ''

@aspects.Aspect(GameSession)
class _GameSessionAspect(object):
   def Join(self, session): # TODO?
      # get hosting user's info and broker the connection
      pass
   def Leave(self, session):
      pass

@aspects.Aspect(Game)
class _GameAspect(object):
   # to find gamekey, look for gameid in memory, like 'menofwarpcd' ASCII
   # gamekey is usually nearby, <1k away
   @classmethod
   def getKey(cls, gameName):
      return str(cls.objects.get(name=gameName).key)

@aspects.Aspect(User)
class _UserAspect:
   def _get_login_dirty(self):
      if ' ' in self.login:
         return '"{0}"'.format(self.login)
      else:
         return self.login
   def _set_login_dirty(self, value):
      self.login = value.strip('"')
   login_dirty = property(_get_login_dirty, _set_login_dirty)

   #TODO: obsolete, remove?
   @classmethod
   def GetUser(cls, **kw):
      matches = cls.objects.filter(**kw)
      if matches:
         return matches[0]
      else:
         return None

   @staticmethod
   def CreateUser(name, pwd=None):
      # FIXME: .name must be enclosed by " if spaces are present (where to put this behavior?)
      return self.__class__.objects.create(login=name, password=pwd)

   def addPersona(self, name):
      name = name.strip('"')
      def add():
         return Persona.objects.create(user=self, name=name)
      def ebAdd(err):
         err.trap(Exception)
         if type(err.value).__name__ == 'IntegrityError': ## different namespaces depending on db type used
            ##FIXME: this is raised when there are spaces in the persona? why???? works fine in eaemu_user table?!
            raise errors.NameTaken()
         else:
            return err
      #return threads.deferToThread(add)
      return defer.maybeDeferred(add).addErrback(ebAdd)

   def getPersonas(self):
      #return [str(x.name) for x in Persona.objects.filter(user=self)]
      return [str(x.name) for x in self.persona_set.all()]

   # TODO: make into a getter method for property in User
   def getPersona(self):
      'returns the active persona'
      # TODO: find better way to manage the active/selected persona. Account could get in a bad state this way (2 active, get()s fail)
      return self.persona_set.get(selected=True)

   def _get_umode(self):
      info = self.userircinfo_set.get(channel=None)
      return info.mode

   def _set_umode(self, value):
      #mode = group.mode.split(' ')[0].strip('+-')
      info = self.userircinfo_set.get(channel=None)
      info.mode = modifyMode(info.mode, value)
      info.save() ## shouldn't, but far away so do it

   umode = property(_get_umode, _set_umode)

   def getChanMode(self, channel):
      info = self.userircinfo_set.get(channel=channel)
      return info.mode

   def setChanMode(self, channel, value):
      info = self.userircinfo_set.get(channel=channel)
      info.mode = modifyMode(info.mode, value)
      info.save() ## shouldn't, but far away so do it

## TODO: a similar method in peerchat should be using thisone
def modifyMode(mode, mod):
   ## TODO? handle args that come after space at end of mode?
   #mode, args = mode.split(' ')
   args = []
   for match in re.finditer('([+-])(\w)', mod):
      sign, flag = match.groups()
      if sign == '+':
         mode = ''.join(set(mode + flag))
      else:
         mode = ''.join(set(mode) - set(flag))
   return '+'+' '.join([mode] + args)

@aspects.Aspect(Persona)
class _PersonaAspect:
   ''' not yet needed
   def _get_name_dirty(self):
      if ' ' in self.name:
         return '"{0}"'.format(self.name)
      else:
         return self.name
   def _set_name_dirty(self, value):
      self.name = value.strip('"')
   name_dirty = property(_get_name_dirty, _set_name_dirty)
   '''

   @classmethod
   def getUser(cls, **kw):
      '''
      Retrieves the User object that this Persona belongs to.
      '''
      return cls.objects.get(**kw).user


@aspects.Aspect(Stats)
class _StatsAspect:
   @classmethod
   def getStats(cls, name, chanName):
      persona = Persona.objects.get(name__iexact=name)
      channel = Channel.objects.get(name__iexact=chanName)
      @djangoAsync(persona)
      def dbOps():
         return cls.objects.get_or_create(persona=persona, channel=channel)[0]
      return dbOps()

   username = property(lambda self: self.persona.user.getIrcUserString())

   def dumpFields(self, fields, withNames=False):
      #response = ''.join('\\{0}'.format(getattr(user.stats, x)) for x in fields) # only possible with getter-methods
      fieldVals = {}
      for fld in fields:
         if fld == 'b_arenaTeamID': ## FIXME?
            val = getattr(self, fld)
            fieldVals[fld] = val and val.id or 0 # use zero if field is null (very rare case)
         else:
            fieldVals[fld] =getattr(self, fld, None) or '' ## None's become ''

      return ':\\' + '\\'.join(sum(
                                   [[k, str(fieldVals[k])] for k in fields] if withNames else
                                   [[str(fieldVals[k])] for k in fields],
                                   []
      ))

## FIXME: this should be formalized into a singleton instance
phpbb_db = ConnectionPool(**config['phpbb_db']['connection'])
## TODO: maybe grab this info from same database as the one in eaEmu.dj.settings?
def syncAccount(username):
   def ebRunQuery(err):
      print 'couldnt open connection to phpbb db -- {0}'.format(err.value)
      raise errors.BackendFail()

   def cbRunQuery(result):
      if len(result) == 0:
         raise errors.BackendFail()
      try:
         user = User.objects.get(Q(email__iexact=username) | Q(login__iexact=username))
      except User.DoesNotExist:
         user = User()
      user.phpbb_id, user.login, user.password, user.email = result[0]
      user.save()
      return user

   #dfr.setTimeout(5) ## FIXME: this doesnt work as expected. how to timeout a query??
   return phpbb_db.runQuery('SELECT user_id, username, user_password, user_email FROM phpbb_users WHERE username_clean LIKE LOWER("{0}") or user_email LIKE LOWER("{0}")'.format(username)
                            ).addCallbacks(cbRunQuery, ebRunQuery)

@aspects.Aspect(LoginSession)
class _LoginSessionAspect(object):
   def __init__(self, *args, **kw):
      ## TODO: decrypt,generate this
      #self.key = 'SUeWiB5BXq4h6R8PCn4oPAAAKD0.'
      #self.key = 'SUeWiDsuck7mUGXCCn4oNAAAKDw.'
      ## this is really some kind of special alphabet b64 encode, but doesnt matter for now...
      kw['key'] = base64.b64encode(''.join(chr(random.getrandbits(8)) for _ in range(21)))
      yield aspects.proceed

   def Login(self, username, pwd):
      '''
      right now, this does the following:
      1. sync the account from php db if possible
      2. if fails, whocares, continue and try whatevers in the db
      3. check the password as a hash
      4. if what's in the db is not a hash, check as plaintext as a backup (FIXME, should only check plaintext?)
      5. show bad password if no matches or show 902 if plaintext check was made and failed
      '''
      def cbSync(user):
         self.user = user
         ## HACK? delete any stale sessions before saving
         sessions = LoginSession.objects.filter(user=self.user)
         if sessions.count():
            print('Had to delete pre-existing sessions:', sessions.values())
         for e in sessions:
            e.delete()
         self.save()
         return self.user

      def ebSync(err):
         err.trap(errors.BackendFail)
         print('Couldn\'t sync account for {0}; falling back to what\'s in the db.'.format(username))
         user = User.objects.get(Q(email__iexact=username) | Q(login__iexact=username))
         return defer.succeed(user).addCallback(cbSync) ## behave as though we actually succeeded

      def ebGetUser(err):
         err.trap(User.DoesNotExist)
         raise errors.BackendFail()

      def cbGotUser(user):
         if not user.active:
            raise errors.AccountDisabled()
         else:
            dfr = defer.maybeDeferred(PhpPassword(user).check, pwd).addCallback(cbUserAuth, user)
            if not user.password.startswith('$H$'):
               dfr.addErrback(ebPlainAuth, user)
            return dfr

      def cbUserAuth(isMatch, user):
         if isMatch:
            user.lastLogin = datetime.now()
            user.save()
            return user
         else:
            raise errors.BadPassword()

      def ebPlainAuth(err, user):
         ## HACKY alternate auth: current plaintext password.
         ## this allows non-hash passwords to work
         ## (these will only be in db if the sync failed for this account)
         err.trap(errors.BadPassword)
         def ebBadPwd(err):
            err.trap(errors.BadPassword)
            raise errors.BackendAndPasswordFail() ## notify that non-forum password was incorrect
         return defer.maybeDeferred(PlainTextPassword(user).check, pwd).addCallback(cbUserAuth, user).addErrback(ebBadPwd)

      def cbCheckNumSessions(user):
         if LoginSession.objects.count() > 2:
            raise Exception('You may only login with a maximum of 2 clients in LAN Mode. Restart the server if you think this error shouldn\'t be happening.')
         else:
            return user

      if config.get('lanMode', False):
         ## In lan mode, you can log in as anybody. The account gets created ad-hoc.
         try:
            user = User.objects.get(Q(email__iexact=username) | Q(login__iexact=username))
         except:
            user = User.objects.create(login=username, password=pwd)
         return defer.succeed(user).addCallback(cbSync).addCallback(cbCheckNumSessions)
      else:
         return syncAccount(username).addCallbacks(cbSync, ebSync).addCallbacks(cbGotUser, ebGetUser)

@aspects.Aspect(Theater)
class _TheaterAspect(object):
   sessionClass = LoginSession

   @classmethod
   def getTheater(cls, name):
      return cls.objects.get(name=name)

   def PlayerLeaveGame(self, session, game_id):
      try:
         player = Player.objects.get(user=session.user)
         assert player.game_id == game_id
         player.delete()
      except:
         pass #TODO

   def PlayerJoinGame(self, session, game_id):
      Player.objects.create(user_id=session.user_id, game_id=game_id)

   def CreateSession(self, ip, port):
      ## HACK FIXME XXX TODO!!!!!!!!!!: prune these more regularly and also when we get an exception+disconnect in a connection

      ## prune old sessions in case they got left behind
      existing = self.sessionClass.objects.filter(extIp=ip, extPort=port) # unlikely to be same port...
      for e in existing:
         e.delete()
      return self.sessionClass.objects.create(theater=self, intIp=ip, intPort=port, extIp=ip, extPort=port)

   def DeleteSession(self, ip, port):
      ## HACK: if the connection is lost early enough, there may be no session to delete...
      for session in self.sessionClass.objects.filter(extIp=ip, extPort=port):
         session.delete()

   def ConnectionEstablished(self, key, user):
      self.sessionClass.objects.get(key=key).update(user=user)

   def ConnectionClosed(self, sess):
      del self.sessions[sess.key]

   def GetSession(self, key):
      return self.sessions[key]

   def CreateGame(self):
      pass

   def ListGames(self, filters=None):
      return self.games.values()

   def GetGame(self, game_id=None, host=None):
      if game_id != None:
         return GameSession.objects.get(id=game_id)
      elif host != None:
         return User.objects.get(login=host).player_set[0]

class djangoAsync(object):
   def __init__(self, model):
      self.model = model

   def __call__(self, func):
      def djangoAsyncWrapper(*args, **kw):
         done = defer.Deferred()
         ## XXX: this is still flawed, because if a channel is saved somewhere outside of these two
         ## methods (which it currently isn't), the race condition is back again.
         def sigSaved(**kw):
            if kw['instance'] is self.model:
               #print(kw)
               signals.post_save.disconnect(sigSaved, sender=self.model.__class__)
               done.callback(result)

         result = func(*args, **kw)

         ## XXX: i'm really after other stuff like when channel.users is saved, but this will have to do...
         signals.post_save.connect(sigSaved, sender=self.model.__class__)
         self.model.save()

         return done
      return djangoAsyncWrapper

##HACK: clean login sessions at startup
for sess in LoginSession.objects.all():
   sess.delete()

## clear out static chans at startup
## TODO: move or redesign this
## maybe at Channel init build grp.users out of grp.clients?
## that is, prune bad clients during __init__ rather that just at start?
## i dont think this is best, it promotes bad accounting...
for chan in Channel.objects.all():
   chan.users.clear()
## clear stats too so that they don't get duped on new joins
for stats in Stats.objects.all():
   stats.delete()

