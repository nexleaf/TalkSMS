#!/usr/bin/env python

import django
from django.db import models
from django.contrib.auth.models import User
from django.db.models import *

# needed to link Tasks to Templates
import dbtemplates.models

from datetime import datetime
from pytz import timezone
import os, json


##########################
# Custom models for Tasks
##########################


# TODO: Want to add this file to the migrations eventually
# but will pass for now since all very simple storage.
# Commands would be:
#  ./manage.py schemamigration taskmanager.tasks --initial
#  ./manage.py migrate taskmanager.tasks
#  ... might not need the 'taskmanager.' part
#


##########################
# Mediabus

class MediaBusRawLog(models.Model):
    identity = models.CharField(max_length=256)
    message_datetime = models.DateTimeField(auto_now_add=True)
    message_number = models.IntegerField()
    message_text = models.CharField(max_length=256)
    
    class Meta:
        ordering = ['-message_datetime']

##########################
