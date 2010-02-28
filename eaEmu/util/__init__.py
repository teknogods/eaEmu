from __future__ import absolute_import
import logging
import threading

from .aspects import *

def getLogger(prefix, protocol=None, host=None, port=None):
   if protocol:
      peer = protocol.transport.getPeer()
      host, port = peer.host.replace('.', '-'), peer.port
   return logging.getLogger('{0}.{1}:{2}'.format(prefix, host, port))

def hexdump(src, length=32):
   result = []
   digits = 4 if isinstance(src, unicode) else 2
   for i in xrange(0, len(src), length):
      s = src[i:i+length]
      hexa = b' '.join(["%0*X" % (digits, ord(x))  for x in s])
      text = b''.join([x if 0x20 <= ord(x) < 0x7F else b'.'  for x in s])
      result.append( b"%04X   %-*s   %s" % (i, length*(digits + 1), hexa, text) )
   return b'\n'.join(result)

class synchronized(object):
   metaLock = threading.Lock()

   def __init__(self, obj=None):
      if obj:
         with synchronized.metaLock:
            if not hasattr(obj, '__lock'):
               obj.__lock = threading.Lock()
      self.obj = obj

   def __call__(self, func):
      if not self.obj:
         ## no lock object was given
         obj = func
         with synchronized.metaLock:
            if not hasattr(obj, '__lock'):
               obj.__lock = threading.Lock()
      else:
         obj = self.obj

      def syncedFunc(*args, **kw):
         with obj.__lock:
            return func(*args, **kw)

      return syncedFunc

class SingletonMeta(type):
   def __new__(klass, name, bases, dikt):
      origNew = klass.__new__
      def new(klass, *args):
         if not hasattr(klass, '__singleton'):
            print ('no attr')
            klass.__singleton = origNew(klass, name, bases, dikt)
         return klass.__singleton
      dikt['__new__'] = new
      return type.__new__(klass, name, bases, dikt)

## class decorator
def Singleton(clsToDecorate):
   #class Singleton(clsToDecorate, object):
   def __new__(klass, *args):
      if not hasattr(klass, '__singleton'):
         print ('no attr')
         klass.__singleton = super(type(klass), klass).__new__(klass, *args)
      return klass.__singleton
   #return Singleton
   clsToDecorate.__new__ = __new__
   return clsToDecorate

def Singleton(target):
   def newWrap(klass, *args):
      if not hasattr(klass, '__singleton'):
         print ('no attr')
         klass.__singleton = super(klass.__class__, klass).__new__(klass, *args)
      return klass.__singleton
   print('ohai')
   from .aspects import with_wrap
   aspects.with_wrap(newWrap, target)
   return target

def Singleton(target):
   if not hasattr(target, '__new__'):
      target.__new__ = lambda *a, **k: None
   def newWrap(klass, *args):
      print('hi')
      if not hasattr(target, '__singleton'):
         print ('no attr')
         target.__singleton = yield aspects.proceed
      yield aspects.return_stop(target.__singleton)
   aspects.with_wrap(newWrap, target.__new__)
   return target
