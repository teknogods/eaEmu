#!/usr/bin/python2.6
import sys
import os
from subprocess import *

def updateModels():
   modFile = 'eaEmu/dj/eaEmu/models.py'
   f = open(modFile, 'w')
   f.write('from django.db import models\n\n')
   f.close()
   prefix = os.path.dirname(sys.argv[0])
   cmd = ' '.join([
         os.path.join(prefix, 'dia2django.py'),
         os.path.join(prefix, 'eaEmu.dia'),
         '>>',
         modFile
   ])
   Popen(cmd, shell=True).wait()

def runManager():
   from django.core.management import execute_manager
   try:
      sys.path.append('.')
      from eaEmu.dj import settings
   except ImportError:
      sys.stderr.write('''Error: Can't find eaEmu.dj.settings from %r. It appears you've customized things.
   You'll have to run django-admin.py, passing it your settings module.
   ''' % __file__)
      sys.exit(1)
   execute_manager(settings)

if __name__ == "__main__":
   updateModels()
   runManager()
