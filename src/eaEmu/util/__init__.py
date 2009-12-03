import logging

def getLogger(prefix, protocol=None, host=None, port=None):
   if protocol:
      peer = protocol.transport.getPeer()
      host, port = peer.host.replace('.', '-'), peer.port
   return logging.getLogger('{0}.{1}:{2}'.format(prefix, host, port))

class AttachMethod(object):
   def __init__(self, klass):
      self.klass = klass

   def __call__(self, func):
      setattr(self.klass, func.__name__, func)
