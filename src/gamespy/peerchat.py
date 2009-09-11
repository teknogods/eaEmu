from __future__ import print_function
import logging

from twisted.words.protocols import irc
from twisted.words.protocols.irc import lowQuote
from twisted.internet.protocol import ServerFactory
from twisted.protocols.portforward import *
from twisted.words.service import IRCUser, WordsRealm, IRCFactory, Group
from twisted.cred.portal import Portal
from twisted.cred.checkers import ICredentialsChecker, InMemoryUsernamePasswordDatabaseDontUse
from twisted.cred import credentials
from zope.interface import implements
from twisted.internet import defer, threads
from twisted.words import iwords
from twisted.python import failure

import db
from cipher import *
import myAspects; aspects = myAspects

'''
2009-08-22 17:36:30,263 - gamespy.chatServ - received: 'JOIN #GSP!redalert3pc!Ma1a1D10cM \r\n'
2009-08-22 17:36:30,277 - gamespy.gpcm.server - server received: \status\1\sesskey\17007244\statstring\Online\locstring\\final\
2009-08-22 17:36:31,302 - gamespy.chatCli - received: ':s 702 #GPG!2167 #GPG!2167 wickybangbang BCAST :\\b_flags\\
:Jackalus!Xs1pfFWvpX|165580976@* JOIN :#GSP!redalert3pc!Ma1a1D10cM\
:s 332 Jackalus #GSP!redalert3pc!Ma1a1D10cM :RodanVSGodzilla 2v2 U CANNOT DEFEAT US!
:s 333 Jackalus #GSP!redalert3pc!Ma1a1D10cM RodanVSGodzilla 1250987477
:s 353 Jackalus = #GSP!redalert3pc!Ma1a1D10cM :@RodanVSGodzilla @Bloodtrocuted wweo77o6277ls1 Jackalus
:s 366 Jackalus #GSP!redalert3pc!Ma1a1D10cM :End of NAMES list
:RodanVSGodzilla!*@* UTM #GSP!redalert3pc!Ma1a1D10cM :PN/ 0=RodanVSGodzilla,1=Bloodtrocuted,2=wweo77o6277ls1,3=Jackalus
:RodanVSGodzilla!*@* UTM #GSP!redalert3pc!Ma1a1D10cM :SL/ M=281data/maps/official/map_mp_4_feasel1_ep1;MC=37EA6978;MS=0;SD=-72651989;GSID=118E;GT=-1;PC=-1;RU=3 100 10000 0 1 10 1 1 0 -1 0 -1 -1 1 ;S=H,4CBA6E18,0,TT,6,8,3,0,0,1,-1,:H,4CBA6E18,8088,FT,2,2,0,0,0,1,-1,:H,5E807904,8088,FT,-1,7,-1,1,0,1,-1,:H,1807794F,8088,FT,-1,7,-1,-1,0,1,-1,:X:X:;
:RodanVSGodzilla!*@* UTM #GSP!redalert3pc!Ma1a1D10cM :Pings/ ,,,,0,0
:RodanVSGodzilla!*@* UTM #GSP!redalert3pc!Ma1a1D10cM :PIDS/ d27d30c, ,d32dc69, ,cb4f9ca, ,9de90b0, , , , , ,
:RodanVSGodzilla!XvqGGW9sqX|220713740@* UTM Jackalus :NAT/ NATHOST0 1764730201 RodanVSGodzilla
2009-08-22 17:36:31,322 - gamespy.chatServ - received: 'MODE #GSP!redalert3pc!Ma1a1D10cM
SETCKEY #GPG!2167 Jackalus :\\b_flags\\s
SETCKEY #GSP!redalert3pc!Ma1a1D10cM Jackalus :\\b_flags\\s
GETCKEY #GSP!redalert3pc!Ma1a1D10cM * 030 0 :\\username\\b_flags\r\n'
2009-08-22 17:36:31,335 - gamespy.gpcm.server - server received: \status\3\sesskey\17007244\statstring\Staging\locstring\2v2 U CANNOT DEFEAT US!\final\
2009-08-22 17:36:31,375 - gamespy.chatServ - received: 'SETCKEY #GPG!2167 Jackalus :\\b_clanName\\\\b_arenaTeamID\\0\\b_locale\\0\\b_wins\\0\\b_losses\\1\\b_rank1v1\\\\b_rank2v2\\\\b_clan1v1\\\\b_clan2v2\\\\b_elo1v1\\\\b_elo2v2\\\\b_onlineRank\\1\r\nSETCKEY #GSP!redalert3pc!Ma1a1D10cM Jackalus :\\b_clanName\\\\b_arenaTeamID\\0\\b_locale\\0\\b_wins\\0\\b_losses\\1\\b_rank1v1\\\\b_rank2v2\\\\b_clan1v1\\\\b_clan2v2\\\\b_elo1v1\\\\b_elo2v2\\\\b_onlineRank\\1\r\nGETCKEY #GSP!redalert3pc!Ma1a1D10cM * 031 0 :\\b_clanName\\b_arenaTeamID\\b_locale\\b_wins\\b_losses\\b_rank1v1\\b_rank2v2\\b_clan1v1\\b_clan2v2\\b_elo1v1\\b_elo2v2\\b_onlineRank\r\n'
2009-08-22 17:36:31,467 - gamespy.chatServ - received: 'UTM #GSP!redalert3pc!Ma1a1D10cM :BCLR/ \r\n'
2009-08-22 17:36:31,478 - gamespy.chatCli - received: ':lxxx!XFlpuv9vpX|201003054@* PART #GPG!2167 :\n'
2009-08-22 17:36:31,561 - gamespy.chatCli - received: ':s 324 Jackalus #GSP!redalert3pc!Ma1a1D10cM +tnle 6\n:s 702 #GSP!redalert3pc!Ma1a1D10cM #GSP!redalert3pc!Ma1a1D10cM Jackalus BCAST :\\b_flags\\s\n:s 702 Jackalus #GSP!redalert3pc!Ma1a1D10cM Jackalus 030 :\\Xs1pfFWvpX|165580976\\s\n:s 702 Jackalus #GSP!redalert3pc!Ma1a1D10cM wweo77o6277ls1 030 :\\X19pffvffX|213187018\\s\n:s 702 Jackalus #GSP!redalert3pc!Ma1a1D10cM Bloodtrocuted 030 :\\XvqGGW9sqX|221437033\\s\n:s 702 Jackalus #GSP!redalert3pc!Ma1a1D10cM RodanVSGodzilla 030 :\\XvqGGW9sqX|220713740\\sh\n:s 703 Jackalus #GSP!redalert3pc!Ma1a1D10cM 030 :End of GETCKEY\n:s 702 #GSP!redalert3pc!Ma1a1D10cM #GSP!redalert3pc!Ma1a1D10cM Jackalus BCAST :\\b_clanName\\\\b_arenaTeamID\\0\\b_locale\\0\\b_wins\\0\\b_losses\\1\\b_rank1v1\\\\b_rank2v2\\\\b_clan1v1\\\\b_clan2v2\\\\b_elo1v1\\\\b_elo2v2\\\\b_onlineRank\\1\n'
2009-08-22 17:36:31,615 - gamespy.chatCli - received: ':s 702 Jackalus #GSP!redalert3pc!Ma1a1D10cM Jackalus 031 :\\\\0\\0\\0\\1\\\\\\\\\\\\\\1\n:s 702 Jackalus #GSP!redalert3pc!Ma1a1D10cM wweo77o6277ls1 031 :\\\\0\\0\\2\\21\\13917\\-1\\-1\\-1\\910\\-1\\5\n:s 702 Jackalus #GSP!redalert3pc!Ma1a1D10cM Bloodtrocuted 031 :\\\\0\\0\\26\\6\\-1\\-1\\-1\\-1\\-1\\-1\\6\n:s 702 Jackalus #GSP!redalert3pc!Ma1a1D10cM RodanVSGodzilla 031 :\\\\0\\0\\49\\29\\13617\\-1\\-1\\-1\\919\\-1\\12\n:s 703 Jackalus #GSP!redalert3pc!Ma1a1D10cM 031 :End of GETCKEY\n'
2009-08-22 17:36:31,663 - gamespy.chatCli - received: ':s 702 #GPG!2167 #GPG!2167 Jackalus BCAST :\\b_flags\\s\n:s 702 #GPG!2167 #GPG!2167 Jackalus BCAST :\\b_clanName\\\\b_arenaTeamID\\0\\b_locale\\0\\b_wins\\0\\b_losses\\1\\b_rank1v1\\\\b_rank2v2\\\\b_clan1v1\\\\b_clan2v2\\\\b_elo1v1\\\\b_elo2v2\\\\b_onlineRank\\1\n'
2009-08-22 17:36:32,339 - gamespy.chatServ - received: 'UTM RodanVSGodzilla :MAP 1\r\n'
2009-08-22 17:36:32,356 - gamespy.chatServ - received: 'UTM RodanVSGodzilla :REQ/ PlayerTemplate=7\r\n'
2009-08-22 17:36:32,373 - gamespy.chatServ - received: 'UTM RodanVSGodzilla :REQ/ Color=-1\r\n'
2009-08-22 17:36:32,417 - gamespy.chatServ - received: 'UTM RodanVSGodzilla :REQ/ clanID=\r\n'
2009-08-22 17:36:32,763 - gamespy.chatServ - received: 'UTM RodanVSGodzilla :NAT NATINITED3 1764730201 Jackalus\r\n'
2009-08-22 17:36:33,264 - gamespy.chatCli - received: ':RodanVSGodzilla!XvqGGW9sqX|220713740@* UTM Jackalus :NAT/ NEGO0 3 692FA55A\n'
2009-08-22 17:36:33,793 - gamespy.chatServ - received: 'UTM RodanVSGodzilla :REQ/ StartPos=2\r\n'
2009-08-22 17:36:34,140 - gamespy.chatCli - received: ':RodanVSGodzilla!*@* UTM #GSP!redalert3pc!Ma1a1D10cM :PN/ 0=RodanVSGodzilla,1=Bloodtrocuted,2=wweo77o6277ls1,3=Jackalus\n'
2009-08-22 17:36:34,359 - gamespy.chatCli - received: ':RodanVSGodzilla!*@* UTM #GSP!redalert3pc!Ma1a1D10cM :SL/ M=281data/maps/official/map_mp_4_feasel1_ep1;MC=37EA6978;MS=0;SD=-72651989;GSID=118E;GT=-1;PC=-1;RU=3 100 10000 0 1 10 1 1 0 -1 0 -1 -1 1 ;S=H,4CBA6E18,0,TT,6,8,3,0,0,1,-1,:H,4CBA6E18,8088,FT,2,2,0,0,0,1,-1,:H,5E807904,8088,FT,-1,7,-1,1,0,1,-1,:H,1807794F,8088,FT,-1,7,2,-1,0,1,-1,:X:X:;\n'
2009-08-22 17:36:34,390 - gamespy.chatCli - received: ':RodanVSGodzilla!*@* UTM #GSP!redalert3pc!Ma1a1D10cM :Pings/ ,,,,0,0\n:RodanVSGodzilla!*@* UTM #GSP!redalert3pc!Ma1a1D10cM :PIDS/ d27d30c, ,d32dc69, ,cb4f9ca, ,9de90b0, , , , , ,\n'
2009-08-22 17:36:35,199 - gamespy.chatServ - received: 'UTM RodanVSGodzilla :REQ/ StartPos=1\r\n'
2009-08-22 17:36:35,452 - gamespy.chatCli - received: ':RodanVSGodzilla!*@* UTM #GSP!redalert3pc!Ma1a1D10cM :PN/ 0=RodanVSGodzilla,1=Bloodtrocuted,2=wweo77o6277ls1,3=Jackalus\n'
2009-08-22 17:36:35,674 - gamespy.chatCli - received: ':RodanVSGodzilla!*@* UTM #GSP!redalert3pc!Ma1a1D10cM :SL/ M=281data/maps/official/map_mp_4_feasel1_ep1;MC=37EA6978;MS=0;SD=-72651989;GSID=118E;GT=-1;PC=-1;RU=3 100 10000 0 1 10 1 1 0 -1 0 -1 -1 1 ;S=H,4CBA6E18,0,TT,6,8,3,0,0,1,-1,:H,4CBA6E18,8088,FT,2,2,0,0,0,1,-1,:H,5E807904,8088,FT,-1,7,-1,1,0,1,-1,:H,1807794F,8088,FT,-1,7,1,-1,0,1,-1,:X:X:;\n'
2009-08-22 17:36:35,705 - gamespy.chatCli - received: ':RodanVSGodzilla!*@* UTM #GSP!redalert3pc!Ma1a1D10cM :Pings/ ,,,,0,0\n:RodanVSGodzilla!*@* UTM #GSP!redalert3pc!Ma1a1D10cM :PIDS/ d27d30c, ,d32dc69, ,cb4f9ca, ,9de90b0, , , , , ,\n'
2009-08-22 17:36:36,466 - gamespy.chatServ - received: 'PART #GSP!redalert3pc!Ma1a1D10cM :\r\nSETCKEY #GPG!2167 Jackalus :\\b_flags\\\r\n'
2009-08-22 17:36:36,481 - gamespy.gpcm.server - server received: \status\1\sesskey\17007244\statstring\Online\locstring\\final\
2009-08-22 17:36:36,565 - gamespy.masterSrv - received: "\x00\xd9\x00\x01\x03\x00\x00\x01\x00redalert3pc\x00redalert3pc\x000lOLkr-'(groupid=2167) AND (gamemode != 'closedplaying')\x00\\hostname\\gamemode\\hostname\\mapname\\gamemode\\vCRC\\iCRC\\cCRC\\pw\\obs\\rules\\pings\\numRPlyr\\maxRPlyr\\numObs\\mID\\mod\\modv\\name_\x00\x00\x00\x00\x04"
'''


class Peerchat(IRCUser):
   def connectionMade(self):
      IRCUser.connectionMade(self)
      self.log  = logging.getLogger('gamespy.peerchat.{0.host}:{0.port}'.format(self.transport.getPeer()))

      ## some HACKS for IRCUser compat
      self.name = '*' ## need this since user hasn't logged in yet
      self.password = '' ## FIXME, TODO: remove once auth process fixed

   def dataReceived(self, data):
      for line in data.split('\n'):
         line = line.strip('\r')
         if line:
            self.log.debug('recv IRC: {0}'.format(repr(line)))
      IRCUser.dataReceived(self, data)

   def sendLine(self, line):
      data = line + '\n' # peerchat doesn't send \r
      self.log.debug('send IRC: {0}'.format(repr(data)))
      ##don't use IRC.sendLine(self, line)! \r\n won't get encrypted!!
      self.transport.write(data)

   # TODO: enumerate GS cmd ids and use more meaningful names
   def irc_CRYPT(self, prefix, params):
      pass ## this will be handled by aspects, if at all

   def irc_USRIP(self, prefix, params):
      self.sendMessage('302', '', ':=+@{0}'.format(self.transport.getPeer().host), prefix='s')

   def irc_USER(self, prefix, params):
      #'XflsaqOa9X|165580976' is encodedIp|GSProfileId aka persona, '127.0.0.1', 'peerchat.gamespy.com', 'a69b3a7a0837fdcd763fdeb0456e77cb' is cdkey
      user, ip, host, cdkey = params
      encIp, profileId = user.split('|')

      self.user = DbUser.objects.get(id=db.Persona.objects.get(id=profileId).user.id) #HACKy XXX
      assert self.user.getIrcUserString() == user

      ## NOTE: don't call supermethod here

   _welcomeMessages = [
        (irc.RPL_WELCOME, ":connected to Twisted IRC"),
        (irc.RPL_YOURHOST, ":Your host is %(serviceName)s, running version %(serviceVersion)s"),
        (irc.RPL_CREATED, ":This server was created on %(creationDate)s"),

        # "Bummer.  This server returned a worthless 004 numeric.
        #  I'll have to guess at all the values"
        #    -- epic
        (irc.RPL_MYINFO,
         # w and n are the currently supported channel and user modes
         # -- specify this better
         "%(serviceName)s %(serviceVersion)s w n"),
        ]
   def irc_NICK(self, prefix, params):
      # TODO: assert that this user has logged in to the main login server so that impersonation
      # isn't possible like it is for the real gamespy

      # TODO: are personas available only for newer games?
      # solution is to just create 1 persona by default for each login

      # Here is the fix for impersonation: use name found during USER command
      # TODO: remove this when new auth methods are plugged in
      #self.nick = db.Persona.objects.get(user=self.user, selected=True).name

      IRCUser.irc_NICK(self, prefix, params) ## sends _welcomeMessage

   def irc_CDKEY(self, prefix, params):
      self.sendMessage('706', '1', ':Authenticated')

   def irc_JOIN(self, prefix, params):
      ## TODO: make sure everything is send just like in original peerchat impl
      IRCUser.irc_JOIN(self, prefix, params)

   def getClientPrefix(self):
      # follows RFC prefix BNF, but with encIp,gsProf
      return '{0}!{1}@*'.format(self.nick, self.user.getIrcUserString())

   def irc_PART(self, prefix, params):
      ## TODO: delete gamelobby once empty
      IRCUser.irc_PART(self, prefix, params)

   def send_UTM(self):
      for key in ('PN', 'SL', 'Pings', 'PIDS'):
         val = getattr(self.channel.gamelobby, key)
         if val:
            self.sendMessage('UTM', self.channel.name, ':{0}/ {1}'.format(key, val), prefix=self.channel.users.all()[0]) ## HACK: assumes first in list is host

   def receive(self, sender, recipient, message):
      '''
      This is an override of the regular receive that always assumes
      it has been triggered by the PRIVMSG command. This one differs in that
      it checks for  the 'command' key in the message dict for UTM etc. and sends
      that command instead.
      '''
      if iwords.IGroup.providedBy(recipient):
         recipientName = '#' + recipient.name
      else:
         recipientName = recipient.name

      text = message.get('text', '<an unrepresentable message>')
      for L in text.splitlines():
         usrStr = '%s!%s@%s' % (sender.name, sender.name, self.hostname)
         if 'command' in message:
            self.sendLine(":{0} {1} {2} :{3}".format(usrStr, message['command'], recipientName, lowQuote(L)))
         else:
            self.privmsg(
               usrStr,
               recipientName,
               L)

   def irc_UTM(self, prefix, params):
      try:
         targetName = params[0].decode(self.encoding)
      except UnicodeDecodeError:
         self.sendMessage(
            irc.ERR_NOSUCHNICK, targetName,
            ":No such nick/channel (could not decode your unicode!)")
         return

      if params[-1].startswith('KPA'):
         return
      if params[-1].startswith('NAT'):
         return

      messageText = params[-1]
      if targetName.startswith('#'):
         target = self.realm.lookupGroup(targetName[1:])
      else:
         target = self.realm.lookupUser(targetName).addCallback(lambda user: user.mind)

      def cbTarget(targ):
         if targ is not None:
            return self.avatar.send(targ, {"text": messageText, 'command':'UTM'})

      def ebTarget(err):
         self.sendMessage(
            irc.ERR_NOSUCHNICK, targetName,
            ":No such nick/channel.")

      target.addCallbacks(cbTarget, ebTarget)

   def irc_WHO(self, prefix, params):
      pass
      ## TODO
      '''
      'WHO daghros\r\n'
2009-08-23 18:50:03,828 - gamespy.masterCli - decoded: '\x00\xec\x02~G\xa8l\xbf\x19\xec\xc0\xa8\x01\x88\x19\xec@\xde\xa6mViciousPariah ViciousPariah-War Arena!\x00data/maps/internal/war_arena_v3.7_mando777/war_arena_v3.7_mando777.map\x00\x06\x06openstaging\x001.12.3444.25830\x00-117165505\x00\x00\x013 100 10000 0 1 10 0 1 0 -1 0 -1 -1 1 \x00\x00\x02\x04\x00\x00251715600\x00\x00RA3\x000\x00\x00\x00'
2009-08-23 18:50:03,898 - gamespy.chatCli - received: ':s 352 Jackalus * XsfqlGFW9X|182446558 * s daghros H :0 cea8ff6a8da628bcff9249151b46f53d\n'
'''


   def _old_irc_UTM(self, prefix, params):
      chan = params[0]
      if not chan.startswith('#'):
         return ## TODO: REQ comamnds put username instead of chan
      body = params[-1] ## should always be just 2 anyway
      if body.startswith('MAP'):
         self.sendMessage('UTM', self.nick, prefix=self.getClientPrefix())
      else:
         cmd, data = body.split('/ ', 1)
         lobby = db.GameLobby.objects.get(channel__name=chan[1:])
         if cmd == 'KPA': ## KeePAlive
            #TODO: keepalive
            pass
         elif cmd == 'SL': ## Set Lobby info?
            info = dict(pair.split('=', 1) for pair in data.split(';') if pair)
            print(info['S'])
            lobby.SL = body
         elif cmd == 'PN': ## Player Name update
            lobby.PN = body
         elif cmd == 'Pings': ## player Pings update
            lobby.Pings = body
         elif cmd == 'PIDS': ## Player IDS update
            lobby.PIDS = body
         elif cmd == 'BCLR': ## ?? no args, no reply
            pass
         elif cmd == 'REQ': ## requests a color, position, etc.
            pass # TODO: rebroadcast to all ppl in chan
         else:
            self.log.debug('unhandled UTM cmd: {0}'.format(cmd))
            #UTM #GSP!redalert3pc!MPlPcDD4PM :SL/ M=283data/maps/official/map_mp_2_feasel4;
            #MC=6CE347A5;
            #MS=0;
            #SD=1883891704;
            #GSID=7F96;
            #GT=-1;
            #PC=-1;
            #RU=3 100 10000 0 1 10 0 1 0 -1 0 -1 -1 1 ;
            #S=H,1807794F,0,TT,-1,7,-1,-1,0,1,-1,:O:O:O:X:X:;
            #'UTM #GSP!redalert3pc!MN11PzNN9M :PN/ 0=Jackalus\r\n'
            #'UTM #GSP!redalert3pc!MN11PzNN9M :Pings/ ,0,0,0,0,0\r\n'
            #'UTM #GSP!redalert3pc!MN11PzNN9M :PIDS/ 9de90b3, , , , , , , , , , , ,\r\n'
            #'UTM #GSP!redalert3pc!MN11PzNN9M :KPA/ \r\n'
         lobby.save()


   def irc_GETCKEY(self, prefix, params):
      chan, nick, rId, zero, fields = params
      fields  = fields.split('\\')[1:]

      grp = unicode(chan[1:])

      def ebGroup(err):
         err.trap(ewords.NoSuchGroup)
         pass ## TODO

      def cbGroup(group):
         if nick == '*':
            #users = db.Channels.objects.get(name=group.name).users.filter(loginsession__isnull=False) ## HACK race condition here?
            users = group.iterusers()
         else:
            users = [db.Persona.objects.get(name=nick).user]

         for user in users:
            # TODO: add get_username getter to Stats, once properties are supported, to fetch the ircUser string
            #response = ''.join('\\{0}'.format(getattr(user.stats, x)) for x in fields) # only possible with getter-methods
            response = ':'
            uName = user.getPersona().name
            stats = db.Stats.objects.get_or_create(persona=user.getPersona(), game=db.Game.objects.get(name='redalert3pc'))[0] # TODO, FIXME
            for f in fields:
               if f == 'username':
                  response += '\\{0}'.format(user.getIrcUserString())
               elif f == 'b_arenaTeamID':
                  response += '\\{0}'.format(getattr(stats, f).id)
               else:
                  response += '\\{0}'.format(getattr(stats, f))
            self.sendMessage('702', chan, uName, rId, response)
         self.sendMessage('703', chan, rId, ':End of GETCKEY')
         # 702 = RPL_GETCKEY? -- not part of RFC 1459

      self.realm.lookupGroup(grp).addCallbacks(cbGroup, ebGroup)

   def irc_SETCKEY(self, prefix, params):
      # SET triggers BCAST to others in chan as well?
      pass # TODO: analyze and implement

   def _sendTopic(self, group):
      '''
      Send the topic of the given group to this user, if it has one.
      '''
      topic = group.topic
      if topic:
         #author = group.meta.get("topic_author") or "<noone>"
         author = "<noone>"
         #date = group.meta.get("topic_date", 0)
         date = 0
         self.topic(self.name, '#' + group.name, topic)
         self.topicAuthor(self.name, '#' + group.name, author, date)

   def _setTopic(self, channel, topic):
      #<< TOPIC #divunal :foo
      #>> :glyph!glyph@adsl-64-123-27-108.dsl.austtx.swbell.net TOPIC #divunal :foo

      def cbGroup(group):
         newMeta = {}#group.meta.copy()
         newMeta['topic'] = topic
         newMeta['topic_author'] = self.name
         from time import time
         newMeta['topic_date'] = int(time())

         def ebSet(err):
            self.sendMessage(
               irc.ERR_CHANOPRIVSNEEDED,
               "#" + group.name,
               ":You need to be a channel operator to do that.")

         return defer.succeed(None)
         ## FIXME
         #return group.setMetadata(newMeta).addErrback(ebSet)

      def ebGroup(err):
         err.trap(ewords.NoSuchGroup)
         self.sendMessage(
            irc.ERR_NOSUCHCHANNEL, '=', channel,
            ":That channel doesn't exist.")

      self.realm.lookupGroup(channel).addCallbacks(cbGroup, ebGroup)


class _old_PeerchatFactory(ServerFactory):
   protocol = Peerchat

   def __init__(self,  gameName):
      self.gameName = gameName

   def buildProtocol(self, addr):
      inst = ServerFactory.buildProtocol(self, addr)
      inst.cipherFactory = PeerchatCipherFactory(db.Game.getKey(self.gameName))
      return inst

class PeerchatFactory(IRCFactory):
   protocol = Peerchat

   def __init__(self):
      realm = PeerchatRealm()
      IRCFactory.__init__(self, realm, PeerchatPortal(realm))


## INTEGRAGTION TODO:
## follow naming, callback convention, db abstraction
## move all db stuff to DbGroup and DbUser
## delete old_ peerchat
## TODO:
## * all db access should use deferToThread
## * figure out deferred chain in addGroup

## TODO: check that interfac is fully implemented
class DbGroup(db.Channel):
   implements(iwords.IGroup)

   class Meta:
      proxy = True

   clientMap = {} #double HACKy -- need to maintain this classwide as class gets reinstantiated by queries

   def __init__(self, *args, **kw):
      db.Channel.__init__(self, *args, **kw)

      if self.id not in DbGroup.clientMap:
         DbGroup.clientMap[self.id] = {}
         if not hasattr(self, 'pk'): ## must do this check to avoid clearing unsaved instance
            self.users.clear() ## clear only on first instantiation (i.e. startup)
      self.clients = DbGroup.clientMap[self.id] ## used to find Protocol+IChatClient objects by their dbUser.id
      ## self.users is in the db and contains dbUser
      ## these lists unfortunately have to be maintained separately :/
      ## TODO: handle this tracking better

   def _ebUserCall(self, err, client):
      return failure.Failure(Exception(client, err))


   def _cbUserCall(self, results):
      for (success, result) in results:
         if not success:
            clientuser, err = result.value # XXX
            self.remove(clientuser, err.getErrorMessage())

   def add(self, client):
      assert iwords.IChatClient.providedBy(client), "%r is not a chat client" % (client,)
      if client.user not in self.users.all():
         additions = []
         self.users.add(client.user)
         self.clients[client.user.id] =  client
         ## notify other clients in this group
         for usr in self.users.exclude(id=client.user.id): ## better way to write this?
            if usr.id not in self.clients:
               continue ## this is need for clients that exit badly
            clt = self.clients[usr.id]
            d = defer.maybeDeferred(clt.userJoined, self, client.user)
            d.addErrback(self._ebUserCall, client=clt)
            additions.append(d)
         ## callbacks for Deferreds in a DeferredList are fired only once all have completed
         defer.DeferredList(additions).addCallback(self._cbUserCall)
      return defer.succeed(None)

   def remove(self, client, reason=None):
      assert reason is None or isinstance(reason, unicode)
      if client.user in self.users.all():
         self.users.remove(client.user)
         removals = []
         for usr in self.users.exclude(id=client.user.id):
            clt = self.clients[client.user.id]
            d = defer.maybeDeferred(clt.userLeft, self, client.user, reason)
            d.addErrback(self._ebUserCall, client=clt)
            removals.append(d)
         del self.clients[client.user.id]
         defer.DeferredList(removals).addCallback(self._cbUserCall)
      return defer.succeed(None)

   def iterusers(self):
      ## TODO: deferToThread
      return iter(DbUser.objects.get(id=user.id) for user in self.users.all())

   def receive(self, sender, recipient, message):
      assert recipient is self
      receives = []
      for usr in self.users.exclude(id=sender.user.id):
         clt = self.clients[usr.id]
         d = defer.maybeDeferred(clt.receive, sender, self, message)
         d.addErrback(self._ebUserCall, client=clt)
         receives.append(d)
      defer.DeferredList(receives).addCallback(self._cbUserCall)
      return defer.succeed(None)


## TODO: check that interfac is fully implemented
class DbUser(db.User):
   implements(iwords.IUser)

   # FIXME: these are not preserved in db
   realm = None
   mind = None

   class Meta:
      proxy = True

   @classmethod
   def getUser(cls, name):
      return DbUser.objects.get(id=db.Persona.objects.get(name=name).user.id)

   ## NOTE that we cant use this field in queries!
   def get_name(self):
      return self.getPersona().name
   name = property(fget=get_name)

   def loggedIn(self, realm, mind):
      self.realm = realm
      self.mind = mind
      from time import time
      self.signOn = time()

   def join(self, group):
      return group.add(self.mind)

   def leave(self, group, reason=None):
      return group.remove(self.mind, reason)

   def send(self, recipient, message):
      from time import time
      self.lastMessage = time()
      return recipient.receive(self.mind, recipient, message)

class PeerchatRealm(WordsRealm):
   def __init__(self):
      WordsRealm.__init__(self, 's') ## 's' is what real peerchat uses (prly to save bandwidth)
      ## clean up channels from dirty exit
      for chan in DbGroup.objects.all():
         chan.users.clear()
         if chan.name.startswith('GSP'):
            chan.delete()

   def itergroups(self):
      return iter(DbGroup.objects)

   def addUser(self, user):
      raise NotImplementedError

   def addGroup(self, group):
      if not isinstance(group, DbGroup):
         return defer.fail() # TODO: return Failure obj as well

      ## TODO: try out this deferred chain
      #d = threads.deferToThread(group.save) ## this is all that should be needed, assuming obj is already setup
      #d.addCallback(lambda _: defer.succeed(group))
      #return d

      group.save()
      return defer.succeed(group)

   def lookupUser(self, name):
      assert isinstance(name, unicode)
      return threads.deferToThread(DbUser.getUser, name)

   def lookupGroup(self, name):
      assert isinstance(name, unicode)

      def getGroup(name):
         if name.startswith('GSP'):
            grp = DbGroup.objects.get_or_create(name=name, prettyName=name, game=db.Game.objects.get(name=name.split('!')[1]))[0] ## TODO:better way to provide game?
         else:
            grp = DbGroup.objects.get(name=name)
         return grp

      return threads.deferToThread(getGroup, name=name)

class PeerchatPortal(Portal):
   def __init__(self, realm):
      Portal.__init__(self, realm, [InsecureAccess()])

class InsecureAccess:
   '''
   TODO: fix this by checking that user is actually logged in on ealogin side.
   '''
   implements(ICredentialsChecker)
   credentialInterfaces = credentials.IUsernamePassword,

   def requestAvatarId(self, credentials):
      return defer.succeed(credentials.username)

   def checkPassword(self, password):
      return defer.succeed(True)

#---------- PROXY CLASSES --------
class CipherProxy:
   def __init__(self, server, client, gamekey):
      self.clientIngress = PeerchatCipher(server, gamekey)
      self.clientEgress = PeerchatCipher(server, gamekey)
      self.serverIngress = PeerchatCipher(client ,gamekey)
      self.serverEgress = PeerchatCipher(client ,gamekey)

   def recvFromServer(self, data):
      unenc = self.serverIngress.crypt(data)
      log = logging.getLogger('gamespy.chatCli') #HACKy
      log.debug('received: '+repr(unenc))
      if 'Unknown CD Key' in unenc:
         unenc = re.sub(r'(:s 706 \w+) .*', r'\1 1 :Authenticated', unenc)
         log.debug('but sending this instead: %s', unenc)
      return self.serverEgress.crypt(unenc)

   def recvFromClient(self, data):
      unenc = self.clientIngress.crypt(data)
      log = logging.getLogger('gamespy.chatServ') #HACKy
      log.debug('received: '+repr(unenc))
      #patches follow
      return self.clientEgress.crypt(unenc)

class ProxyPeerchatClient(ProxyClient):
   cipher = None #a little HACKy
   def dataReceived(self, data):
      # first receive should have challenges
      if not self.cipher:
         logging.getLogger('gamespy').debug(repr(data))
         sChal = data.split(' ')[-2].strip()
         cChal = data.split(' ')[-1].strip()
         self.cipher = CipherProxy(sChal, cChal, self.peer.gamekey)
      else:
         data = self.cipher.recvFromServer(data)
      ProxyClient.dataReceived(self, data)

class ProxyPeerchatClientFactory(ProxyClientFactory):
   protocol = ProxyPeerchatClient
   log = logging.getLogger('gamespy.chatCli')

class ProxyPeerchatServer(ProxyServer):
   clientProtocolFactory = ProxyPeerchatClientFactory
   def dataReceived(self, data):
      if self.peer.cipher:
         data = self.peer.cipher.recvFromClient(data)
      else:
         logging.getLogger('gamespy').debug(repr(data))
      ProxyServer.dataReceived(self, data)

class ProxyPeerchatServerFactory(ProxyFactory):
   protocol = ProxyPeerchatServer
   log = logging.getLogger('gamespy.chatSrv')

   def __init__(self, gameName, host, port):
      ProxyFactory.__init__(self, host, port)
      self.gameName = gameName

   def buildProtocol(self, addr):
      p = ProxyFactory.buildProtocol(self, addr)
      p.gamekey = db.Game.getKey(self.gameName)
      return p

##TODO: make a generic logging aspect for all Protocol objects to capture receives and sends and log based on module name
class PeerchatEncryption(object):
   __metaclass__ = aspects.Aspect(Peerchat)

   def connectionMade(self):
      self.doCrypt = False
      yield aspects.proceed

   def dataReceived(self, data):
      if self.doCrypt:
         data = self.cCipher.crypt(data)
      yield aspects.proceed(self, data)

   def sendLine(self, line):
      data = line + '\n' # peerchat doesn't send \r
      if self.doCrypt:
         data = self.sCipher.crypt(data)
      self.log.debug('send IRC: {0}'.format(repr(data)))
      ##don't use IRC.sendLine(self, line)! \r\n won't get encrypted!!
      self.transport.write(data)
      # dont continue to wrapped function, it'll try to append another newline
      yield aspects.return_stop(None)

   def irc_CRYPT(self, prefix, params):
      # params are usually 'des', '1', 'redalertpc'
      self.cipherFactory = PeerchatCipherFactory(db.Game.getKey(params[2]))
      self.sCipher = self.cipherFactory.getCipher()
      self.cCipher = self.cipherFactory.getCipher()

      self.sendMessage('705', self.cCipher.challenge, self.sCipher.challenge)
      self.doCrypt = True ## encrypt traffic henceforth
      yield aspects.proceed
