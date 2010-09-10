#!/usr/bin/env python

import django
from django.db import models
from django.contrib.auth.models import User
from django.db.models import *

# needed to link Tasks to Templates
import dbtemplates.models

from datetime import datetime
from pytz import timezone
import os

# =================================================================
# ==== Users
# =================================================================

class Patient(models.Model):
    address = models.CharField(max_length=200)
    first_name = models.CharField(max_length=80)
    last_name = models.CharField(max_length=80)

    def __unicode__(self):
        return "%s, %s (%s)" % (self.last_name, self.first_name, self.address)

class Clinician(models.Model):
    # links the Clinician object to a User object for authentication purposes
    user = models.ForeignKey(User, unique=True)
    
    def __unicode__(self):
        return "%s" % (self.user)
    
# signal handler to associate users with clinician objects
from django.db.models.signals import post_save

def user_save_handler(sender, **kwargs):
    if 'created' in kwargs and kwargs['created']:
        clinician = Clinician(user=kwargs['instance'])
        clinician.save()

post_save.connect(user_save_handler, sender=User)


# =================================================================
# ==== Task Descriptions
# =================================================================

class Task(models.Model):
    name = models.CharField(max_length=100)
    module = models.CharField(max_length=100)
    className = models.CharField(max_length=100)
    schedulable = models.BooleanField(blank=True,default=False)

    # maintains the templates used by this task
    templates = models.ManyToManyField(dbtemplates.models.Template)

    def __unicode__(self):
        return "%s (%s.%s)" % (self.name, self.module, self.className)

class TaskTemplate(models.Model):
    name = models.CharField(max_length=100)
    task = models.ForeignKey(Task)
    arguments = models.TextField(blank=True)

    def __unicode__(self):
        return "%s" % (self.name)

# =================================================================
# ==== Processes (Scheduled Task + Session Group)
# =================================================================

class ProcessManager(models.Manager):
    def get_pending_processes(self):
        # a pending process has only incomplete scheduled tasks
        qset = super(ProcessManager, self).get_query_set()
        return qset.exclude(scheduledtask__completed=True)
    
    def get_current_processes(self):
        # a current process has at least one incomplete session or scheduled task
        qset = super(ProcessManager, self).get_query_set()
        return qset.filter(Q(session__completed=False)|Q(scheduledtask__completed=False,session__completed=True)).distinct()

    def get_completed_processes(self):
        # a completed process has only complete scheduled tasks and sessions
        qset = super(ProcessManager, self).get_query_set()
        return qset.exclude(scheduledtask__completed=False).exclude(session__completed=False)
    
class Process(models.Model):
    name = models.CharField(max_length=100)
    patient = models.ForeignKey(Patient)
    creator = models.ForeignKey(Clinician, blank=True, null=True)
    add_date = models.DateTimeField(auto_now_add=True)

    objects = ProcessManager()

    def get_tasks(self):
        return self.scheduledtask_set.all()

    def get_sessions(self):
        return self.session_set.all()

    def get_pending_tasks(self):
        # a current process has at least one incomplete session
        return self.scheduledtask_set.filter(completed=False)
    
    def get_current_sessions(self):
        # a current process has at least one incomplete session
        return self.session_set.filter(completed=False)

    def get_completed_sessions(self):
        # a current process has at least one incomplete session
        return self.session_set.filter(completed=True)

    def get_status(self):
        pending_cnt = self.get_pending_tasks().count()
        current_cnt = self.get_current_sessions().count()
        completed_cnt = self.get_completed_sessions().count()
        
        if pending_cnt > 0 and current_cnt <= 0 and completed_cnt <= 0: return "pending"
        elif (current_cnt) > 0 or (pending_cnt > 0 and completed_cnt > 0): return "running"
        elif pending_cnt <= 0 and current_cnt <= 0 and completed_cnt > 0: return "past"
        else: return "unknown"

    def __unicode__(self):
        return "%s (#%d)" % (self.name, self.id)

# =================================================================
# ==== Sessions and Logging/Data Collection
# =================================================================

class SessionManager(models.Manager):
    def get_current_sessions(self):
        qset = super(SessionManager, self).get_query_set()
        return qset.filter(completed_date__isnull=True, completed=False)

    def get_timedout_sessions(self):
        qset = super(SessionManager, self).get_query_set()
        return qset.filter(completed_date__isnull=True, completed=False, timeout_date__isnull=False, timeout_date__lte=datetime.now())

    def get_completed_sessions(self):
        qset = super(SessionManager, self).get_query_set()
        return qset.filter(completed_date__isnull=False, completed=True)

class Session(models.Model):
    patient = models.ForeignKey(Patient)
    task = models.ForeignKey(Task)
    process = models.ForeignKey(Process,null=True)
    add_date = models.DateTimeField(auto_now_add=True)
    completed = models.BooleanField(blank=True,default=False)
    completed_date = models.DateTimeField(blank=True,null=True)
    timeout_date = models.DateTimeField(blank=True,null=True)
    state = models.CharField(max_length=100)    

    objects = SessionManager()

    def get_messages(self):
        return self.sessionmessage_set.all()

    def get_status(self):
        if self.completed: return "past"
        else: return "running"
    
    def __unicode__(self):
        return "Session for %s on %s" % (self.patient.address, self.task.name)

class SessionMessage(models.Model):
    session = models.ForeignKey(Session)
    message = models.TextField()
    outgoing = models.BooleanField()
    add_date = models.DateTimeField(auto_now_add=True)
    
    def __unicode__(self):
        if self.outgoing:
            return "Sent to %s: %s" % (self.session.patient.address, self.message)
        else:
            return "Received from %s: %s" % (self.session.patient.address, self.message)
    
class TaskPatientDatapoint(models.Model):
    patient = models.ForeignKey(Patient)
    task = models.ForeignKey(Task)
    add_date = models.DateTimeField(auto_now_add=True)
    data = models.TextField()

    def __unicode__(self):
        return "Datapoint for %s on %s" % (self.patient.address, self.task.name)

# =================================================================
# ==== Scheduled tasks
# =================================================================

class ScheduledTaskManager(models.Manager):
    def get_pending_tasks(self):
        qset = super(ScheduledTaskManager, self).get_query_set()
        return qset.filter(schedule_date__gt=datetime.now(), active=True, completed=False)

    def get_due_tasks(self):
        qset = super(ScheduledTaskManager, self).get_query_set()
        return qset.filter(schedule_date__lte=datetime.now(), active=True, completed=False)

    def get_past_tasks(self):
        qset = super(ScheduledTaskManager, self).get_query_set()
        return qset.filter(schedule_date__lte=datetime.now(), active=True, completed=True)

class ScheduledTask(models.Model):
    patient = models.ForeignKey(Patient)
    task = models.ForeignKey(Task)
    process = models.ForeignKey(Process,null=True)
    add_date = models.DateTimeField(auto_now_add=True)
    arguments = models.TextField(blank=True)
    schedule_date = models.DateTimeField()
    active = models.BooleanField(blank=True, default=True)
    completed = models.BooleanField(blank=True,default=False)
    completed_date = models.DateTimeField(blank=True,null=True)
    result = models.TextField(blank=True)

    objects = ScheduledTaskManager()

    def is_pending(self):
        return (self.schedule_date > datetime.now()) and (not self.completed)

    def is_due(self):
        return (self.schedule_date <= datetime.now()) and (not self.completed)

    def is_past(self):
        return (self.schedule_date <= datetime.now()) and (self.completed)

    def get_status(self):
        if self.is_pending(): return "pending"
        elif self.is_due(): return "due"
        elif self.is_past(): return "past"
        else: return "unknown"

    def __unicode__(self):
        return "Scheduled Task for %s on %s" % (self.patient.address, self.task.name)
