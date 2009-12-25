## TODO: this file is just dregs ATM
## things to salvage from here:
##  * move server:port lists to their respective files
##  * migrate to using twistd to launch gui reactor
from __future__ import print_function
import warnings
warnings.simplefilter('ignore', DeprecationWarning)

import re
import traceback
import os
import sys
from socket import gethostbyname

from twisted.internet import reactor

## TODO: move these to modules
servers = {
   # TODO: maybe move port #'s and hosts into the classes themselves?

   # Men of War
   'eaEmu.gamespy.games.menofwar.MowService':[
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
   'eaEmu.ea.games.mercs2.Mercs2Service':[
      ('mercs2-pc.fesl.ea.com', 18710), # makes theater server at port +1
      #('mercs2-theater.fesl.ea.com', 18715), #not needed since hostname sent by fesl
   ],

   # Burnout Paradise The Ultimate Box
   'eaEmu.ea.games.pcburnout08.Burnout08Service':[
      ('pcburnout08.ea.com', 21841), # makes theater(ish) server at port +1
   ],

   # Need for Speed SHIFT (a.k.a. pro street 2)
   'eaEmu.ea.games.nfsps2.Service':[
      ('nfsps2-pc.fesl.ea.com', 18201),
      ('nfsps2-pc.theater.ea.com', 18202), # nomally 18206 FIXME: dont hardcode these relative port offsets
   ],

   ## CNC 4
   'eaEmu.ea.games.cnc4.Service':[
      ('prodgos28.ea.com', 14611),
   ],
}

defaultServices = [
      #'eaEmu.ea.games.cnc4.Service',
      'eaEmu.ea.games.redalert3.Service',
      #'eaEmu.ea.games.nfsps2.Service',
]

## TODO: deprecate main in favor of Application + twistd
def main(argv=None):
   argv = argv or sys.argv

   interface = None
   try:
      import wx
      import eaEmu.ui.wx.wxMain
      interface = ui.wx.wxMain
   except:
      print('Couldn\'t import WX, running in console-only mode.')

   if interface:
      ## TODO: see twistd --help-reactors and use that to launch gui mode
      ## (detect what reactor's being used)
      interface.servers = servers #TODO: decouple this list from main methods
      interface.main(argv)
   else:
      from twisted.python import log
      log.startLogging(sys.stdout)
      for serviceName in defaultServices:
         mod, name = serviceName.rsplit('.', 1)
         service = getattr(__import__(mod, fromlist=[name]), name)()
         service.startService()
      reactor.run()

if __name__ == '__main__':
   main()
