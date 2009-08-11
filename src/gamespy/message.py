

class GamespyMessage:
   def __init__(self, data):
      self.data = data
      self.map = dict(self.data)
   
   def __repr__(self):
      #return ''.join(['\\{0}\\{1}'.format(k, v) for k, v in self.data.iteritems()] + ['final\\'])
      return ''.join(['\\{0}\\{1}'.format(k, v) for k, v in self.data] + ['\\final\\'])

def parseMsgs(data, xor=False):
   # this technique does not properly discard garbage
   # Should use regex r'(\\.*\\.*\\)+\\final\\'
   msgs = []
   for msg in [gs_xor(x) if xor else x for x in data.split('\\final\\') if x]:
      tokens = msg.split('\\')[1:]
      msgs.append(GamespyMessage(zip(tokens[::2], tokens[1::2])))
   return msgs
