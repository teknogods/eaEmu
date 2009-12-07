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

def hexdump(src, length=32):
   result = []
   digits = 4 if isinstance(src, unicode) else 2
   for i in xrange(0, len(src), length):
      s = src[i:i+length]
      hexa = b' '.join(["%0*X" % (digits, ord(x))  for x in s])
      text = b''.join([x if 0x20 <= ord(x) < 0x7F else b'.'  for x in s])
      result.append( b"%04X   %-*s   %s" % (i, length*(digits + 1), hexa, text) )
   return b'\n'.join(result)

