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

   def __call__(self, klass):
      for key, value in klass.__dict__.iteritems():
         if not hasattr(self.targetClass, key):
            ## if defining a new attribute, just assign it
            setattr(self.targetClass, key, value)
         else:
            ## getattr won't work!! If used, the method will be bound to
            ## 'klass' and consequently assert that 'self' is of the correct type
            ## when invoked.
            #attr = getattr(klass, key)
            attr = klass.__dict__[key]
            if callable(attr):
                  with_wrap(attr, getattr(self.targetClass, key))
                  #print 'wrapped', key
      ## no need to return anything, the decorated class shouldn't exist
      ## -- the act of decorating it wraps its targetClass
      ## TODO: do return the class that has a method to unwrap everything again

