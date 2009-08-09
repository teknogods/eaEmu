import logging
import struct

from twisted.internet.protocol import DatagramProtocol

class AvailableServer(DatagramProtocol):
   log = logging.getLogger('gamespy.available.server')
   def datagramReceived(self, data, (host, port)):
      if data.startswith('\x09\0\0\0'):
         # eg, '\x09\0\0\0\0redalert3pc\0':
         # same response for all games
         print 'available!'
         self.transport.write(struct.pack('L', 0x0009fdfe) + '\0'*3, (host, port))
      else:
         self.log.error('unhandled request: %s' % repr(data))
         # TODO (maybe just skip it and fix as needed): udp forward
         #ProxyServer.dataReceived(self, data)
