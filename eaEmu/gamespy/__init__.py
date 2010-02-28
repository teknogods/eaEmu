from __future__ import absolute_import
__all__ = [
   'auth',
   'cipher',
   'gpcm',
   'login',
   'master',
   'message',
   'peerchat',
   'webServices',
]

for mod in __all__:
   #exec 'from . import {0}'.format(mod)
   #exec 'import eaEmu.gamespy.{0}'.format(mod)
   #globals()[mod] = __import__(mod, globals(), locals(), level=-1)
   #globals()[mod] = __import__(mod, globals(), locals(), level=-1)
   pass

globals().update((mod, __import__(mod, globals(), level=1)) for mod in __all__)
