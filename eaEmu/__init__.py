from __future__ import print_function

import os
import yaml
import logging
import logging.config

from twisted.python import log

# This twisted log observer is useful for duping all log messages to the
# built-in python logging module. This is necessary in WingIDE, where the
# option to catch logged exceptions can be turned on. Without that option and
# this LogObs, twisted catches and swallows all deferred exceptions printed on
# __del__(), making it all but impossible to debug them in Wing.
class LogObs(log.PythonLoggingObserver):
   def emit(self, eventDict):
      text = log.textFromEventDict(eventDict)
      if text is None:
         return

      if 'logLevel' in eventDict:
         self.logger.log(eventDict['logLevel'], text)
      elif eventDict.get('isError', False) and not eventDict.get('printed', False):
         self.logger.exception(text)
      else:
         self.logger.info(text)

logCfg = 'logging.cfg'
if os.path.isfile(logCfg):
   ## load the logging config
   logging.config.fileConfig(logCfg)
   ## start duping the twisted log lines into python's logging module
   LogObs().start()
else:
   print('{0} not found -- network traffic logging disabled.'.format(logCfg))

def loadConfig(filePath):
   with open(filePath) as configFile:
      global config
      config = yaml.load(configFile.read())
      return config

# this gets filled in by eaEmu.twistd, normally, but do this
# just in case something is trying to import a module that
# relies on it's presence.
try:
   config = loadConfig('config.yml')
except:
   print('couldnt load config')
   config = None

