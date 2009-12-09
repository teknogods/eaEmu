from twisted.application.internet import TimerService
from twisted.application.service import Service
from twisted.internet import task
from twisted.internet import defer


class LoopingCall(task.LoopingCall):
   def __call__(self):
      def cb(result):
         if self.running:
            self._reschedule()
         else:
            d, self.deferred = self.deferred, None
            d.callback(self)

      def eb(failure):
         self.running = False
         d, self.deferred = self.deferred, None
         d.errback(failure)

      ## HACK: bug -- reactor.callLater()
      ## seems to ignore .cancel() requests, so this
      ## method ends up getting called after the loop
      ## has been stopped.
      if self.running:
         self.call = None
         d = defer.maybeDeferred(self.f, *self.a, **self.kw)
         d.addCallbacks(cb, eb)

class KeepaliveService(TimerService):
   def __init__(self, pingFunc, step, onTimeout, now=True):
      self.step = step
      self.call = (pingFunc, [], {}) # need args to pingFunc?
      self.onTimeout = onTimeout
      self.now = now
      self.ping = defer.Deferred()

   def alive(self):
      if self.ping.called:
         if self.running:
            ## delay until now + step
            self._loop.stop()
            self._loop.start(self.step, now=False)
      else:
         self.ping.callback(None)

   def startService(self):
      ## this implementation of startService overrides the original

      if self.running:
         return

      Service.startService(self)
      pingFunc, args, kwargs = self.call

      def pingFail(failure):
         failure.trap(defer.TimeoutError)
         #print 'Call to %s timed out. Calling onTimeout and stopping service.' % (pingFunc.__name__,)
         self.onTimeout()
         self.stopService()

      def sendPing():
         self.ping = defer.Deferred()
         ## the pingFunc is assumed to be a syncronous function that
         ## sends the request along to the client and returns immediately.
         ## TODO: maybe assume that this returns a deferred that is fired when
         ## the response is received?
         pingFunc(*args, **kwargs)
         self.ping.addErrback(pingFail)
         self.ping.setTimeout(self.step - 1) # timeout if no response before next iteration
         return self.ping ## LoopingCall will reschedule as soon as this fires

      self._loop = LoopingCall(sendPing)
      self._loop.start(self.step, now=self.now).addErrback(self._failed)

   def stopService(self):
      ## bug in TimerService if you stop when hasnt yet started...
      ## because of condition "not hasattr(self, '_loop')"
      if self.running:
         return TimerService.stopService(self)
