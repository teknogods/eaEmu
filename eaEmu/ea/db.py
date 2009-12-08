from datetime import datetime

#from twisted.internet import defer
from twisted.internet import threads

from ..gamespy.cipher import *

## TODO: move these funcs
def encode64(input_val, count, itoa64):
   ''' Encode binary data from input_val to ASCII string.

   Every six bits of input_val are represented by corresponding
   char from 64-char length itoa64 array. That is 0 will be
   represented in resulting string with char itoa64[0], 1 will
   be represented with itoa64[1], ..., 63 will be represented
   with itoa64[63].
   '''
   output = ''
   i = 0

   while i<count:
      value = ord(input_val[i])
      i = i+1
      output = output + itoa64[value&0x3f]

      if i < count:
         value = value | (ord(input_val[i]) << 8)

      output = output + itoa64[(value>>6)&0x3f]

      i = i+1
      if i >= count:
         break

      if i < count:
         value = value | (ord(input_val[i]) << 16)

      output = output + itoa64[(value>>12)&0x3f]

      i = i+1
      if i >= count:
         break

      output = output + itoa64[(value>>18)&0x3f]

   return output

def crypt_private(passwd, passwd_hash, hash_prefix='$H$'):
   '''
   Hash password, using same salt and number of
   iterations as in passwd_hash.

   This is useful when you want to check password match.
   In this case you pass your raw password and password
   hash to this function and then compare its return
   value with password hash again:

      is_valid = (crypt_private(passwd, hash) == hash)

   hash_prefix is used to check that passwd_hash is of
   supported type. It is compared with first 3 chars of
   passwd_hash and if does not match error is returned.

   NOTE: all arguments must be ASCII strings, not unicode!
   If you want to support unicode passwords, you could
   use any encoding you want. For compatibility with PHP
   it is recommended to use UTF-8:

   passwd_ascii = passwd.encode('utf-8')
   is_valid = (crypt_private(passwd_ascii, hash) == hash)

   Here hash is already assumed to be an ASCII string.

   In case of error '*0' is usually returned. But if passwd_hash
   begins with '*0', then '*1' is returned to prevent false
   positive results of password check.
   '''
   itoa64 = './0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz'
   output = '*0'
   # Prevent output from being the same as passwd_hash, because
   # this may lead to false positive password check results.
   if passwd_hash[0:2] == output:
      output = '*1'

   # Check for correct hash type
   if passwd_hash[0:3] != hash_prefix:
      return output

   count_log2 = itoa64.index(passwd_hash[3])
   if count_log2<7 or count_log2>30:
      return output
   count = 1<<count_log2

   salt = passwd_hash[4:12]
   if len(salt) != 8:
      return output

   m = md5.new(salt)
   m.update(passwd)
   tmp_hash = m.digest()
   for i in xrange(count):
      m = md5.new(tmp_hash)
      m.update(passwd)
      tmp_hash = m.digest()

   output = passwd_hash[0:12]+encode64(tmp_hash, 16, itoa64)
   return output

## TODO: migrate errors to db
class EaError(Exception):
   def __init__(self, id, text):
      self.id = id
      self.text = text

## note that these strings are never displayed, so i left the ones i'm not sure about blank
EaError.BadPassword = EaError(122, 'The password the user specified is incorrect')
EaError.AccountNotFound = EaError(101, 'The user was not found')
EaError.AccountDisabled = EaError(102, '')
EaError.NameTaken = EaError(160, 'That account name is already taken')

try:
   from ..dj import settings
   import django.conf
   if not django.conf.settings.configured:
      django.conf.settings.configure(**settings.__dict__)

   import django.db.models

   from ..dj.eaEmu import models
   from ..dj.eaEmu.models import GameList, Player, EnterGameRequest, Persona
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

class djProxy(django.db.models.base.ModelBase):
   def __new__(cls, name, bases, attrs):
      class _Meta:
         proxy = True
         app_label = 'djProxy'
      cls.Meta = _Meta
      new_class =  django.db.models.base.ModelBase.__new__(cls, name, bases, attrs)
      return new_class

class Game(models.GameSession):
   __metaclass__ = djProxy

   def Join(self, session): # TODO?
      # get hosting user's info and broker the connection
      pass
   def Leave(self, session):
      pass

class User(models.User):
   __metaclass__ = djProxy

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
models.User.getPersona = getPersona

def getUser(cls, **kw):
   '''
   Retrieves the User object that this Persona belongs to.
   '''
   return cls.objects.get(**kw).user
models.Persona.getUser = classmethod(getUser)

def getStats(cls, name, chanName):
   def fetch():
      persona = db.Persona.objects.get(name__iexact=name)
      channel = db.Channel.objects.get(name__iexact=chanName)
      return cls.objects.get_or_create(persona=persona, channel=channel)[0]
   return threads.deferToThread(fetch)

models.Stats.getStats = classmethod(getStats)

class Session(models.LoginSession):
   __metaclass__ = djProxy
   def __init__(self, *args, **kw):
      super(Session, self).__init__(*args, **kw)
      self.key = hash(self)

      # TODO: decrypt,generate this
      #self.key = 'SUeWiB5BXq4h6R8PCn4oPAAAKD0.'
      #self.key = 'SUeWiDsuck7mUGXCCn4oNAAAKDw.'

   def Login(self, user, pwd):
      def fetch():
         try:
            self.user = User.objects.get(login=user)
         except User.DoesNotExist:
            raise EaError.AccountNotFound

         ## HACK? delete any stale sessions before saving
         for e in Session.objects.filter(user=self.user):
            e.delete()
         self.save()

         if not self.user.active:
            ## FIXME: is there a special EaError for this?
            raise EaError.AccountDisabled
         ## FIXME: stick with 1 auth type?
         elif self.user.password in [pwd, crypt_private(pwd, self.user.password)]:
            self.user.lastLogin = datetime.now()
            self.user.save()
            return self.user
         else:
            raise EaError.BadPassword
      return threads.deferToThread(fetch)

class Theater(models.Theater):
   __metaclass__ = djProxy
   sessionClass = Session

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
      # prune old sessions in case they got left behind
      # TODO: prune these more regularly and also when we get an exception+disconnect in a connection
      existing = self.sessionClass.objects.filter(extIp=ip, extPort=port) # unlikely to be same port...
      if existing:
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
         return Game.objects.get(id=game_id)
      elif host != None:
         return User.objects.get(login=host).player_set[0]
