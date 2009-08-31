from django.db import models

class Game(models.Model) :
    name = models.CharField(max_length=16, unique=True )
    key = models.CharField(max_length=6, null=True )
    description = models.CharField(max_length=100, null=True )

    def __unicode__(self):
        return u""


class User(models.Model) :
    login = models.CharField(max_length=32)
    firstName = models.CharField(max_length=32, blank=True )
    lastName = models.CharField(max_length=32, blank=True )
    password = models.CharField(max_length=32)
    created = models.DateTimeField(auto_now_add=True)
    lastLogin = models.DateTimeField(null=True)
    email = models.CharField(max_length=32)

    def __unicode__(self):
        return u""


class Channel(models.Model) :
    name = models.CharField(max_length=32)
    prettyName = models.CharField(max_length=32)
    game = models.ForeignKey(Game)
    flags = models.CharField(max_length=16, blank=True )
    topic = models.CharField(max_length=256, null=True )
    users = models.ManyToManyField(User)

    def __unicode__(self):
        return u""


class Theater(models.Model) :
    name = models.CharField(max_length=32)

    def __unicode__(self):
        return u""


class MasterGameSession(models.Model) :
    channel = models.ForeignKey(Channel)
    hostname = models.CharField(max_length=30, blank=True, default='' )
    gamemode = models.CharField(max_length=20, blank=True, default='' )
    mapname = models.CharField(max_length=200, blank=True, default='' )
    vCRC = models.CharField(max_length=50, blank=True, default='' )
    iCRC = models.CharField(max_length=50, blank=True, default='' )
    cCRC = models.CharField(max_length=50, blank=True, default='' )
    joinable = models.IntegerField(default=0)
    localip0 = models.CharField(max_length=15, blank=True, default='0.0.0.0' )
    localip1 = models.CharField(max_length=15, blank=True, default='0.0.0.0' )
    localip2 = models.CharField(max_length=15, blank=True, default='0.0.0.0' )
    localip3 = models.CharField(max_length=15, blank=True, default='0.0.0.0' )
    localport = models.IntegerField(default=0)
    obs = models.IntegerField(default=0)
    numRPlyr = models.IntegerField(default=0)
    numplayers = models.IntegerField(default=0)
    maxRPlyr = models.IntegerField(default=0)
    maxplayers = models.IntegerField(default=0)
    numObs = models.IntegerField(default=0)
    mID = models.CharField(max_length=50, default='#' )
    mod = models.CharField(max_length=50, blank=True, default='' )
    modv = models.CharField(max_length=50, blank=True, default='' )
    name = models.CharField(max_length=50, default='#' )
    pings = models.CharField(max_length=50, default='#' )
    publicip = models.IntegerField(default=0)
    publicport = models.IntegerField(default=0)
    pw = models.IntegerField(default=0)
    teamAuto = models.CharField(max_length=50, blank=True, default='' )
    natneg = models.IntegerField(default=0)
    statechanged = models.IntegerField(default=0)
    rules = models.CharField(max_length=50, blank=True, default='' )

    def __unicode__(self):
        return u""


class GameLobby(models.Model) :
    channel = models.OneToOneField(Channel)
    PN = models.CharField(max_length=200, null=True )
    SL = models.CharField(max_length=500, null=True )
    Pings = models.CharField(max_length=100, null=True )
    PIDS = models.CharField(max_length=100, null=True )

    def __unicode__(self):
        return u""


class ArenaTeam(models.Model) :

    def __unicode__(self):
        return u""


class GameList(models.Model) :

    def __unicode__(self):
        return u""


class LoginSession(models.Model) :
    user = models.OneToOneField(User,null=True)
    theater = models.ForeignKey(Theater)
    created = models.DateTimeField(auto_now_add=True)
    key = models.CharField(max_length=32)
    intIp = models.CharField(max_length=15)
    intPort = models.IntegerField()
    extIp = models.CharField(max_length=15)
    extPort = models.IntegerField()

    def __unicode__(self):
        return u""


class CdKey(models.Model) :
    game = models.ForeignKey(Game)
    user = models.ForeignKey(User)
    cdKey = models.CharField(max_length=32)

    def __unicode__(self):
        return u""


class GameSession(models.Model) :
    host = models.OneToOneField(User)
    created = models.DateTimeField()
    list = models.ForeignKey(GameList)
    ekey = models.CharField(max_length=32)
    secret = models.CharField(max_length=256)
    uid = models.CharField(max_length=256)
    slots = models.IntegerField()
    theater = models.ForeignKey(Theater)
    info = models.CharField(max_length=2048, blank=True )
    session = models.ForeignKey(LoginSession)

    def __unicode__(self):
        return u""


class EnterGameRequest(models.Model) :
    game = models.ForeignKey(GameSession)
    slot = models.IntegerField()
    session = models.ForeignKey(LoginSession)

    def __unicode__(self):
        return u""


class Player(models.Model) :
    user = models.ForeignKey(User)
    game = models.ForeignKey(GameSession)

    def __unicode__(self):
        return u""


class Persona(models.Model) :
    user = models.ForeignKey(User)
    name = models.CharField(max_length=32)
    selected = models.BooleanField(default=False)
    friends = models.ManyToManyField('self')

    def __unicode__(self):
        return u""


class Stats(models.Model) :
    persona = models.OneToOneField(Persona)
    game = models.ForeignKey(Game)
    b_flags = models.CharField(max_length=32, blank=True, default='' )
    b_clanName = models.CharField(max_length=64, blank=True, default='' )
    b_arenaTeamID = models.ForeignKey(ArenaTeam,default=0)
    b_locale = models.IntegerField(default=0)
    b_wins = models.IntegerField(default=0)
    b_losses = models.IntegerField(default=0)
    b_rank1v1 = models.IntegerField(default=-1)
    b_rank2v2 = models.IntegerField(default=-1)
    b_clan1v1 = models.IntegerField(default=-1)
    b_clan2v2 = models.IntegerField(default=-1)
    b_elo1v1 = models.IntegerField(default=-1)
    b_elo2v2 = models.IntegerField(default=-1)
    b_onlineRank = models.IntegerField(default=1)

    def __unicode__(self):
        return u""

