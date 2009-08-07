from django_evolution.mutations import *
from django.db import models

MUTATIONS = [
    AddField('Channel', 'prettyName', models.CharField, initial='bleh', max_length=32)
    ]

