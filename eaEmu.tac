#!/usr/bin/python
import sys
import twisted.plugin
from eaEmu.util import aspects
import eaEmu.twistd
from twisted.application.service import IServiceMaker
from zope.interface import implements

if __name__ == '__main__':
   ## Here, I'm wrapping getPlugins(). This is pretty tricky:
   ## getPlugins() itself is a generator function, which adds to
   ## the confusion of using yield statements for the aspects wrapper.
   ## Keep in mind that the generator function we're wrapping really
   ## only returns a single generator object. So, to prepend our
   ## interface-implementing objects to that generator, we need to
   ## define a new one that's a composed of its own yield statements
   ## as well as the yielded values from the original generator. Hence,
   ## we save the original generaton call (to avoid infinite recursion),
   ## then return our newGenerator that yields the new values we want before
   ## yielding those from the original generator.
   origGen = twisted.plugin.getPlugins
   def wrapGetPlugins(interface, package=None):
      def newGen():
         for obj in eaEmu.twistd.__dict__.values():
            try:
               yield interface(obj)
            except TypeError, ex:
               pass
         for obj in origGen(interface, package):
            yield obj
      yield aspects.return_stop(newGen())
   aspects.with_wrap(wrapGetPlugins, origGen)

   ## add some default args
   sys.argv[1:1] = ['-n', '-o', 'eaEmu']

   from twisted.scripts.twistd import run
   run()
else:
   ## HACKY TAC startup is supported but not recommended
   ## use twistd -n -o ra3 instead
   ## or just ./<this file>
   from twisted.application.service import Application
   from eaEmu.ea.games.redalert3 import Service
   application = Application('EA Online Server Emulator')
   svc = Service(webPort=80)
   svc.setServiceParent(application)
