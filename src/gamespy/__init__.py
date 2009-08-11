mods = [
   'available',
   'downloads',
   'gpcm',
   'login',
   'master',
   'peerchat',
   'sake',
]

for m in mods:
   exec 'import {0}'.format(m)