#!/usr/bin/env python2.6
import warnings
warnings.simplefilter('ignore', DeprecationWarning)

interface = None

try:
   import wx
   import ui.wx.wxMain
   interface = ui.wx.wxMain
except:
   print 'Couldn\'t import WX, running in console-only mode.'

from twisted.internet import reactor

import re
import traceback
import os
import logging
import logging.config
import sys
from socket import gethostbyname

from twisted.python import log


servers = {
   # TODO: maybe move port #'s and hosts into the classes themselves?

   # Men of War
   'gamespy.games.menofwar.MowService':[
      ('gpcm.gamespy.com', 29900),
      ('peerchat.gamespy.com', 6667),
      ('files.bestway.com.ua', 80),
      ('motd.gamespy.com', 80),
      ('menofwarpc.available.gamespy.com', 27900),
      ('menofwarpc.ms6.gamespy.com', 28910),
      ('menofwarpc.gamestats.gamespy.com', 29920),
      ('menofwarpc.master.gamespy.com', 29910), # 29910 is keycheck, 27900 for natneg
      ('menofwarpc.natneg1.gamespy.com', 27901),
      ('menofwarpc.natneg2.gamespy.com', 27901),
      ('menofwarpc.natneg3.gamespy.com', 27901),
      ],

   # Mercs 2
   'ea.games.mercs2.Mercs2Service':[
      ('mercs2-pc.fesl.ea.com', 18710), # makes theater server at port +1
      #('mercs2-theater.fesl.ea.com', 18715), #not needed since hostname sent by fesl
   ],

   # Burnout Paradise The Ultimate Box
   'ea.games.pcburnout08.Burnout08Service':[
      ('pcburnout08.ea.com', 21841), # makes theater(ish) server at port +1
   ],

   # RA 3
   'ea.games.redalert3.Service':[
      ('cncra3-pc.fesl.ea.com', 18840),
      #('cncra3-pc.theater.ea.com', 18845), # not in use by EA, not strictly needed anyway
      ('redalert3pc.available.gamespy.com', 27900),
      ('na.llnet.eadownloads.ea.com', 80), # this is used in 1.4
      #('servserv.generals.ea.com', 80), # this is used in 1.0
      ('peerchat.gamespy.com', 6667),
      ('gpcm.gamespy.com', 29900),
      ('redalert3pc.ms1.gamespy.com', 28910),
      ('redalert3services.gamespy.com', 80),
      ('redalert3pc.sake.gamespy.com', 80),
      ('psweb.gamespy.com', 80),
      ('redalert3pc.auth.pubsvs.gamespy.com', 80),
      ('redalert3pc.comp.pubsvs.gamespy.com', 80),
      ('redalert3pc.natneg1.gamespy.com', 80),
      ('redalert3pc.natneg2.gamespy.com', 80),
      ('redalert3pc.natneg3.gamespy.com', 80),
   ],
   # Need for Speed SHIFT (a.k.a. pro street 2)
   'ea.games.nfsps2.Service':[
      ('nfsps2-pc.fesl.ea.com', 18201),
      ('nfsps2-pc.theater.ea.com', 18202), # nomally 18206 FIXME: dont hardcode these relative port offsets
   ],

   ## CNC 4
   'ea.games.cnc4.Service':[
      ('prodgos28.ea.com', 14611),
   ],
}

def main(argv=None):
   argv = argv or sys.argv

   logCfg = 'logging.cfg'
   if os.path.isfile(logCfg):
      logging.config.fileConfig(logCfg)
   else:
      print '{0} not found -- network traffic logging disabled.'.format(logCfg)

   if interface:
      interface.servers = servers #TODO: decouple this list from main methods
      interface.main(argv)
   else:
      log.startLogging(sys.stdout)
      for serviceName in [
         'ea.games.cnc4.Service',
         #'ea.games.redalert3.Service',
         #'ea.games.nfsps2.Service',
         ]:
         addresses = servers[serviceName]
         mod, name = serviceName.rsplit('.', 1)
         service = getattr(__import__(mod, fromlist=[name]), name)(addresses)
         service.startService()
      reactor.run()

if __name__ == '__main__':
   main()
