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


# =================================================================
# ==== Users
# =================================================================

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

class Patient(models.Model):
    address = models.CharField(max_length=200)
    first_name = models.CharField(max_length=80)
    last_name = models.CharField(max_length=80)
    clinicians = models.ManyToManyField(Clinician)
    halted = models.BooleanField(default=False)

    def __unicode__(self):
        return "%s, %s (%s)" % (self.last_name, self.first_name, self.address)

# =================================================================
# ==== Services and Alerts
# =================================================================

class Service(models.Model):
    name = models.CharField(max_length=100, unique=True, db_index=True)
    last_status = models.CharField(max_length=100, blank=True, null=True)
    last_status_date = models.DateTimeField(blank=True, null=True)

    def __unicode__(self):
        return self.name

class AlertType(models.Model):
    STATUSES =(
            (u'error', u'error'),
            (u'info', u'info'),
            (u'exception', u'exception'),
            (u'generic', u'generic')
        )
    
    name = models.CharField(max_length=100, unique=True, db_index=True)
    service = models.ForeignKey(Service)
    title_template = models.CharField(max_length=500)
    message_template = models.TextField()
    status = models.CharField(max_length=100, choices=STATUSES)
    
    def __unicode__(self):
        return self.name

class AlertManager(models.Manager):
    def add_alert(self, alert_type, title="", message="", arguments={}, patient=None):
        na = Alert(
            alert_type = AlertType.objects.get(name=alert_type),
            title = title,
            message = message,
            arguments = json.dumps(arguments),
            patient = patient
            )
        na.save()
    
class Alert(models.Model):
    alert_type = models.ForeignKey(AlertType)
    patient = models.ForeignKey(Patient, blank=True, null=True)
    title = models.CharField(max_length=100)
    message = models.TextField()
    arguments = models.TextField()
    add_date = models.DateTimeField(auto_now_add=True)

    objects = AlertManager()

    class Meta:
        ordering = ['-add_date']

    def __unicode__(self):
        if self.patient:
            return "%s for %s" % (self.alert_type, self.patient)    
        else:
            return self.alert_type

# =================================================================
# ==== Task Descriptions
# =================================================================

class Task(models.Model):
    name = models.CharField(max_length=100)
    module = models.CharField(max_length=100)
    className = models.CharField(max_length=100)
    schedulable = models.BooleanField(blank=True,default=False)

    # maintains the templates used by this task
    templates = models.ManyToManyField(dbtemplates.models.Template, blank=True, null=True)
    
    def __unicode__(self):
        return "%s (%s.%s)" % (self.name, self.module, self.className)

class TaskTemplate(models.Model):
    name = models.CharField(max_length=100)
    task = models.ForeignKey(Task)
    arguments = models.TextField(blank=True)

    def __unicode__(self):
        return "%s" % (self.name)

# =================================================================
# ==== Processes (Scheduled Task + Session aggregation)
# =================================================================

class ProcessManager(models.Manager):
    def get_pending_processes(self):
        # a pending process has only incomplete scheduled tasks and no completed sessions
        qset = super(ProcessManager, self).get_query_set()
        return qset.exclude(scheduledtask__completed=True).exclude(session__completed=True)
    
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

    class Meta:
        verbose_name_plural = "processes"

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
# ==== Scheduled Tasks
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

# =================================================================
# ==== Serialized Task
# ==== (used to store state of running tasks between system reboots)
# =================================================================

class SerializedTask(models.Model):
    # orig args sent to task
    t_args = models.CharField(max_length=500)
    # parameter blob: json_self.args from the task
    t_pblob = models.CharField(max_length=500)

    ## serialized attributes for sms.StateMachine, representing state at last .save()
    s_app = models.CharField(max_length=50)

    # FAISAL: replaced s_session_id being an IntegerField with it being a real foreign key
    ## we will use this as a foreign key into the Session/taskmanager_session table
    # s_session_id = models.IntegerField(max_length=50)
    s_session = models.ForeignKey(Session)

    # tasknamespace id's can be saved as json strings so that switching between simple id types (string, int)
    #    doesn't change the db model.
    s_tnsid = models.CharField(max_length=50)

    s_done = models.BooleanField(max_length=50)
    # label of the message node that's currently referenced in the statemachine as self.node.
    s_node = models.CharField(max_length=50)
    #s_event = models.CharField(max_length=50)
    # last response left in statemachine.mbox
    s_last_response = models.CharField(max_length=150)

    ## serialized attributes for sms.Message 
    m_sentcount = models.IntegerField(max_length=5)
    m_retries = models.IntegerField(max_length=5)
    m_timeout = models.IntegerField(max_length=8)
    
    ## serialized attributes for sms.Interaction
    # label for the initial node
    i_initialnode = models.CharField(max_length=30) 
    

    
    def __unicode__(self):
        return """
    t_args: %s
    t_pblob: %s
    s_app: %s
    s_session_id: %s
    s_tnsid: %s
    s_done: %s
    s_node: %s
    s_last_response: %s
    m_sent_count: %s
    m_retries: %s
    m_timeout: %s
    i_initialnode: %s
        """ % (self.t_args,\
               self.t_pblob,\
               self.s_app,\
               self.s_session_id,\
               self.s_tnsid, \
               self.s_done,\
               self.s_node,\
               self.s_last_response,\
               self.m_sentcount, \
               self.m_retries,\
               self.m_timeout,\
               self.i_initialnode)



# =================================================================
# ==== Misc
# =================================================================


class UnmatchedMessages(models.Model):
    identity = models.CharField(max_length=256)
    message_datetime = models.DateTimeField(auto_now_add=True)
    message_text = models.CharField(max_length=256)
    
    class Meta:
        ordering = ['-message_datetime']
