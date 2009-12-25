import yaml

from zope.interface import implements
from twisted.python import usage
from twisted.plugin import IPlugin
from twisted.application.service import IServiceMaker
from twisted.application import internet
from twisted.python.usage import portCoerce

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
      with open(options['config']) as configFile:
         import eaEmu
         config = eaEmu.config = yaml.load(configFile.read())
      try:
         options.update(dict((k, v) for k, v in config['tap'][self.tapname].iteritems() if options.get(k, None) is None))
      except (KeyError, AttributeError), ex:
         pass ## section in config file was not found
      if None in options.values():
         raise Exception('Missing an essential parameter. Add it to config file or commandline.')
      options
      exec 'from {0} import Service'.format(options['module']) in globals()
      return Service(**options)

eaEmu = EaEmuServiceFactory()