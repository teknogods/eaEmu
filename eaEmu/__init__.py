from __future__ import print_function

import os
import logging
import logging.config

from twisted.python import log

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
   logging.config.fileConfig(logCfg)
   LogObs().start()
else:
   print('{0} not found -- network traffic logging disabled.'.format(logCfg))
