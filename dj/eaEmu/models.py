from django.db import models

class User(models.Model):
   login = models.CharField(max_length=32)
   first_name = models.CharField(max_length=32, null=True)
   last_name = models.CharField(max_length=32, null=True)
   password = models.CharField(max_length=32)
   created = models.DateField(auto_now_add=True)
   last_login =  models.DateField(null=True)

class Theater(models.Model):
   name = models.CharField(max_length=32)

class Session(models.Model):
   user = models.ForeignKey(User, null=True)
   theater = models.ForeignKey(Theater)
   created = models.DateField(auto_now_add=True)
   key = models.CharField(max_length=32)
   int_ip = models.CharField(max_length=15)
   int_port = models.IntegerField()
   ext_ip = models.CharField(max_length=15)
   ext_port = models.IntegerField()
   
class GameList(models.Model):
   pass

class Game(models.Model):
   host = models.ForeignKey(User)
   created = models.DateField(auto_now_add=True)
   list = models.ForeignKey(GameList)
   ekey = models.CharField(max_length=32)
   secret = models.CharField(max_length=256)
   uid = models.CharField(max_length=256)
   slots = models.IntegerField()
   theater = models.ForeignKey(Theater)
   info = models.CharField(max_length=2048, blank=True)
   session = models.ForeignKey(Session)

class Player(models.Model):
   user = models.ForeignKey(User)
   game = models.ForeignKey(Game)

class EnterGameRequest(models.Model):
   game = models.ForeignKey(Game)
   slot = models.IntegerField()
   session = models.ForeignKey(Session)

   
   
# Gamespy stuff
class GamespyGame(models.Model):
   name = models.CharField(max_length=16)
   key = models.CharField(max_length=6)
   
class Channel(models.Model):
   name = models.CharField(max_length=32)
   prettyName = models.CharField(max_length=32)
   game = models.ForeignKey(GamespyGame)
   flags = models.CharField(max_length=16, blank=True)
   topic = models.CharField(max_length=32, null=True)