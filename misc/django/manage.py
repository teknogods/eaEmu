#!/usr/bin/python2.6
import sys
import os
from subprocess import *

def updateModels():
   modFile = 'eaEmu/models.py'
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
   try:
      import django.conf
      import yaml
      config = yaml.load(open('config.yml').read())
      django.conf.settings.configure(**config['django'])
   except Exception, ex:
      sys.stderr.write('Error: Can\'t load config.yml\n')
      import traceback
      traceback.print_exc()
      sys.exit(1)
   from django.core.management import execute_from_command_line
   sys.path.append('.')
   execute_from_command_line()

if __name__ == "__main__":
   updateModels()
   runManager()
