#----- Evolution for eaEmu
from django_evolution.mutations import *
from django.db import models

MUTATIONS = [
#AddField('Game', 'session', models.ForeignKey, initial=1, related_model='eaEmu.Session'),
    DeleteField('Game', 'ext_port'),
    DeleteField('Game', 'int_ip'),
    DeleteField('Game', 'ext_ip'),
    DeleteField('Game', 'int_port'),
#AddField('Session', 'int_ip', models.CharField, initial='0.0.0.0', max_length=15),
#AddField('Session', 'ext_ip', models.CharField, initial='0.0.0.0', max_length=15),
#AddField('Session', 'ext_port', models.IntegerField, initial=0),
#AddField('Session', 'int_port', models.IntegerField, initial=0)
]
#----------------------
