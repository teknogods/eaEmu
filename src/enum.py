## TODO: add importToLocal() method that writes vals into local namespace
import types

class EnumException(Exception):
    pass

class EnumType(type):
    def __new__(klass, name, bases, dikt):
        reverse = dict((v, k) for k, v in dikt.iteritems())
        dikt['__enum__'] = dikt.copy() # backup copy of orig enumvals
        dikt['_reverseLookup'] = reverse
        newCls =  type.__new__(klass, name, bases, dikt)
        if name == '': # if class is nameless only instantiation of this metaclass could have produced it
            newCls.__name__ = 'AnonymousEnum_%x' % hash(newCls)
        return newCls

    def whatis(klass, value):
        return klass._reverseLookup[value]

class Enum(object):
   __metaclass__ = EnumType

def enum(*args):
        '''
        enum([name ,]<enumList>)
        '''
        if len(args) == 1:
            enumList = args[0]
            name = ''
        else:
            name, enumList = args
        lookup = {}
        reverseLookup = {}
        i = 0
        uniqueNames = []
        uniqueValues = []
        for x in enumList:
            if type(x) == types.TupleType:
                x, i = x
            if type(x) != types.StringType:
                raise EnumException('enum name is not a string: ' + x)
            if type(i) != types.IntType:
                raise EnumException('enum value is not an integer: ' + i)
            if x in uniqueNames:
                raise EnumException('enum name is not unique: ' + x)
            if i in uniqueValues:
                raise EnumException('enum value is not unique for ' + x)
            uniqueNames.append(x)
            uniqueValues.append(i)
            lookup[x] = i
            reverseLookup[i] = x
            i = i + 1
        return EnumType(name, (Enum,), lookup)

'''
# these are all valid
class abcd(Enum):
   a = 1
   b = 2
   c = 3
   d = 4
abc = enum(['a', 'b', 'c'])

Volkswagen = enum([
     'JETTA',
     'RABBIT',
     'BEETLE',
     ('THING', 400),
     'PASSAT',
     'GOLF',
     ('CABRIO', 700),
     'EURO_VAN',
     'CLASSIC_BEETLE',
     'CLASSIC_VAN'
])

Insect = enum('Insect', [
     'ANT',
     'APHID',
     'BEE',
     'BEETLE',
     'BUTTERFLY',
     'MOTH',
     'HOUSEFLY',
     'WASP',
     'CICADA',
     'GRASSHOPPER',
     'COCKROACH',
     'DRAGONFLY'
])


#print Volkswagen.EURO_VAN
#print Volkswagen.whatis(702)
#print Volkswagen.__name__
#print abc.__name__
#print abcd.__name__
'''
