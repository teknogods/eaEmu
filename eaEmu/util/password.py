import md5
import base64

from twisted.internet.threads import deferToThread
from twisted.enterprise.adbapi import ConnectionPool

from ..ea.errors import EaError

def reverse64encode(data):
   '''
   PHP base64 takes reads hextets right to left rather than left to right, so
   this function can be used to encode a binary string in that sequence.
   '''
   np = 3 - len(data) % 3 ## number of pad chars
   data = ''.join('\x00' for _ in range(np)) + data[::-1]
   return base64.b64encode(data)[:np-1 if np else None:-1]

_phpAlph64 = './0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz'
def php64translate(b64data, reverse=False):
   '''
   Translates from the regular base64 alphabet to the one used by php --
   no padding and rearranged alphabet.
   '''
   return b64translate(b64data, _phpAlph64, reverse)

_translation = [chr(_x) for _x in range(256)]

def b64translate(b64data, newAlph, reverse=False):
   '''
   Applies a translation to base64 data.

   newAlph should be a string of chars from vals 0..63, then the optional pad char.
   '''
   alph = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/='
   if len(newAlph) < 64:
      raise Exception('Alphabet too short.')
   elif len(newAlph) == 64:
      newAlph += '=' ## default pad byte
   translation = _translation[:]
   tTable = dict(zip(alph, newAlph))
   if reverse:
      tTable = dict(zip(newAlph, alph))
   for k, v in tTable.iteritems():
      translation[ord(k)] = v
   return b64data.translate(''.join(translation))

class PasswordChecker(object):
   def __init__(self, user):
      self.user = user

   def check(self, input):
      return False

class PlainTextPassword(PasswordChecker):
   def check(self, user):
      return self.user.password == input

class PhpPassword(PasswordChecker):
   def __init__(self, user, prefix='$H$'):
      super(PhpPassword, self).__init__(user)
      self.password = self.user.password
      self.prefix = prefix

   def check(self, input):
      '''
      This algorithm is adapted from the Portable PHP Password Hashing Framework by Alexander Chemeris
      http://www.openwall.com/phpass/

      It was written pretty sloppily, so I cleaned it up.
      '''
      if not self.password.startswith(self.prefix) or len(self.password) < 12:
         return False

      count_log2 = _phpAlph64.index(self.password[3])
      if count_log2<7 or count_log2>30:
         #raise Exception('Bad count_log2')
         return False
      count = 1<<count_log2

      salt = self.password[4:12]
      if len(salt) != 8:
         raise Exception('hash not long enough')

      m = md5.new(salt)
      m.update(input)
      tmp_hash = m.digest()
      for i in xrange(count):
         m = md5.new(tmp_hash)
         m.update(input)
         tmp_hash = m.digest()

      return self.password == self.password[:12] + php64translate(reverse64encode(tmp_hash))

class RemotePhpPassword(PhpPassword):
   _info = {
      'dbapiName' : 'MySQLdb',
      'host'      : 'teknogods.com',
      'user'      : 'teknogod',
      'passwd'    : 'hm9tzuh9',
      'db'        : 'teknogodscom',
   }
   #_info = {'dbapiName':'sqlite3', 'database':'eaEmu.db')

   def __init__(self, user):
      super(RemotePhpPassword, self).__init__(user=user)

   def check(self, input):
      ## TODO: opening every time a pwd is checked is pretty inefficient...
      def openDbConn():
         return ConnectionPool(**self._info) ## doesnt actually connect until query is run?

      def cbConnOpen(db):
         return db.runQuery('SELECT user_password FROM phpbb_users WHERE username = "{0}"'.format(self.user.login))

      def ebRunQuery(err):
         print 'couldnt open connection to phpbb db -- {0}'.format(err.value)
         ## consume the error and return False for match
         #return False ## TODO: maybe raise an exception that leads to an EaError message being printed
         raise EaError.BackendFail

      def cbGotPwd(result):
         self.password = result[0][0]
         return super(RemotePhpPassword, self).check(input)

      #dfr.setTimeout(5) ## FIXME: this doesnt work as expected
      return deferToThread(openDbConn).addCallbacks(cbConnOpen).addCallbacks(cbGotPwd, ebRunQuery)
