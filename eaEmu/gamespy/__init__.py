mods = [
   'auth',
   'available',
   'gpcm',
   'login',
   'master',
   'peerchat',
   'webServices',
]

for m in mods:
   exec 'import {0}'.format(m)
