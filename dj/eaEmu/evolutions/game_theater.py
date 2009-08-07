from django_evolution.mutations import *
from django.db import models

MUTATIONS = [
    AddField('Game', 'theater', models.ForeignKey, initial=1, related_model='eaEmu.Theater')
    ]

