from zope.interface import implements

from twisted.python import usage
from twisted.plugin import IPlugin
from twisted.application.service import IServiceMaker
from twisted.application import internet
from twisted.python.usage import portCoerce

class EaEmuOptions(usage.Options):
   optParameters = [['port', 'p', 1235, 'The port number to listen on.']]

class EaEmuServiceFactory(object):
   implements(IServiceMaker, IPlugin)
   tapname = 'eaEmu'
   description = 'EA Online Server Emulator'
   options = EaEmuOptions

   def makeService(self, options):
      #from eaEmu.ea.games.redalert3 import Service
      return Service()

## TODO: individual server plugins are just shortcuts
## until i can merge all into the above and take options
## for picking which to run
## Unless it'd be possible to keep them separate and somehow
## share port 80... dont think so.
class Ra3Options(usage.Options):
   optParameters = [
       ['webport', 'p', 80, 'The port to run the http web services on.', portCoerce],
   ]

class Ra3ServiceFactory(object):
   implements(IServiceMaker, IPlugin)
   tapname = 'ra3'
   description = 'CnC Red Alert 3 Server Emulator'
   options = Ra3Options

   def makeService(self, options):
      from eaEmu.ea.games.redalert3 import Service
      return Service(**options)

#eaEmu = EaEmuServiceFactory()
ra3serv = Ra3ServiceFactory()
