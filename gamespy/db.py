#TODO: split gamespy stuff into it's own db?


# TODO: clean up this import stuff
try:
   import dj.settings
   import django.conf
   if not django.conf.settings.configured:
      django.conf.settings.configure(**dj.settings.__dict__)
   from dj.eaEmu.models import *
except Exception, e:
   print 'Exception while importing django modules:', e
   
import new

# to find gamekey, look for gameid in memory, like 'menofwarpcd' ASCII
# gamekey is usually nearby, <1k away
@classmethod
def getKey(cls, gameName):
   return str(cls.objects.get(name=gameName).key)
Game.getKey = getKey
   
   
## TODO:: these should maybe just be removed entirely? all they do is abstract django
## out of the calls, but maybe the assumption we're using django is an okay one to make,
## especially since the kw args getting passed are django-specific anyway. For true abstraction,
## these functions should take a fixed list of arguments. On the other hand, that just limits us
## further.
## DECISION: add class/instance methods to model objects and use those
