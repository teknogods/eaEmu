class Mapping(type):
   def __new__(self, name, bases, dikt):
      klass = type.__new__(self, name, bases, dikt)
      klass.__realDict__ = dikt.copy()
      return klass

   def getattr(self, name):
      if name in self.__realDict__:
         return self.__realDict__[name]
      else:
         return self.__dict__[name]

   def setattr(self, name, value):
      if name.startswith('_') or name in self.__realDict__:
         self.__realDict__[name] = value
      else:
         self.__dict__[name] = value

class GamespyMessage(object):
   __metaclass__ = Mapping

   def __init__(self, pairs):
      self._pairs = pairs
      self.__dict__.update(dict(pairs))

   def __str__(self):
      return str(self._pairs)

   def __repr__(self):
      #return ''.join(['\\{0}\\{1}'.format(k, v) for k, v in self.data.iteritems()] + ['final\\'])
      return ''.join(['\\{0}\\{1}'.format(k, v) for k, v in self._pairs] + ['\\final\\'])

class MessageFactory:
   @staticmethod
   def getMessages(data, xor=False):
      # this technique does not properly discard garbage
      # Should use regex r'(\\.*\\.*\\)+\\final\\'
      msgs = []
      for msg in [gs_xor(x) if xor else x for x in data.split('\\final\\') if x]:
         tokens = msg.split('\\')[1:]
         msgs.append(GamespyMessage(zip(tokens[::2], tokens[1::2])))
      return msgs

   @staticmethod
   def getMessage(*args):
      return GamespyMessage(*args)

