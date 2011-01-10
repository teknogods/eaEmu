from __future__ import absolute_import

#from ..login import EaServer, MessageHandler
from ..login import * # all handlers too
from ..message import Message
from ...util import getLogger
from ...db import *

from twisted.application.internet import SSLServer, TCPServer
from twisted.application.service import MultiService
from twisted.protocols.portforward import *
from twisted.internet.protocol import ServerFactory
#from twisted.application.internet import TimerService

import time
import random
import logging
import base64

class Mercs2Session(LoginSession):
   def __init__(self, *args, **kw):
      super(Mercs2Session, self).__init__(*args, **kw)
      self.theater = Theater.objects.get(name='mercs2')

   # Here's how a session is hosted and joined. (I think) Message
   # sequence is left-to-right, top-to-bottom in this table.
   #  Host       Theater    Guest
   #  CGAM      CGAM                # host creates game
   #  EGAM      EGAM                # host enters own game
   #            EGRQ                # thtr fwds request to enter to self
   #  EGRS      EGRS                # host allows it
   #            EGEG                # host is allowed to enter
   #  PENT      PENT                # Player ENTered
   #                        EGAM    # guest wants to join
   #                EGAM
   #            EGRQ                # unconfirmed !
   #  EGRS      EGRS                # unconfirmed !
   #                EGEG            # ok come on in! (what's "denied"?) maybe guest always gets EGEG then just ECNL if not allowed?
   #                        PENT?
   #
   def CreateGame(self, opts): # TODO: change arg to **opts or obj with keys in it
      # is this already available to us in the db?
      self.__dict__.update(
         ext_ip = msg.transport.getPeer().host,
         ext_port = msg.map['PORT'],
         int_ip = msg.map['INT-IP'],
         int_port = msg.map['INT-PORT'],
      )
      self.save()

      game = GameSession.objects.create(
         list = GameList.objects.get(id=257),
         host = self.user,
         ekey = 'T1LZMJuD6PVPPjQsjv4r6Q==',
         secret = 'kYcQzhZU7rWVNTl49aTFjT2bDDOrZ/ATI+pBcc5h5PQfQi4cSf6rNDXlSGuaIEfdLKsYg6CjNtvugPm11NfuBg==',
         uid = '3cfb83c0-d98a-4ecc-ad06-3242c12bd070',
         # stuff from CGAM msg:
         slots = msg.map['MAX-PLAYERS'],
         #FIXME!!!!#info = dict((k, v) for k, v in msg.map.iteritems() if k.startswith('B-')),
         theater = self.theater,
         session = self,
      )

      return {
         'EKEY':game.ekey,# enter key? needed to join game? host checks it to verify you're not some random join?
         'GID':game.id,
         'J':0, #?
         'JOIN':0, #?
         'LID':game.list_id,
         'MAX-PLAYERS':game.slots,
         'SECRET':game.secret, # changes every time.
         'UGID':game.uid, # looks similar to windows class GUIDs??
      }

   def EnterGame(self, msg):
      if 'GID' in msg.map: # this means the client is hosting.
         # dict:GID=4280,LID=257,PORT=10000,PTYPE=P,R-INT-IP=192.168.0.81,R-INT-PORT=6001
         # these vals are provided by client, so response is easy
         game = self.theater.GetGame(game_id=int(msg.map['GID']))
      else: # game id needs to be looked up
         # dict:PORT=10000,PTYPE=P,R-INT-IP=192.168.0.81,R-INT-PORT=10000,R-U-USERID=914483734,R-USER=simonmc86,TID=6,TYPE=G,USER=simonmc86
         # (notice my ip and uid above, but somebody else's username...)
         # the client seems to just join games based on player name and lets the server look up the info.
         game = self.theater.GetGame(host=msg.map['USER'])

      # update session info
      self.__dict__.update(
         int_ip = msg.map['R-INT-IP'],         int_port = int(msg.map['R-INT-PORT']),
         ext_ip = msg.prot.transport.getPeer().host,
         ext_port = int(msg.map['PORT']),
      )
      self.save()

      # store this request
      rq = EnterGameRequest(
         game = game,
         slot = game.player_set.count() + 1,
         #rq.pid = min(rq.pid, 2) # HACK: PID can never exceed 2
         session = self, # the requester
      )
      rq.save()

      # simple reply that request is being handled
      return {
         'GID' : game.id,
         'LID' : game.list_id,
      }

   def HandleEnterGameResponse(self, msg):
      # dict:ALLOWED=1,GID=4280,LID=257,PID=1,TID=6
      self.Reply(msg, {}) # bounce TID only

      game = self.theater.GetGame(game_id=int(msg.map['GID']))
      pid = int(msg.map['PID']) # PID in the response is what slot joiner should occupy
      rq = game.entergamerequest_set.get(slot=pid)
      self.theater.PlayerJoinGame(rq.session, game_id=rq.game_id)
      Mercs2Theater.connections[rq.session_id].SendEnterGameEnterGame({ #HACK
         'LID':game.list_id,
         'GID':game.id,
         'UGID':game.uid, # Universal Game ID?
         'HUID':game.host_id, # Host User ID
         'I':game.session.ext_ip,
         'P':game.session.ext_port,
         'INT-IP':game.session.int_ip,
         'INT-PORT':game.session.int_port,
         'PL':'pc', # PLatform
         'PID':pid, # server is telling client his player id
         'EKEY':game.ekey, # some kinda session key?
         'TICKET': rq.id,
      })


@aspects.Aspect(Theater)
class _TheaterAspect(object):
   sessionClass = Mercs2Session
   connections = {} #HACKy way to access protocol objects via session id

mercs2theater = Theater.getTheater('mercs2')

class Mercs2LoginServer(EaServer):
   theater = mercs2theater
   # this class handles id, TXN, flags, theater.Session does the important parts of the msg.map
   def handleRequest(self, msg):
      replies = EaServer.handleRequest(self, msg)
      if replies != None:
         return replies

      reply = self.messageClass()
      reply.id = msg.id
      # This seems to always hold true. The last byte(s?) is the message sequence id.
      # If an error is returned, I've seen the values 'ntfn' and 'ferr' occupy the flags field
      # Client always sends c0 as first byte.
      reply.flags = 0x80000000 | (msg.flags & 0xFF) # how many bytes is sequence id??
      # This also seems always to be true:
      reply.map['TXN'] = msg.map['TXN']

      # append to this list if more than 1 message needs to be sent back
      replies = [reply]

      if msg.id == 'fsys':
         if msg.map['TXN'] == 'GetPingSites':
            # no inputs
            reply.map.update({
               'minPingSitesToPing':0,
               'pingSite':[
                  {'addr':'159.153.157.1', 'name':'eu-ip', 'type':0}, # europe
                  {'addr':'159.153.224.65', 'name':'ec-ip', 'type':0}, # east coast
                  {'addr':'159.153.193.193', 'name':'wc-ip', 'type':0}, # west coast
               ],
            })
         else:
            replies = None
      elif msg.id == 'acct':
         if msg.map['TXN'] == 'Login':
            self.session.HandleLogin(msg)
            replies = []
         elif msg.map['TXN'] == 'LookupUserInfo':
            # dict:userInfo.0.namespace=,userInfo.0.userId=930439156,userInfo.[]=1
            # HACK: assumes only 1 user in query
            user = User.GetUser(id=int(msg.map['userInfo'][0]['userId']))
            reply.map.update({'userInfo':[
               {
                  'userName':user.login,
                  'userId':user.id,
                  'namespace':'MAIN' #always
               },
            ]})
         else:
            replies = None
      elif msg.id == 'subs': # Mercs2 MOVEME?
         if msg.map['TXN'] == 'GetEntitlementByBundle':
            # dict:TXN=GetEntitlementByBundle,bundleId=REG-PC-MERCENARIES2-UNLOCK-1
            # this is the vacation skin pre-order bonus
            reply.map.update({
               'pricingOptionId':'REG-PC-MERCENARIES2-UNLOCK-1',
               'name':'"Mercenaries 2 UNLOCK 1 PC"',
               'description':'"Mercenaries 2 UNLOCK 1 PC"',
               'type':1,
               'entitlementStatus':0,
               'entitlementStatusDesc':'ACTIVE',
               'entitlementSuspendDate':'',
            })
            if False: # this is what's sent if not entitled
               reply.map.update({
                  'errorCode':3012,
                  'localizedMessage':'"The customer has never had entitlement for this bundle."',
                  'errorContainer':[],
               })
         else:
            replies = None
      if replies == None:
         self.factory.log.warning('request with id={0}, txn={1} unhandled!'.format(msg.id, msg.map['TXN']))
      return replies

class Mercs2Msg_Status(Message):
   def __init__(self, games):
      id = 605 #TODO, FIXME
      Message.__init__(self, 'pnow', 0x80000000, {
         'TXN':'Status',
         'id.id':id,
         'id.partition': msg.map['partition.partition'], # FIXME
         'sessionState':'COMPLETE',
         'props':toEAMapping({
            'availableServerCount':0,
            'games':[{'fit':0, 'gid':g.id, 'lid':g.lid} for g in games],
            'resultType':'LIST',
         })
      })


class Mercs2MsgHlr_Start(MessageHandler):
   def makeReply(self, msg):
      #  dict:TXN=Start,debugLevel=off,partition.partition=/eagames/MERCS2,players.0.ownerId=914483734,players.0.ownerType=1,players.0.props.{availableServerCount}=1,players.0.props.{filter-version}=mercs2-pc_ver_1555048492,players.0.props.{filterToGame-version}=version,players.0.props.{firewallType}=unknown,players.0.props.{maxListServersResult}=20,players.0.props.{name}=culley31,players.0.props.{poolMaxPlayers}=1,players.0.props.{poolTargetPlayers}=0:1,players.0.props.{poolTimeout}=30,players.0.props.{sessionType}=listServers,players.0.props.{}=10,players.[]=1,version=1
      id = 605 #TODO
      return msg.makeReply({
         'id.id':id, # ID for query, sent back in this & Status msg
         'id.partition':msg.map['partition.partition'],
      })

   def handle(self, msg):
      MessageHandler.Reply(self)

      games = mercs2theater.ListGames()
      Mercs2Msg_Status(games)
      # TODO: capture a log when hosting to double check for any special messages sent when that happens. joining should be covered adequately by the last logs i took.

class Mercs2MsgHlr_Hello(EaMsgHlr_Hello):
   def makeReply(self):
      reply = EaMsgHlr_Hello.makeReply(self)
      reply.map.update({
         'domainPartition.domain':'eagames',
         'domainPartition.subDomain':'MERCS2',
      })
      return reply

class Mercs2MsgHlr_Login(MessageHandler):
   def makeReply(self, msg):
      return msg.makeReply({
         'displayName': self.user.login,
         'userId': self.user.id,
         'profileId': self.user.id, # seems to be always the same as userId
         'lkey':self.key,
         'entitledGameFeatureWrappers':[{ #mercs 2 stuff
            'gameFeatureId':6014,
            'status':0,
            'message':'',
            'entitlementExpirationDate':'',
            'entitlementExpirationDays':-1,
         }],
      })
   def handle(self, msg):
      self.user = self.server.session.Login(msg.map['name'], msg.map['password'])
      if self.user:
         self.Reply(msg)
         d = EaCmd_Ping(self.server).getResponse()
         #TODO: replace with service
         #self.pingSvc.startService()
      else:
         # TODO send different reply here
         print 'TODO: user not found or bad pwd'

class Mercs2MsgHlr_CGAM(MessageHandler):
   '''Create GAMe'''
   def makeReply(self, msg):
      return msg.makeReply(self.info)
   def handle(self, msg):
      # B-U-AcceptType=2,B-U-Character=2,B-U-DlcMapId=0,B-U-Duration=0,B-U-FriendlyFire=0,B-U-IsDLC=0,B-U-Map=vz,B-U-Mission=,B-U-Money=0,B-U-Oil=0,B-U-UseVoice=0,B-maxObservers=0,B-numObservers=0,B-version=mercs2-pc_ver_1555048492,
      #DISABLE-AUTO-DEQUEUE=0,HTTYPE=A,HXFR=0,INT-IP=192.168.0.81,INT-PORT=10000,JOIN=O,LID=-1,
      #MAX-PLAYERS=2,NAME=hostname,PORT=10000,QLEN=0,RESERVE-HOST=1,
      # RT=,SECRET=,TID=4,TYPE=G,UGID=

      self.gameinfo = self.server.session.CreateGame(msg)
      self.Reply()

class Mercs2MsgHlr_EGAM(MessageHandler):
   '''Enter GAMe'''
   def makeReply(self, msg):
      return msg.makeReply(self.info)
   def handle(self, msg):
      self.info = self.server.session.EnterGame(msg)
      self.Reply()

      Mercs2Cmd_EGAM(self.server).send()

      # send the request msg to the host
      rDict = {
         'PTYPE':'P',
         'GID':game.id,
         'IP':rq.session.ext_ip,
         'PORT':rq.session.ext_port,
         'LID':game.list_id,
         'NAME':rq.session.user.login,
         'UID':rq.session.user_id,
         'PID':rq.slot,
         'R-INT-IP':rq.session.int_ip, # Requester's(?) INTernal IPaddress
         'R-INT-PORT':rq.session.int_port,
         'TICKET':rq.id, # i take ticket to mean request-id
      }
      # NOTE that the "R-" keys dont seem to be consistent
      # -- some are the requester's others are the host's...
      if game.host != rq.session.user:
         rDict.update({
            'R-USER':game.host.login,
            'R-U-USERID':rq.user.id, # dont make much sense :(
         })
      Mercs2Theater.connections[game.session_id].SendEnterGameRequest(rDict) #HACK


class Mercs2MsgHlr_GetRankedStats:
   def makeReply(self, msg):
      return msg.makeReply({
         #keys.0=vz,keys.[]=1,periodId=0,periodPast=0
         'stats' : [
            {
               'key':'vz',
               'rank':4390,
               'text':self.session.user.login,
               'value':'2.4562758E7',
            },
         ],
      })

class Mercs2TheaterServer(EaServer): #kinda a HACKy misnomer but quick way to inherit EaMessage usage
   theater = mercs2theater
   def Reply(self, msg, map):
      map = map.copy()
      map.update({'TID':msg.map['TID']})
      msg.flags = 0 # with mercs2, replies must all be 0! particularly CGAM
      EaServer.Reply(self, msg, map)

   def SendEnterGameRequest(self, map):
      self.SendMsg('EGRQ', 0, map)

   def SendEnterGameEnterGame(self, map):
      self.SendMsg('EGEG', 0, map)

   def handleRequest(self, msg):
      reply = self.messageClass()
      reply.id = msg.id
      # note: flags on client always seem to be 0x40000000
      # while those on server are 0x00000000
      reply.flags = 0
      # reply's TID is always present and matches request's
      reply.map['TID'] = msg.map['TID']

      # append to this list if more than 1 message needs to be sent back
      replies = [reply]

      if msg.id == 'CONN':
         # LOCALE=en_US,PLAT=PC,PROD=mercs2-pc,PROT=2,SDKVERSION=3.5.12.0.1,TID=1,VERS=1.0
         reply.map['TIME'] = int(time.time())
         reply.map['activityTimeoutSecs'] = 86400
         reply.map['PROT'] = 2 # no clue what this is
      elif msg.id == 'USER':
         # LKEY=SUeWiB3AH4p9LAXlCn4oOAAAKD0.,MAC=$7a790554222c,NAME=,SKU=15727
         self.session = self.theater.sessionClass.objects.get(key=msg.map['LKEY'])
         Mercs2Theater.connections[self.session.id] = self # HACK
         reply.map['NAME'] = self.session.user.login
      elif msg.id == 'LLST':
         # FAV-GAME-UID=,FAV-PLAYER-UID=,FILTER-FAV-ONLY=0,FILTER-MIN-SIZE=0,FILTER-NOT-CLOSED=0,FILTER-NOT-FULL=0,FILTER-NOT-PRIVATE=0,TID=3
         reply.map['NUM-LOBBIES'] = 1
         replies.append(self.messageClass('LDAT', 0, {
            'TID':msg.map['TID'],
            'FAVORITE-GAMES':0,
            'FAVORITE-PLAYERS':0,
            'LID':257, # Listing ID? The id for list of results (257 every time tho...)
            'LOCALE':'en_US',
            'MAX-GAMES':10000,
            'NAME':'mercs2PC01',
            'NUM-GAMES':7, # probably number of games available
            'PASSING':7, # probably number of games passing filters
         }))
      elif msg.id == 'GDAT': # Game DATa - queries can specify a GameID or USERname of friend
         # dict:TYPE=G,USER=elitak
         # ... or dict:GID=768,LID=257

         # return "none found" by returning nothing but TID:
         #reply.flags = 'ntfn' # this is interesting. 'not found' perhaps? leads me to believe that these 4 bytes arent strictly reserved for bitfields

         if 'GID' in msg.map:
            game = self.theater.GetGame(game_id=int(msg.map['GID']))
         elif 'USER' in msg.map:
            game = self.theater.GetGame(host=msg.map['USER'])

         # return search result:
         reply.map.update({
            'LID':game.lid,
            'GID':game.id,
            'TYPE':'G',

            'N':'hostname', # only literal value i've seen
            'I':game.ipEx[0],
            'P':game.ipEx[1],

            'PL':'PC', # PLatform?
            'V':'1.0',

            'HN':game.host.name, # Host's Name
            'HU':game.host.id, # Host User ID

            'J':'O',
            'JP':0, # joining players?
            'AP':len(game.players), # Active/Actual Players
            'MP':game.slots, # Maximum Players

            # ???
            'PW':0, # password?
            'QP':0,

            # NOTE: these are all in game.info now
            # and are here for documentiation purposes only.
            #'B-version':'mercs2-pc_ver_1555048492',
            #'B-numObservers':0,
            #'B-maxObservers':0,
            #'B-U-Character':1, # what character the host is playing 1=sweden, 2=usa, 3=china
            #'B-U-AcceptType':2, # what characters to accept? not used?
            #'B-U-FriendlyFire':0,
            #'B-U-IsDLC':0,
            #'B-U-UseVoice':0,
            #'B-U-Duration':2458, # time played. in seconds
            #'B-U-Map':'vz',
            #'B-U-DlcMapId':0,
            #'B-U-Mission':'PmcCon001',
            #'B-U-Money':181000, # amount of money currently held
            #'B-U-Oil':125, # amount of oil currently held
         })
         reply.map.update(game.info)
         replies.append(self.messageClass('GDET', 0, { #Game DET??
            'TID':msg.map['TID'],
            'LID':game.lid,
            'GID':game.id,
            'UGID':game.uid,
         }))

         # this may seem redundant but I think it's for games where
         # there can be more than 1 other player, hence the PID
         replies.append(self.messageClass('PDAT', 0, { #Player DATa
            'TID':msg.map['TID'],
            'GID':game.id,
            'LID':game.lid,
            'NAME':game.host.name,
            'UID':game.host.id,
            'PID':1, # HACK
         }))
      elif msg.id == 'CGAM':
         self.session.HandleCreateGame(msg)
         replies = []
      elif msg.id == 'EGAM': # Enter GAMe?
         # This is the game start notification sent to the server.
         self.session.HandleEnterGame(msg)
         replies = []
      elif msg.id == 'EGRS': # Enter Game ReSponse
         self.session.HandleEnterGameResponse(msg)
         replies = []
      elif msg.id == 'ECNL': # Enter CoNnection Lost?
         # sent when guest leaves host
         # 0x40000000 dict:GID=768,LID=257,TID=7
         reply.map['GID'] = msg.map['GID']
         reply.map['LID'] = msg.map['LID']
         self.theater.PlayerLeaveGame(self.session, int(msg.map['GID']))
      elif msg.id == 'PENT': # Player ENTered
         #  dict:GID=4280,LID=257,PID=1,TID=7
         # says to theater, I am player <PID> in game <GID>
         reply.map['PID'] = msg.map['PID']
      elif msg.id == 'PLVT': # PLayer ... ? (Vector?) Player LeaVe..?
         # never capped, seems to come after timing out connection attempt
         # right before ECNL
         reply = None #unhandled
      elif msg.id == 'UGAM': # UpdateGAMe?
         # dict:B-maxObservers=0,B-numObservers=0,GID=4280,JOIN=O,LID=257,MAX-PLAYERS=2,TID=8
         replies = [] # no response!? tends to have UBRA from client with same TID
      elif msg.id == 'UBRA': #Update BRA???
         # dict:GID=4280,LID=257,START=1,TID=8
         pass # just bounce the TID
      else:
         replies = None
      return replies

class Mercs2LoginFactory(ServerFactory):
   protocol = Mercs2LoginServer
   log = util.getLogger('fesl.mercs2')

class Mercs2TheaterFactory(ServerFactory):
   protocol = Mercs2TheaterServer
   log = util.getLogger('theater.mercs2')

class Service(MultiService):
   def __init__(self, **options):
      basePort = 18710
      MultiService.__init__(self)
      sCtx = OpenSSLContextFactoryFactory.getFactory('fesl.ea.com')
      sFact = Mercs2LoginFactory()
      #sFact = makeTLSFwdFactory('fesl.fwdCli', 'fesl.fwdSer')('mercs2-pc.fesl.ea.com', basePort)
      self.addService(SSLServer(basePort, sFact, sCtx))
      sFact = Mercs2TheaterFactory()
      #sFact = makeTCPFwdFactory('theater.fwdCli', 'theater.fwdSer')('mercs2-pc.theater.ea.com', basePort+5)
      self.addService(TCPServer(basePort+5, sFact))

