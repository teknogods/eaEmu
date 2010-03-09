import time

from twisted.application.internet import SSLServer, TCPServer
from twisted.application.service import MultiService
from twisted.internet.protocol import ServerFactory

from ea.db import *
from ea.login import *
#from util.fwdserver import *
import util

def fC(self, data):
   print repr(data)
   fwdDRC(self, data)

def fS(self, data):
   print repr(data)
   fwdDRS(self, data)

def getService(address):
   service = MultiService()
   return service

idNdx = 1

class Player:
   def __init__(self, info):
      self.info = dict((k, info[k]) for k in [
         'NAME',
         'USERFLAGS',
         'USERPARAMS',
      ])
      self.name = self.info['NAME']
      self.theater = burnoutTheater
      self.user = self.theater.GetUser(self.name)
   def GetInfo(self, index):
      info = {
         # player info
         'OPPO':self.user.name,
         'OPFLAG':self.info['USERFLAGS'],
         'OPPARAM':self.info['USERPARAMS'],

         'ADDR':self.user.addr,
         'LADDR':self.user.laddr,
         'MADDR':'', # okay if blank
         'OPID':self.user.id,

         # dunno if these ever change
         'PRES':0,
         'OPPART':0,
      }
      return dict((k+str(index), v) for k, v in info.iteritems())
class Game:
   def __init__(self, info):
      #copy these vals in
      self.info = dict((k, info[k]) for k in [
         'CUSTFLAGS',
         'MINSIZE',
         'MAXSIZE',
         'NAME', # name of game == name of creating player
         'PARAMS',
         'PRIV',
         'SEED', # should change after init
         'SYSFLAGS',
      ])

      # default vals
      self.info.update({
         'COUNT':0, #current player count, including invisible host
         'NUMPART':1, # NUMber of PARTies?
         'PARTSIZE0': self.info['MAXSIZE'], # dunno if this is equiv. to maxsize. PARTy SIZE?
         'GPSREGION':2,
         'GAMEPORT':9657,
         'VOIPPORT':9667,
         'EVGID':0,
         'EVID':0,
         'IDENT':6450,
         'GAMEMODE':0,
         'PARTPARAMS0':'',
         'ROOM':0,
         'WHEN':'2009.2.8-9:44:15',
         'WHENC':'2009.2.8-9:44:15',
         'GPSHOST':self.info['NAME'],
         'HOST':self.info['NAME'], #hosting player, normally botname
         # UH OHZ. is bot required for hosting???
         # worst case scenario: it is. solution: man-in-middle to play full verision as though it's trial version
         # is there even a difference??
      })

      self.players = []
      self.AddPlayer(Player(info))

   def AddPlayer(self, player):
      self.players.append(player)
      self.info['COUNT'] += 1

   def RemovePlayer(self, player):
      pass #TODO


class Burnout08Session(Session):
   def HandleGameJoin(self, msg):
         # CUSTFLAGS=413345024,FORCE_LEAVE=1,IDENT=6450,MAXSIZE=9,MINSIZE=2,NAME=bixop,PARAMS=,,,d800b85,,72755255,PASS=,PRIV=0,ROOM=0,SEED=9351261,
         # SESS=@brobot2583-bixop-498ea96f,SYSFLAGS=64,USERFLAGS=0,USERPARAMS=PUSMC01?????,,,ff1,,20004,,,3ed10a59

         # this response is similar to a game search result but with self included in clients
         # and a few more details:
         # LADDRs, MADDRs,

         game = self.theater.FindGame(msg.map['NAME'])
         self.Reply(msg, game.info)

         #might also need +who and +mgm before join from server -> cilent
         # also dunno if matchmaker makes request to host like in mercs

   def HandleFGet(self, msg):
      # TAG=F
      self.SendWho(self.user.name)
      self.theaterServ.SendMsg('+fup', 0, {
         'FLUP':0,
         'PRES':'',
      })
      self.Reply(msg)

   def SendWho(self, username):
      user = self.theater.GetUser(username)
      self.theaterServ.SendMsg('+who', 0, {
         'M':user.name,
         'N':user.name,
         'MA':'$7a790554222c',
         'A':user.addr,
         'LA':user.laddr,
         'P':1,
         'AT':'',
         'C':'4000,,7,1,1,,1,1,5553',
         'CL':511,
         'F':'U',
         'G':0,
         'HW':0,
         'I':71615,
         'LO':'enUS',
         'LV':1049601,
         'MD':0,
         'PRES':1,
         'RP':0,
         'S':'',
         'US':0,
         'VER':5,
         'X':'',
      })
   def SendMGM(self, game):
      self.theaterServ.SendMsg('+mgm', 0, game.info)

   def HandleGPSC(self, msg): #GPS Create?
      #  CUSTFLAGS=413345024,FORCE_LEAVE=1,MAXSIZE=9,MINSIZE=2,NAME=rtchd,PARAMS=,,,d800b85,,656e5553,PASS=,PRIV=0,
      # REGIONS=15,94,187,140,SEED=0,SYSFLAGS=64,USERFLAGS=0,USERPARAMS=PUSMC01?????,,,ff1,,20004,,,3ed10a59
      game = self.theater.CreateGame(msg.map)

      self.Reply(msg)
      self.SendWho(self.user.name)
      self.SendMGM(game)

   def Reply(self, msg, map=None):
      map = map or {}
      self.theaterServ.Reply(msg, map) #all go to theaterserv

   def HandleHCHK(self, msg):
      self.SendWho(self.user.name)
      self.Reply(msg)

   def HandleGameSearch(self, msg):
      if 'CANCEL' in msg.map:
         # client sends gsea CANCEL=1 to tell server to stop sending results
         self.Reply(msg)
      else:
         games = self.theater.GetGames()
         self.Reply(msg, {'COUNT': len(games)}) # number of results
         for game in games:
            self.SendGameSearchResult(game)

   def SendGameSearchResult(self, game):
      self.theaterServ.SendMsg('+gam', 0, game.info)

   def HandleAuth(self, msg):
      # BUILDDATE="Dec  3 2008",LOGD="LD=1,5<<a literal newline>>",MAC=$7a790554222c,NAME=tnhc,PASS=~Iii{4f|xq>a[zLz0Z%Rs9[He@ydyV,
      # SDKVERS=6.4.0.0,SKU=PC,SLUS=07604772/US,VERS=<<same bindata as before>>
      # TOKEN is used in lieu of NAME when "remember me" is enabled in-game
      # TOKEN is scrambled base64encoded data like in RA3

      # invalid login reply looks like this
      #'AUTOPASS':'SOCK67114', # dunno what this is for, only happens with failure
      #reply.flags = 0x70617373 # 'pass' signifies rejected login and has no body

      #HACK, FIXME: this info is gathered before login
      laddr = self.user.laddr
      addr = self.user.addr

      map = {}
      if 'NAME' in msg.map:
         self.user = self.theater.Login(msg.map['NAME'], msg.map['PASS'])
         map['TOKEN'] = 'pc6r0gHSgZXe1dgwo_CegjBCn24uzUC7KVq1LJDKJ0KQmCtria79vYw4pdPaTmjYbpFJIesipOa_TkGSIk48p-psfeqG6bhmE6cy-u24aB5noLCleNs4SfM0_HON3SXH5-7g3py94t0bIrtbP2klog..'
      elif 'TOKEN' in msg.map:
         global idNdx
         self.user = self.theater.Login('guest%d'%idNdx, msg.map['PASS'])
         idNdx += 1
         map['TOKEN'] = msg.map['TOKEN']

      self.user.laddr = laddr#HACK
      self.user.addr = addr#HACK

      map.update({
         'NAME':self.user.name,
         'MAIL':'user@domain.com',
         'PERSONAS':self.user.name,
         'BORN':'19840215', # birthdate with no separators
         'FROM':'US',
         'LOC':'enUS',
         'TOS':1, # agreed to Terms Of Service?
         'SPAM':'NN', # probably email notification checkboxes at signup. Y or N for each
         'SINCE':'2006.3.18-12:45:00', # when account was created? doesnt seem to be.
         'LAST':'2009.2.8-09:46:00', # last login time

         'ADDR':self.user.addr, # inform client of it's external address
         '_LUID':'$000000000b32588d',
      })
      self.Reply(msg, map)

class Burnout08Theater(Theater):
   sessionClass = Burnout08Session
   userClass = User

   #TODO: move up hierarchy
   def CreateGame(self, info):
      game = Game(info)
      self.games[info['NAME']] = game
      return game

   def GetGames(self):
      return self.games.values()

   def Login(self, name, pwd):
      return Theater.CreateUser(self, name, pwd)

burnoutTheater =  Burnout08Theater()
class Burnout08LoginServer(EaServer):
   theater = burnoutTheater

   def handleRequest(self, msg):
      reply = self.messageClass()
      reply.id = msg.id
      reply.flags = 0
      replies = [reply]

      if msg.id == '@tic':
         # input line : RC4+MD5-V2
         # no reply necessary
         replies = []
      elif msg.id == '@dir':
         #dict:BUILDDATE="Dec  3 2008",SDKVERS=6.4.0.0,SKU=PC,SLUS=07604772/US,VERS=<<binary data>>
         self.session = self.theater.Connect()
         self.session.key = self.transport.getPeer().host #HACK
         self.theater.ConnectionEstablished(self.session)
         reply.map.update({
            'ADDR':self.transport.getHost().host,
            'PORT':self.transport.getHost().port + 1,
            # TODO: figure out how the session keys match up across connections.
            # prly combines these 2 to make the key sent to theater serv
            'MASK':'b4c3cda8f20dbc748e8b357aa2c585c0',
            'SESS':self.session.key, # originally 'SESS':1233894580,
         })
      else:
         replies = None
      if replies == None:
         self.factory.log.warning('request with id={0} unhandled!'.format(msg.id))
      return replies

class Burnout08TheaterServer(EaServer):
   theater = burnoutTheater

   def handleRequest(self, msg):
      replies = FeslServer.handleRequest(self, msg)
      if replies != None:
         return replies
      reply = self.messageClass()
      reply.id = msg.id
      reply.flags = 0
      replies = [reply]

      if msg.id == 'addr':
         #dict:ADDR=5.84.34.44,PORT=49250
         # this is just local endpoint info
         self.tmpUserAddr = msg.map['ADDR'] #HACKy
         replies = []# no reply

         # month and day should be 1 digit but doesnt matter since it just gets bounced anyway
         replies.append(self.messageClass('~png', 0, {
            'REF':time.strftime('%Y.%m.%d-%H:%M:%S', time.gmtime())
         }))
      elif msg.id == 'skey':
         # dict:SKEY=$5075626c6963204b6579
         # this is probably derived from SESS in the other service
         self.session = self.theater.GetSession(self.transport.getPeer().host) #HACK
         self.session.theaterServ = self #HACK
         self.session.user.laddr = self.tmpUserAddr # HACKY
         self.session.user.addr = self.transport.getPeer().host
         reply.map.update({
            'DP':'PC/Burnout-2008/na1', #partition?
            'GFID':'"ODS:19038.110.Base Product;BURNOUT PARADISE ULTIMATE EDITION_PC_ONLINE_ACCESS"',
            'PLATFORM':'pc',
            'PSID':'PS-REG-BURNOUT2008',
            'SKEY':'$51ba8aee64ddfacae5baefa6bf61e009', # based on skey given?
         })
      elif msg.id == 'news':
         #dict:NAME=client.cfg
         if msg.flags == 0:
            reply.map.update({
               'PEERTIMEOUT':10000,
               'BUDDY_SERVER':'159.153.234.52',
               'BUDDY_PORT':13505,
               'GPS_REGIONS':'159.153.202.54,159.153.105.104,159.153.161.178,159.153.174.133',

               'EACONNECT_WEBOFFER_URL':'"http://gos.ea.com/easo/editorial/common/2008/eaconnect/connect.jsp?site=easo&lkey=$LKEY$&lang=%s&country=%s"',
               'TOSAC_URL':'"http://gos.ea.com/easo/editorial/common/2008/tos/tos.jsp?style=accept&lang=%s&platform=pc&from=%s"',
               'TOSA_URL':'"http://gos.ea.com/easo/editorial/common/2008/tos/tos.jsp?style=view&lang=%s&platform=pc&from=%s"',
               'TOS_URL':'"http://gos.ea.com/easo/editorial/common/2008/tos/tos.jsp?lang=%s&platform=pc&from=%s"',

               'USE_GLOBAL_ROAD_RULE_SCORES':0,
               'ROAD_RULES_RESET_DATE':'2007.10.11 18:00:00',
               'CAR_OLD_ROAD_RULES_TAGFIELD':'"RULES,RULES1,RULES2,RULES3,RULES4,RULES5,RULES6,RULES7,RULES8,RULES9,RULES10,RULES11,RULES12,RULES13,RULES14,RULES15,RULES16"',
               'CAR_ROAD_RULES_TAGFIELD':'"RULES17"',
               'BIKE_DAY_OLD_ROAD_RULES_TAGFIELD':'"BIKEDAYRULES1,BIKEDAYRULES2"',
               'BIKE_DAY_ROAD_RULES_TAGFIELD':'"BIKEDAYRULES3"',
               'BIKE_NIGHT_OLD_ROAD_RULES_TAGFIELD':'"BIKENIGHTRULES1,BIKENIGHTRULES2"',
               'BIKE_NIGHT_ROAD_RULES_TAGFIELD':'"BIKENIGHTRULES3"',
               'QOS_LOBBY':'159.153.105.1',
               'OS_PORT':17582,
               'ROAD_RULES_SKEY':'frscores',
               'PROFANE_STRING':'"@/&!"',
               'CHAL_SKEY':'chalscores',

               'FEVER_CARRIERS':'FritzBraun,EricWimp,Matazone,NutKC,FlufflesDaBunny,Flinnster,Molen,LingBot,DDangerous,Technocrat,The PLB,Chipper1977,Bazmobile,CustardKid,The Wibbler,AlexBowser,Blanks 82,Maxreboh,Jackhamma,MajorMajorMajor,Riskjockey,ChiefAV,Charnjit,Zietto,BurntOutDave,Belj,Cupster,Krisis1969,OrangeGopher,Phaigoman,Drastic Surgeon,Tom Underdown,Discodoktor,Cargando,Gaztech,PompeyPaul,TheSoldierBoy,louben17,Colonel Gambas,EliteBeatAgent,Uaintdown,SynergisticFX,InfamousGRouse,EAPR,EAPR 02,Jga360 JP2,EAJproduct',
               'TELE_DISABLE':'AD,AF,AG,AI,AL,AM,AN,AO,AQ,AR,AS,AW,AX,AZ,BA,BB,BD,BF,BH,BI,BJ,BM,BN,BO,BR,BS,BT,BV,BW,BY,BZ,CC,CD,CF,CG,CI,CK,CL,CM,CN,CO,CR,CU,CV,CX,DJ,DM,DO,DZ,EC,EG,EH,ER,ET,FJ,FK,FM,FO,GA,GD,GE,GF,GG,GH,GI,GL,GM,GN,GP,GQ,GS,GT,GU,GW,GY,HM,HN,HT,ID,IL,IM,IN,IO,IQ,IR,IS,JE,JM,JO,KE,KG,KH,KI,KM,KN,KP,KR,KW,KY,KZ,LA,LB,LC,LI,LK,LR,LS,LY,MA,MC,MD,ME,MG,MH,ML,MM,MN,MO,MP,MQ,MR,MS,MU,MV,MW,MY,MZ,NA,NC,NE,NF,NG,NI,NP,NR,NU,OM,PA,PE,PF,PG,PH,PK,PM,PN,PS,PW,PY,QA,RE,RS,RW,SA,SB,SC,SD,SG,SH,SJ,SL,SM,SN,SO,SR,ST,SV,SY,SZ,TC,TD,TF,TG,TH,TJ,TK,TL,TM,TN,TO,TT,TV,TZ,UA,UG,UM,UY,UZ,VA,VC,VE,VG,VN,VU,WF,WS,YE,YT,ZM,ZW,ZZ',

               'BUNDLE_PATH':'"https://gos.ea.com/easo/editorial/Burnout/2008/livedata/bundle/"',

               'NEWS_DATE':'2008.6.11 21:00:00',
               'NEWS_URL':'"http://gos.ea.com/easo/editorial/common/2008/news/news.jsp?lang=%s&from=%s&game=Burnout&platform=pc"',

               'AVAIL_DLC_URL':'"https://gos.ea.com/easo/editorial/Burnout/2008/livedata/Ents.txt" ',

               'AVATAR_URL':'"http://www.criteriongames.com/pcstore/avatar.php?persona=%s"',
               'AVATAR_URL_ENCRYPTED':1,

               'STORE_DLC_URL':'"http://pctrial.burnoutweb.ea.com/pcstore/store_dlc.php?lang=%s&from=%s&game=Burnout&platform=pc&env=live&nToken=%s&prodid=%s"',
               'STORE_URL':'"http://pctrial.burnoutweb.ea.com/t2b/page/index.php?lang=%s&from=%s&game=Burnout&platform=pc&env=live&nToken=%s"',
               'STORE_URL_ENCRYPTED':1,

               'ETOKEN_URL':'"https://gos.ea.com/easo/editorial/common/2008/nucleus/nkeyToNucleusEncryptedToken.jsp?nkey=%s&signature=%s"',
               'USE_ETOKEN':1,

               'LIVE_NEWS_URL':'"https://gos.ea.com/easo/editorial/Burnout/2008/livedata/main.jsp?lang=%s&from=%s&game=Burnout&platform=pc&env=live&nToken=%s"',
               'LIVE_NEWS2_URL':'"http://portal.burnoutweb.ea.com/loading.php?lang=%s&from=%s&game=Burnout&platform=pc&env=live&nToken=%s"',

               'PRODUCT_DETAILS_URL':'"http://pctrial.burnoutweb.ea.com/t2b/page/ofb_pricepoints.php?productID=%s&env=live"',
               'PRODUCT_SEARCH_URL':'"http://pctrial.burnoutweb.ea.com/t2b/page/ofb_DLCSearch.php?env=live"',
            })
         #elif msg.flags == 'new8':
         else:
            replies = None
      elif msg.id == '~png':
         #  dict:REF=2009.2.7-11:34:06,TIME=1
         replies = []
      elif msg.id == 'sele':
         # dict:MYGAME=1 GAMES=0 ROOMS=0 USERS=1 MESGS=1 MESGTYPES=100728964 STATS=500 RANKS=1 USERSETS=1
         reply.map.update({
            'DP':'PC/Burnout-2008/na1', #partition id?
            'ASYNC':0,
            'CTRL':0,
            'GAMES':0,
            'GFID':'"ODS:19038.110.Base Product;BURNOUT PARADISE ULTIMATE EDITION_PC_ONLINE_ACCESS"',
            'INGAME':0,
            'MESGS':0,
            'MESGTYPES':'',
            'MYGAME':1,
            'PLATFORM':'pc',
            'PSID':'PS-REG-BURNOUT2008',
            'ROOMS':0,
            'SLOTS':280,
            'STATS':0,
            'USERS':0,
            'USERSETS':0,
         })
      elif msg.id == 'auth':
         self.session.HandleAuth(msg)
         replies = []
      elif msg.id == 'pers': # get PERSona info
         # CDEV=,LOGD="LD=1,5\n",MAC=$7a790554222c,PERS=rtchd
         reply.map.update({
            'A':'24.7.121.79', # detected external address
            'EX-telemetry':'159.153.244.82,9983,enUS,^\xf1\xfe\xf6\xd0\xcd\xc5\xcb\x9f\xb5\xa8\xf2\xa8\xa0\xe3\xa8\xa0\x98\xa0\xcb\xa3\xb7\x8c\x9a\xb2\xac\xc8\xdc\x89\xf6\xa6\x8e\x98\xb5\xea\xd0\x91\xa3\xc6\xcc\xb1\xac\xc8\xc0\x81\x83\x86\x8c\x98\xb0\xe0\xc0\x81\xa3\xec\x8c\x99\xb5\xf0\xe0\xa1\xc6\x85\xd4\xa1\xaf\x84\xd5\x93\xe7\xed\xdb\xba\xf4\xda\xc8\x81\x83\x86\xce\x97\xee\xc2\xc5\xe1\x92\xc6\xcc\x99\xb4\xe0\xe0\xb1\xc3\xa6\xce\x98\xac\xca\xb9\xab\xb5\x8a\x80',
            'IDLE':50000,
            'LA':'5.84.34.44', # Last Address
            'LAST':'2009.2.8-09:46:37', # Last login time
            'LKEY':'SX74lCZjaiaR2COKCn4p3AAAKG4.',
            'LOC':'enUS',
            'MA': msg.map['MAC'],
            'NAME':msg.map['PERS'],
            'PERS':msg.map['PERS'],
            'PLAST':'2009.2.8-09:46:00',
            'PSINCE':'2009.2.8-09:41:00',
            'SINCE':'2009.2.8-09:41:00',
         })
      elif msg.id == 'fget':
         self.session.HandleFGet(msg)
         replies = []
      elif msg.id == 'usld':
         # no inputs
         reply.map.update({
            'IMGATE':0,
            'QMSG0':'"Wanna play?"',
            'QMSG1':'"I rule!"',
            'QMSG2':'Doh!',
            'QMSG3':'"Mmmm... doughnuts."',
            'QMSG4':'"What time is it?"',
            'QMSG5':'"The truth is out of style."',
            'SPM_EA':0,
            'SPM_PART':0,
            'UID':'$000000000b32588d',
         })
      elif msg.id == 'slst':
         # LOC=enUS
         reply.map.update({
            'COUNT':27,
            'VIEW0':'lobby,"Online Lobby Stats View",',
            'VIEW1':'DLC,"DLC Lobby Stats View",',
            'VIEW2':'RoadRules,"Road Rules",',
            'VIEW3':'DayBikeRRs,"Day Bike Road Rules",',
            'VIEW4':'NightBikeRR,"Night Bike Road Rules",',
            'VIEW5':'PlayerStatS,"Player Stats Summary",',
            'VIEW6':'LastEvent1,"Recent Event 1 Details",',
            'VIEW7':'LastEvent2,"Recent Event 2 Details",',
            'VIEW8':'LastEvent3,"Recent Event 3 Details",',
            'VIEW9':'LastEvent4,"Recent Event 4 Details",',
            'VIEW10':'LastEvent5,"Recent Event 5 Details",',
            'VIEW11':'OfflineProg,"Offline Progression",',
            'VIEW12':'Rival1,"Rival 1 information",',
            'VIEW13':'Rival2,"Rival 2 information",',
            'VIEW14':'Rival3,"Rival 3 information",',
            'VIEW15':'Rival4,"Rival 4 information",',
            'VIEW16':'Rival5,"Rival 5 information",',
            'VIEW17':'Rival6,"Rival 6 information",',
            'VIEW18':'Rival7,"Rival 7 information",',
            'VIEW19':'Rival8,"Rival 8 information",',
            'VIEW20':'Rival9,"Rival 9 information",',
            'VIEW21':'Rival10,"Rival 10 information",',
            'VIEW22':'DriverDetai,"Driver details",',
            'VIEW23':'RiderDetail,"Rider details",',
            'VIEW24':'IsldDetails,"Island details",',
            'VIEW25':'Friends,"Friends List",',
            'VIEW26':'PNetworkSta,"Paradise Network Stats",',
         })
      elif msg.id == 'gqwk':
         # FORCE_LEAVE=1,GPS=1,GS0=0,GS1=0,GS2=2,GS3=1,GS4=5,GS5=0,USERFLAGS=0,USERPARAMS=PUSMC01?????,,,ff1,,20004,,,3ed10a59
         replies = []
         # TODO: this is supposed to quickmatch a game, i never capped the result of this...
      elif msg.id == 'sviw': #Stats VIeW?
         # VIEW=DLC
         reply.map.update({
            'N':9, # count of CSVs that follow
            'DESCS':'1,1,1,1,1,1,1,1,1',
            'NAMES':'0,3,4,5,6,7,8,9,10',
            'PARAMS':'2,2,2,2,2,2,2,2,2',
            'SYMS':'TOTCOM,a,0,TAKEDNS,RIVALS,ACHIEV,FBCHAL,RANK,WINS,SNTTEAM,SNTFFA',
            'TYPES':'~num,~num,~num,~num,~num,~rnk,~num,~pts,~pts',
            'SS':'65',
         })
      elif msg.id == 'sdta': # Stats DATa?
         # PERS=rtchd,SLOT=0,VIEW=DLC
         reply.map.update({
            'SLOT':0,
            'STATS':'0,0,0,0,0,0,0,0,0',
         })
      elif msg.id == 'gpsc': # GPS Create?
         self.session.HandleGPSC(msg)
         replies = []
      elif msg.id == 'hchk':
         # no inputs. triggers a +who as well as empty response
         self.session.HandleHCHK(msg)
         replies = []
      elif msg.id == 'gsea': # Game SEArch
         # ASYNC=1,COUNT=100,CUSTFLAGS=0,CUSTMASK=0,CUSTOM=,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,4,2,,,1,2,801,,5,,1,PLAYERS=1,START=0,SYSFLAGS=0,SYSMASK=262144
         self.session.HandleGameSearch(msg)
         replies = []
      elif msg.id == 'gjoi': # Game JOIn
         self.session.HandleGameJoin(msg)
         replies = []
      elif msg.id == 'glea': # Game LEAve
         # FORCE=1 SET=0

         #server sends back all the game info again...
         # ADDR0=159.153.161.174,ADDR1=95.72.167.223,COUNT=2,CUSTFLAGS=413345024,EVGID=0,EVID=0,GAMEMODE=0,GAMEPORT=9657,GPSHOST=bixop,GPSREGION=2,HOST=@brobot2583,IDENT=6450,LADDR0=10.161.162.89,LADDR1=192.168.1.5,MADDR0=,MADDR1=$001fc61bc95c,MAXSIZE=9,MINSIZE=2,NAME=bixop,NUMPART=1,OPFLAG0=0,OPFLAG1=413345024,OPID0=650,OPID1=71666,OPPART0=0,OPPART1=0,OPPO0=@brobot2583,OPPO1=bixop,PARAMS=",,,d800b85,,72755255",PARTSIZE0=9,PRES0=0,PRES1=0,PRIV=0,ROOM=0,SEED=9351261,SYSFLAGS=64,VOIPPORT=9667,WHEN=2009.2.8-9:44:15,WHENC=2009.2.8-9:44:15
         pass #TODO
      elif msg.id == 'fupr': # comes after a game join
         # JOIN=1 PRES=1
         pass # just bounce
      elif msg.id == 'rvup': # RiVal UPdate
         # {'RIVAL0': ',,,,,,,,,,,,bixop'}
         # TODO: never capped this
         pass

      else:
         replies = None
      if replies == None:
         self.factory.log.warning('request with id={0} unhandled!'.format(msg.id))
      return replies

class Burnout08LoginServerFactory(ServerFactory):
   protocol = Burnout08LoginServer
   log = util.getLogger('fesl.burnout08', self)

class Burnout08TheaterServerFactory(ServerFactory):
   protocol = Burnout08TheaterServer
   log = util.getLogger('theater.burnout08', self)

class Burnout08Service(MultiService):
   def __init__(self, addresses=None):
      MultiService.__init__(self)

      ctx = OpenSSLContextFactoryFactory.getFactory('fesl.ea.com')
      fact = Burnout08LoginServerFactory()
      #fact = makeTLSFwdFactory('fesl.fwdCli', 'fesl.fwdSer', fC, fS)(*address)
      self.addService(SSLServer(addresses[0][1], fact, ctx))

      fact = Burnout08TheaterServerFactory()
      #fact = makeTCPFwdFactory('theater.fwdCli', 'theater.fwdSer', fwdDRC, fwdDRS)(address[0], address[1]+1)
      self.addService(TCPServer(addresses[0][1]+1, fact))
