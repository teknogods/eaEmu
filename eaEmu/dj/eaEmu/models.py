from django.db import models


class Game(models.Model) :
    name = models.CharField(max_length=16, unique=True )
    key = models.CharField(max_length=6, null=True )
    description = models.CharField(max_length=100, null=True )

    def __unicode__(self):
        return u""


class User(models.Model) :
    phpbb_id = models.IntegerField(null=True, unique=True)
    login = models.CharField(max_length=32, unique=True )
    password = models.CharField(max_length=34)
    created = models.DateTimeField(auto_now_add=True)
    lastLogin = models.DateTimeField(null=True)
    email = models.CharField(max_length=32, null=True, unique=True )
    active = models.BooleanField(default=True)
    notes = models.CharField(max_length=200, null=True )

    def __unicode__(self):
        return u""


class Theater(models.Model) :
    name = models.CharField(max_length=32)

    def __unicode__(self):
        return u""


class Channel(models.Model) :
    name = models.CharField(max_length=32)
    prettyName = models.CharField(max_length=32)
    game = models.ForeignKey(Game)
    mode = models.CharField(max_length=16, default='+tlp' )
    topic = models.CharField(max_length=256, null=True )
    users = models.ManyToManyField(User)

    def __unicode__(self):
        return u""


class MasterGameSession(models.Model) :
    clientId = models.DecimalField(max_digits=10, decimal_places=0, unique=True)
    channel = models.ForeignKey(Channel)
    updated = models.DateTimeField(auto_now=True)
    hostname = models.CharField(max_length=30, blank=True, default='' )
    gamemode = models.CharField(max_length=20, blank=True, default='' )
    mapname = models.CharField(max_length=200, blank=True, default='' )
    vCRC = models.CharField(max_length=50, blank=True, default='' )
    iCRC = models.CharField(max_length=50, blank=True, default='' )
    cCRC = models.CharField(max_length=50, blank=True, default='' )
    joinable = models.IntegerField(default=0)
    localip0 = models.IPAddressField(default='0.0.0.0')
    localip1 = models.IPAddressField(default='0.0.0.0')
    localip2 = models.IPAddressField(default='0.0.0.0')
    localip3 = models.IPAddressField(default='0.0.0.0')
    localport = models.IntegerField(default=0)
    obs = models.IntegerField(default=0)
    numRPlyr = models.IntegerField(default=0)
    numplayers = models.IntegerField(default=0)
    maxRPlyr = models.IntegerField(default=0)
    maxplayers = models.IntegerField(default=0)
    numObs = models.IntegerField(default=0)
    mID = models.CharField(max_length=50, blank=True, default='' )
    mod = models.CharField(max_length=50, blank=True, default='' )
    modv = models.CharField(max_length=50, blank=True, default='' )
    name = models.CharField(max_length=50, blank=True, default='' )
    pings = models.CharField(max_length=50, blank=True, default='' )
    publicip = models.IPAddressField(default='0.0.0.0')
    publicport = models.IntegerField(default=0)
    pw = models.IntegerField(default=0)
    teamAuto = models.CharField(max_length=50, blank=True, default='0' )
    natneg = models.IntegerField(default=0)
    statechanged = models.IntegerField(default=0)
    rules = models.CharField(max_length=50, blank=True, default='' )

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


class UserIrcInfo(models.Model) :
    user = models.ForeignKey(User)
    channel = models.ForeignKey(Channel,null=True)
    mode = models.CharField(max_length=50, default='' )

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
    name = models.CharField(max_length=32, unique=True )
    selected = models.BooleanField(default=False)
    friends = models.ManyToManyField('self')

    def __unicode__(self):
        return u""


class Stats(models.Model) :
    channel = models.ForeignKey(Channel)
    persona = models.ForeignKey(Persona)
    b_flags = models.CharField(max_length=32, null=True )
    b_clanName = models.CharField(max_length=64, null=True )
    b_arenaTeamID = models.ForeignKey(ArenaTeam,null=True)
    b_locale = models.IntegerField(null=True)
    b_wins = models.IntegerField(null=True)
    b_losses = models.IntegerField(null=True)
    b_rank1v1 = models.IntegerField(null=True)
    b_rank2v2 = models.IntegerField(null=True)
    b_clan1v1 = models.IntegerField(null=True)
    b_clan2v2 = models.IntegerField(null=True)
    b_elo1v1 = models.IntegerField(null=True)
    b_elo2v2 = models.IntegerField(null=True)
    b_onlineRank = models.IntegerField(null=True)

    def __unicode__(self):
        return u""

