from __future__ import absolute_import
from aspects import *

class Aspect(object):
   '''
   This is a class that creates a class decorator when called
   that will wrap all of the
   targeted class's methods with those defined in the class
   that is passed to the decorator function.
   '''
   def __init__(self, targetClass):
      self.targetClass = targetClass
      ## TODO: use singleton pattern to avoid double-wrapping?
      if not hasattr(self.targetClass, '__aspects'):
         self.targetClass.__aspects = []

   def __call__(self, klass):
      if klass.__name__ in self.targetClass.__aspects:
         return
      else:
         self.targetClass.__aspects.append(klass.__name__)
      for key, value in klass.__dict__.iteritems():
         attr = klass.__dict__[key] ## this retrieves the *unbound* method
         if not hasattr(self.targetClass, key):
            ## if defining a new attribute, just assign it
            setattr(self.targetClass, key, value)
            #print klass.__name__, 'appended', self.targetClass.__name__, key
         elif callable(attr):
            with_wrap(attr, getattr(self.targetClass, key))
            #print klass.__name__, 'wrapped', self.targetClass.__name__, key
      ## no need to return anything, the decorated class shouldn't even exist, really
      ## -- the act of decorating it wraps its targetClass
      ## TODO: do return the class that has a method to unwrap everything again

