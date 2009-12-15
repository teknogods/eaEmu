import random
import base64
from datetime import datetime

from twisted.internet import defer
from twisted.internet import threads

from ..gamespy.cipher import *
from ..util.password import *
from ..util import aspects
from .errors import *

try:
   from ..dj import settings
   import django.conf
   import django.db.models
   if not django.conf.settings.configured:
      django.conf.settings.configure(**settings.__dict__)
   from ..dj.eaEmu.models import *
except Exception, e:
   print 'Exception while importing django modules:', e
   # generate dummy classes here so we can at least load up
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

# TODO: use class method assignment rather than metaclasses??

#class Partition: # unused
#   lists = [] # gamelists in this partition
#   id = ''
#   name = ''

@aspects.Aspect(GameSession)
class _GameWrap:
   def Join(self, session): # TODO?
      # get hosting user's info and broker the connection
      pass
   def Leave(self, session):
      pass

@aspects.Aspect(User)
class _UserWrap:
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
      def add():
         try:
            return Persona.objects.create(user=self, name=name)
         except Exception, ex: ## TODO make this an errback
            ## errbacks are better than try catches in async calls because it allows the caller to chain on extra except-blocks
            raise EaError.NameTaken ## TODO: find out what this is for mysql (sqlite3.IntegrityError) how to make generic?
      return threads.deferToThread(add)

   def getPersonas(self):
      #return [str(x.name) for x in Persona.objects.filter(user=self)]
      return [str(x.name) for x in self.persona_set.all()]

   # TODO: make into a getter method for property in User
   def getPersona(self):
      'returns the active persona'
      # TODO: find better way to manage the active/selected persona. Account could get in a bad state this way (2 active, get()s fail)
      return self.persona_set.get(selected=True)

@aspects.Aspect(Persona)
class _PersonaWrap:
   @classmethod
   def getUser(cls, **kw):
      '''
      Retrieves the User object that this Persona belongs to.
      '''
      return cls.objects.get(**kw).user


@aspects.Aspect(Stats)
class _StatsWrap:
   @classmethod
   def getStats(cls, name, chanName):
      def fetch():
         persona = db.Persona.objects.get(name__iexact=name)
         channel = db.Channel.objects.get(name__iexact=chanName)
         return cls.objects.get_or_create(persona=persona, channel=channel)[0]
      return threads.deferToThread(fetch)

def syncAccount(username):
   ## TODO: maybe grab this info from same database as the one in eaEmu.dj.settings?
   _info = {
      'dbapiName' : 'MySQLdb',
      'host'      : 'teknogods.com',
      'user'      : 'teknogod',
      'passwd'    : 'hm9tzuh9',
      'db'        : 'teknogodscomo',
   }
   #_info = {'dbapiName':'sqlite3', 'database':'eaEmu.db')
   def openDbConn():
      return ConnectionPool(**_info) ## doesnt actually connect until query is run?

   def cbConnOpen(db):
      return db.runQuery('SELECT user_password, user_email FROM phpbb_users WHERE username = "{0}"'.format(username))

   def ebRunQuery(err):
      print 'couldnt open connection to phpbb db -- {0}'.format(err.value)
      raise EaError.BackendFail

   def cbRunQuery(result):
      synced = False
      if len(result) > 0:
         password, email = result[0]
         user, synced = User.objects.get_or_create(login=username)
         synced = synced or user.password != password
         user.password = password
         user.email = email
         user.save()
      return synced

   #dfr.setTimeout(5) ## FIXME: this doesnt work as expected
   return deferToThread(openDbConn).addCallbacks(cbConnOpen).addCallbacks(cbRunQuery, ebRunQuery)

@aspects.Aspect(LoginSession)
class _LoginSession:
   def __init__(self, *args, **kw):
      ## TODO: decrypt,generate this
      #self.key = 'SUeWiB5BXq4h6R8PCn4oPAAAKD0.'
      #self.key = 'SUeWiDsuck7mUGXCCn4oNAAAKDw.'
      ## this is really some kind of special alphabet b64 encode, but doesnt matter for now...
      kw['key'] = base64.b64encode(''.join(chr(random.getrandbits(8)) for _ in range(21)))
      yield aspects.proceed

   def Login(self, username, pwd):
      def cbSync(success):
         self.user = User.objects.get(login=username)
         ## HACK? delete any stale sessions before saving
         for e in LoginSession.objects.filter(user=self.user):
            e.delete()
         self.save()
         return self.user

      def ebSync(err):
         err.trap(EaError)
         ## FIXME: EaErrors should be subtyped so this extra line isnt necessary:
         if err.value != EaError.BackendFail: return err
         print('Couldn\'t sync account for {0}; falling back to what\'s in the db.'.format(username))
         return defer.succeed(False).addCallback(cbSync) ## dunno if this is proper...

      def ebGetUser(err):
         err.trap(User.DoesNotExist)
         raise EaError.AccountNotFound

      def cbGotUser(user):
         if not user.active:
            raise EaError.AccountDisabled
         else:
            return defer.maybeDeferred(PhpPassword(user).check, pwd).addCallback(cbUserAuth, user).addErrback(ebPlainAuth, user)

      def cbUserAuth(isMatch, user):
         if isMatch:
            user.lastLogin = datetime.now()
            user.save()
            return user
         else:
            raise EaError.BadPassword

      def ebPlainAuth(err, user):
         ## HACKY alternate auth: current plaintext password.
         ## this allows non-hash passwords to work
         ## (these will only be in db if the sync failed for this account)
         err.trap(EaError)
         if err.value != EaError.BadPassword: return err ## FIXME: have own type
         if not pwd.startswith('$H$') and PlainTextPassword(user).check(pwd):
            return defer.maybeDeferred(PlainTextPassword(user).check, pwd).addCallback(cbUserAuth)
         else:
            raise EaError.BackendAndPasswordFail ## notify that non-forum password was incorrect

      return syncAccount(username).addCallbacks(cbSync, ebSync).addCallbacks(cbGotUser, ebGetUser)

@aspects.Aspect(Theater)
class _TheaterWrap:
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
      return self.sessionClass.objects.get(extIp=ip, extPort=port).delete()

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
