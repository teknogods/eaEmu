#!/usr/bin/python

## HACKY TAC startup needed by windows
## until i can get the module to register in dropin.cache
from twisted.application.service import Application
from eaEmu.ea.games.redalert3 import Service
application = Application('EA Online Server Emulator')
svc = Service(webPort=80)
svc.setServiceParent(application)

def twistd():
   ## the code below is copied from the 'twistd' start script

   ## Twisted Preamble
   ## This makes sure that users don't have to set up their environment
   ## specially in order to run these programs from bin/.
   import sys, os, string
   if string.find(os.path.abspath(sys.argv[0]), os.sep+'Twisted') != -1:
      sys.path.insert(0, os.path.normpath(os.path.join(os.path.abspath(sys.argv[0]), os.pardir, os.pardir)))
   if hasattr(os, "getuid") and os.getuid() != 0:
      sys.path.insert(0, os.path.abspath(os.getcwd()))
   ## end of preamble

   from twisted.scripts.twistd import run
   run()

if __name__ == '__main__':
   from twisted.plugin import IPlugin, getPlugins
   list(getPlugins(IPlugin))

   import sys

   from twisted.python.runtime import platformType
   if platformType == "win32":
      ## fallback to using .tac file
      sys.argv[1:1] = ['-n', '-o', '-y', 'eaEmu.tac']
   else:
      sys.argv[1:1] = ['-n', '-o', 'ra3']
   twistd()
