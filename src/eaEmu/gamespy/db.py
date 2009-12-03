#TODO: split gamespy stuff into it's own db?


# TODO: clean up this import stuff
try:
   from ..dj import settings
   import django.conf
   if not django.conf.settings.configured:
      django.conf.settings.configure(**settings.__dict__)
   from ..dj.eaEmu.models import *
except Exception, ex:
   print 'Exception while importing django modules:', ex

import new

# to find gamekey, look for gameid in memory, like 'menofwarpcd' ASCII
# gamekey is usually nearby, <1k away
def getKey(cls, gameName):
   return str(cls.objects.get(name=gameName).key)
Game.getKey = classmethod(getKey)
