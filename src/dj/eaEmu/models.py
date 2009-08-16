from django.db import models

class Game(models.Model) :
    name = models.CharField(max_length=16)
    key = models.CharField(max_length=6)

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


class ArenaTeam(models.Model) :

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
    flags = models.CharField(max_length=16, blank=True )
    topic = models.CharField(max_length=256, null=True )
    users = models.ManyToManyField(User)

    def __unicode__(self):
        return u""


class ClientKey(models.Model) :
    b_flags = models.CharField(max_length=32)
    b_clanName = models.CharField(max_length=64)
    b_arenaTeamID = models.ForeignKey(ArenaTeam)
    b_locale = models.IntegerField()
    b_wins = models.IntegerField()
    b_losses = models.IntegerField()
    b_rank1v1 = models.IntegerField()
    b_rank2v2 = models.IntegerField()
    b_clan1v1 = models.IntegerField()
    b_clan2v2 = models.IntegerField()
    b_elo1v1 = models.IntegerField()
    b_elo2v2 = models.IntegerField()
    b_onlineRank = models.IntegerField()

    def __unicode__(self):
        return u""


class GameList(models.Model) :

    def __unicode__(self):
        return u""


class LoginSession(models.Model) :
    user = models.OneToOneField(User)
    theater = models.ForeignKey(Theater)
    created = models.DateTimeField(auto_now_add=True)
    key = models.CharField(max_length=32)
    intIp = models.CharField(max_length=15)
    intPort = models.IntegerField()
    extIp = models.CharField(max_length=15)
    extPort = models.IntegerField()

    def __unicode__(self):
        return u""


class Profile(models.Model) :

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
    selected = models.BooleanField()

    def __unicode__(self):
        return u""


class IrcUser(models.Model) :
    user = models.OneToOneField(User)
    clientKey = models.OneToOneField(ClientKey)
    profile = models.ForeignKey(Profile)
    encIp = models.CharField(max_length=10)

    def __unicode__(self):
        return u""

