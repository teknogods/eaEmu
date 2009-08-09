# TODO: clean up this import stuff
try:
   import dj.settings
   import django.conf
   if not django.conf.settings.configured:
      django.conf.settings.configure(**dj.settings.__dict__)
   from dj.eaEmu.models import Channel, GamespyGame
except Exception, e:
   print 'Exception while importing django modules:', e

# TODO: move to db
# to find gamekey, look for gameid in memory, like 'menofwarpcd' ASCII
# gamekey is usually nearby, <1k away
gameKeys = {
   'redalert3pc'    : 'uBZwpf',
   'menofwarpcd'    : 'z4L7mK',
   'menofwarpc'     : 'KrMW4d',
}

def getGameKey(gameName):
   return gameKeys[gameName]

def createChannel(**kw):
   return Channel.objects.create(**kw)

def getGameInfo(**kw):
   return GamespyGame.objects.get(**kw)

def getChannel(**kw):
   return Channel.objects.get(**kw)