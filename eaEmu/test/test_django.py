from __future__ import absolute_import
from twisted.trial import unittest
from twisted.internet.threads import deferToThread
from twisted.internet import defer

from ..db import Channel, User

class DjangoRaceConditions(unittest.TestCase):
   def setUp(self):
      pass

   def test_getOrCreate(self):
      chan = Channel.objects.get(id=1)
      user = User.objects.get(login='Keb')
      chan.users.clear()

      def cbAdded(result, times):
         chan = Channel.objects.get(id=1)
         user = User.objects.get(login='Keb')
         print 'added', chan.users.all()
         return deferToThread(chan.users.remove, user).addCallback(cbRemoved, times)

      def cbRemoved(result, times):
         chan = Channel.objects.get(id=1)
         user = User.objects.get(login='Keb')
         print 'removed', chan.users.all()
         if times > 0:
            return deferToThread(chan.users.add, user).addCallback(cbAdded, times - 1)
         else:
            print 'done', chan.users.all()
            return defer.succeed(None)

      print
      print user.login
      print chan.prettyName

      dfr = deferToThread(chan.users.add, user).addCallback(cbAdded, 2)
      return dfr

