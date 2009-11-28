import struct
import logging

from twisted.internet.protocol import Protocol, ServerFactory

class GamespyAuth(Protocol):

   def connectionMade(self):
      peer = self.transport.getPeer()
      self.log = logging.getLogger('gamespy.auth.{0}:{1}'.format(peer.host.replace('.','-'), peer.port))

   def dataReceived(self, data):
      hdrFmt = '!4s4sL'
      hLen = struct.calcsize(hdrFmt)
      lgr, err, length = struct.unpack(hdrFmt, data[:hLen])
      data = data[hLen:]
      self.log.debug('received: {0}'.format(repr(data)))

      #HACKy handling for quick and dirty impl.
      if data.startswith('STR=00000000'):
         # initial message.
         # no body to the response.
         self.transport.write(struct.pack(hdrFmt, lgr, '\x00'*4, hLen))
      elif data.startswith('STR'):
         self.transport.loseConnection()

class GamespyAuthFactory(ServerFactory):
   protocol = GamespyAuth

