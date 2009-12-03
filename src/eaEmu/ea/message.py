import struct
import urllib
import copy

class Message:
   def __init__(self, id='XXXX', flags=0, map=None, extraLines=None, transport=None):
      self.id = id
      self.flags = flags
      self.extraLines = extraLines or []
      self.transport = transport
      self.map = map or {} # init this last (see setattr for reason)
      self.unflatten()

   def __getattr__(self, name):
      if name in self.__dict__:
         value = self.__dict__[name]
      else:
         value = self.map[name]
      return value

   def __setattr__(self, name, value):
      if name in self.__dict__ or 'map' not in self.__dict__:
         self.__dict__[name] = value
      else:
         self.map[name] = value

   def __delattr__(self, name):
      del self.map[name]

   def send(self):
      if self.transport:
         self.transport.write(str(self))
      else:
         raise Exception('transport not provided')

   def __repr__(self):
      'representation of the message suitable for sending over the wire'
      self.flatten()
      body = '\n'.join(['{0}={1}'.format(k, self.quote(v)) for k, v in self.map.iteritems()] + self.extraLines) + '\0'
      self.unflatten()
      length = len(body) + 12 # length includes 12 byte header
      return self.id + struct.pack('!2L', self.flags, length) + body

   def flatten(self):
      fmt = '{0}.{1}'
      # TODO: simpler to write this to work in-place?
      def _flatten(name, obj):
         d = {}
         if isinstance(obj, dict):
            for k, sub in obj.items():
               key = fmt.format(name, k) if name else k
               d.update(_flatten(key, sub))
         elif type(obj) in [list, tuple]:
            d = {fmt.format(name, '[]'):len(obj)}
            for i, e in enumerate(obj):
               d.update(_flatten(fmt.format(name, i), e))
         else:
            d = {name:str(obj)}
         return d

      self.map = _flatten(None, self.map)

   # I'm ambivalent about True as the default for collapse,
   # since EA is inconsistent about it's data structures.
   # If dotted names arent dictionaries then they shouldnt appear as elements
   # of a list! Because of that I have to use a dict to store dotted names
   # in a list collapsed list, making the dict() type ambiguous. In practice,
   # when collapse is True, dictionaries that are not immediate children
   # of lists are EAMappings.
   #
   # TODO: make the msg class support access via msg['a.b'] or msg['a']['b'] or msg.a.b
   def unflatten(self, collapse=True):
      def _unflatten(map, collapse):
         for k, v in map.items():
            if '.' in k:
               name, rest = k.split('.', 1)
               if name not in map:
                  map[name] = {}
               map[name][rest] = v
               del map[k]
         for k, sub in map.items():
            if isinstance(sub, dict):
               _unflatten(sub, collapse)
               if '[]' in sub:
                  # convert to list object
                  map[k] = [sub[str(x)] for x in range(int(sub['[]']))]
               elif '{}' in sub:
                  # TODO: convert to EAmapping object
                  # right now, just prune all "{}" chars
                  #del sub['{}']
                  pass#map[k] = dict((x.strip('{}'), y) for x, y in sub.items())
                  # FIXME: HACKed out cuz it broke fwdServ
               elif collapse:
                  if '[]' not in map: # don't collapse dicts in lists
                     for sk in sub.keys():
                        map['.'.join([k, sk])] = sub[sk]
                     del map[k]
      _unflatten(self.map, collapse)

   # Url quotes a few characters. This seems to be a very selective url quote.
   # Also uses lowercase letters.
   def quote(self, s):
      s = str(s)
      # FIXME: hacked out cuz it broke fwdServ
      # Where was this originally used though? ra3 fesl somewhere i think...
      #s = s.replace(':', '%3a')
      s = s.replace('=', '%3d')
      return s

   def __str__(self):
      'pretty repersentation of the message'
      parts = [
         '({0} on {1.host}:{1.port})'.format(self.__class__.__name__, self.transport.getPeer()),
         'id={0}'.format(self.id),
         'flags={0:#010x}'.format(self.flags),
      ]
      m = self.map
      if 'decodedSize' in m and m['decodedSize'] > 100:
         m = m.copy()
         m['data'] = m['data'][:32] + '...'
      #parts.append('dict: {0}'.format(','.join('{0}={1}'.format(k, m[k]) for k in sorted(m.keys()))))
      parts.append('dict: {0}'.format(repr(m)))
      if self.extraLines:
         parts.append('extraLines: ' + ' '.join(self.extraLines))
      return ' '.join(parts)

   # i know mappings and dicts are the same but this one is for internal use
   # only because i only discovered the "mappings" with '{}' in the key names
   # later. I still want to treat dotted names as dicts, but need to support the
   # explicit {} kind as well. To add one of the latter, use addMapping()
   #
   # for now i'm just treating "Mappings" the same as regular dicts, just with
   # goofy key names. Eventually it may be necessary to give them distinct
   # types, but prly not.
   def addMapping(self, name, contents):
      map = dict(('{{{0}}}'.format(k), v) for k, v in contents.items())
      map['{}'] = len(map)
      self.map[name] = map

   def makeReply(self, map=None):
      ''' subclass should make any appropriate changes to flags,contents after calling this supermethod '''
      reply = copy.copy(self)
      reply.map = {}
      if map: reply.map.update(map)
      return reply

   def getKey(self):
      return ''.join([self.id,])

class MessageFactory:
   def __init__(self, transport, msgClass=Message):
      self.transport = transport
      self.msgClass = msgClass

   def getMessages(self, data):
      messages = []
      while len(data):
         id, flags, length = struct.unpack('!4s2L', data[:12])
         # map takes format: "name=value\n... \0" (final [\n]\0 terminator)
         # HACK/FIXME:In burnout 08, sometimes the length is longer than len(data)
         # and msg is continued in next packet. This is currently unhandled.
         #msg.map = dict([urllib.unquote(x) for x in line.split('=', 1)] for line in data[12:msg.length].strip('\n\0').split('\n'))
         sep = '\n'
         if '\t' in data[12:length]: sep = '\t'#HACK? sometimes separator is tab char!! (burnout 3rd msg)
         map = {}
         extraLines = []
         for line in data[12:length].strip(sep+'\0').split(sep):
            if '=' in line:
               k, v = line.split('=', 1)
               map[k] = urllib.unquote(v)
               #if k == 'ADDR': msg.map[k] = '5.84.34.44'
            else:
               #print 'not a key-value pair: "{0}"'.format(line)
               extraLines.append(line)
         messages.append(self.msgClass(id, flags, map, extraLines, self.transport))
         data = data[length:]
      return messages
