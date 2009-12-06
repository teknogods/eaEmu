#!/usr/bin/python
import sys
import twisted.plugin
import eaEmu.util.aspects2 as aspects
import eaEmu

## HACKY TAC startup is supported but not recommended
## use twistd -n -o ra3 instead
## or just ./<this file>
from twisted.application.service import Application
from eaEmu.ea.games.redalert3 import Service
application = Application('EA Online Server Emulator')
svc = Service(webPort=80)
svc.setServiceParent(application)

if __name__ == '__main__':
   ## this wrapper checks my modules as well as the system ones
   def wrapGetPlugins(interface, package=None):
      yield aspects.proceed(interface, eaEmu)
      yield aspects.proceed
   aspects.with_wrap(wrapGetPlugins, twisted.plugin.getPlugins)

   ## add some default args
   sys.argv[1:1] = ['-n', '-o', 'ra3']

   from twisted.scripts.twistd import run
   run()