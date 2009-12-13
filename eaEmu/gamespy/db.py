import re

from ..util import aspects

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

@aspects.Aspect(Game)
class _GameWrap:
   # to find gamekey, look for gameid in memory, like 'menofwarpcd' ASCII
   # gamekey is usually nearby, <1k away
   @classmethod
   def getKey(cls, gameName):
      return str(cls.objects.get(name=gameName).key)

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

@aspects.Aspect(User)
class _UserWrap:
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
