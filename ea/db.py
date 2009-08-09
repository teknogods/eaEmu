#TODO: move me to ea.db
try:
   import dj.settings
   import django.conf
   if not django.conf.settings.configured:
      django.conf.settings.configure(**dj.settings.__dict__)
   
   import django.db.models
   
   from dj.eaEmu import models
   from dj.eaEmu.models import GameList, Player, EnterGameRequest
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

class Partition: # unused
   lists = [] # gamelists in this partition
   id = ''
   name = ''

class djProxy(django.db.models.base.ModelBase):
   def __new__(cls, name, bases, attrs):
      class _Meta:
         proxy = True
         app_label = 'djProxy'
      cls.Meta = _Meta
      new_class =  django.db.models.base.ModelBase.__new__(cls, name, bases, attrs)
      return new_class

class Game(models.Game):
   __metaclass__ = djProxy
      
   def Join(self, session): # TODO?
      # get hosting user's info and broker the connection
      pass
   def Leave(self, session):
      pass

class User(models.User):
   __metaclass__ = djProxy
   
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

class Session(models.Session):
   __metaclass__ = djProxy
   def __init__(self, *args, **kw):
      super(Session, self).__init__(*args, **kw)
      self.key = hash(self)
      
      # TODO: decrypt,generate this
      #self.key = 'SUeWiB5BXq4h6R8PCn4oPAAAKD0.'
      #self.key = 'SUeWiDsuck7mUGXCCn4oNAAAKDw.'

   def Login(self, user, pwd):
      self.user = User.GetUser(login=user)
      self.save()
      if pwd == self.user.password:
         return self.user
      else:
         return None #TODO: throw exception instead?
   
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
      return self.sessionClass.objects.create(theater=self, int_ip=ip, int_port=port, ext_ip=ip, ext_port=port)

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
