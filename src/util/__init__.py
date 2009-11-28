import logging

def getLogger(prefix, protocol=None, host=None, port=None):
   if protocol:
      peer = protocol.transport.getPeer()
      host, port = peer.host.replace('.', '-'), peer.port
   return logging.getLogger('{0}.{1}:{2}'.format(prefix, host, port))
