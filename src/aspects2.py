from types import FunctionType

from aspects import *

def Aspect(targetClass):
   '''
   This is a factory function to create a metaclass that will wrap all of the
   targeted class's methods with those defined in the class it constructs.
   '''
   class meta(type):
      def __new__(self, name, bases, dikt):
      	klass = type.__new__(self, name, bases, dikt)
	for key in dikt:
		## getattr won't work!! The method will be "bound" to 
		## 'klass' and assert that 'self' is of the correct type
		#attr = getattr(klass, key)
		attr = klass.__dict__[key]
		if type(attr) is FunctionType:
			with_wrap(attr, getattr(targetClass, key))
			#print 'wrapped', key
	return klass
   return meta

