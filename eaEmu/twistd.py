import yaml

from zope.interface import implements
from twisted.python import usage
from twisted.plugin import IPlugin
from twisted.application.service import IServiceMaker
from twisted.application import internet
from twisted.python.usage import portCoerce

def loadConfig(filePath):
   with open(filePath) as configFile:
      import eaEmu
      eaEmu.config = yaml.load(configFile.read())
      return eaEmu.config


## TODO: migrate to a eaEmu service that uses flags or config.yml to determine what services run
## The service should be put together based on what's in the tap section of config.yml
## Or maybe just select 'ra3' or 'mow' or 'mercs2' in the config and then start up that service
## TODO: consider finding a way to run 'ra3' and 'mercs2' by somehow sharing port 80
class EaEmuOptions(usage.Options):
   #optParameters = [['port', 'p', 1235, 'The port number to listen on.']]
   optParameters = [
      ['config', 'c', 'config.yml',
       'The YAML-formatted config file to load settings from. Any other options given on the command line overwrite what\'s in this file.'],
      ['webPort', 'p', None, 'The port to run the http web services on.', portCoerce],
      ['module', 'm', None, 'What module to load the Service from.'],
   ]

class EaEmuServiceFactory(object):
   implements(IServiceMaker, IPlugin)
   tapname = 'eaEmu'
   description = 'EA Online Server Emulator'
   options = EaEmuOptions

   def makeService(self, options):
      config = loadConfig(options['config'])
      try:
         options.update(dict((k, v) for k, v in config['tap'][self.tapname].iteritems() if options.get(k, None) is None))
      except (KeyError, AttributeError), ex:
         pass ## section in config file was not found
      if None in options.values():
         raise Exception('Missing an essential parameter. Add it to config file or commandline.')
      exec 'from {0} import Service'.format(options['module']) in globals()
      return Service(**options)

eaEmu = EaEmuServiceFactory()

class PeerchatProxyOptions(usage.Options):
   optParameters = [
      ['port', 'p', 6667, 'The port to run the proxy on.', portCoerce],
      ['host', 'h', 'tgo.teknogods.com', 'The hostname of the peerchat server to connect to.'],
      ['game', 'g', 'redalert3pc', 'The game id of the peerchat server.'],
   ]

class PeerchatProxyServiceFactory(object):
   implements(IServiceMaker, IPlugin)
   tapname = 'peerchatProxy'
   description = 'Proxy server that allows regular IRC clients to connect to peerchat servers.'
   options = PeerchatProxyOptions

   def makeService(self, options):
      config = loadConfig('config.yml')
      from eaEmu.gamespy.peerchatProxy import Service
      return Service(**options)


peerchatProxy = PeerchatProxyServiceFactory()