from types import FunctionType

from aspects import *

def Aspect(targetClass):
   '''
   This is a function that creates a class decorator that will wrap all of the
   targeted class's methods with those defined in the class
   that is passed to it.
   '''
   def decorator(aspectClass):
      for key in aspectClass.__dict__:
          ## getattr won't work!! The method will be "bound" to 
          ## 'klass' and assert that 'self' is of the correct type
          #attr = getattr(klass, key)
          attr = aspectClass.__dict__[key]
          if type(attr) is FunctionType:
                  with_wrap(attr, getattr(targetClass, key))
                  #print 'wrapped', key
   return decorator

