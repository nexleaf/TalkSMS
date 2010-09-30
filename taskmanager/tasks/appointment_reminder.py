# tasks/appointment_reminder.py

import sms

from datetime import datetime, timedelta
import json, re

from django.template.loader import render_to_string
from taskmanager.models import *

class AppointmentReminder(object):
    def __init__(self, user, args=None):

        self.args = args

        print 'in AppointmentReminder:: self.args: %s; type(self.args):%s' % (self.args, type(self.args))
        
        if isinstance(user, sms.User):
            self.user = user
            self.patient = Patient.objects.get(address=self.user.identity)
        else:
            raise ValueError('unknown type given for user: %s' % user)
        
        # out of sms spec. 
        # it seems awkward to me to shoehorn this behavior in...perhaps there's a cleaner way?
        # m1
        if 'nocancel' in self.args:
            # something like:
            # {% load parse_date %}Hello {{ patient.first_name }}. 
            # Reminder: your appointment for {{ args.appt_type }} is {% if args.daybefore %}tomorrow{% else %}today{% endif %} 
            # at {{ args.appt_date|parse_date|time:"g:i A" }}.{% if args.requires_fasting %}No eating or drinking (except water) 
            # for 9hrs before your appointment.{% endif %} Text back OK to confirm receipt of this message.
            q1 = render_to_string('tasks/appts/reminder_nocancel.html', {'patient': self.patient, 'args': self.args})
        else: 
            # something like:
            # {% load parse_date %}Hello {{ patient.first_name }}. 
            # Reminder: your {{ args.appt_type }} is on {{ args.appt_date|parse_date|date:"n/d" }} at {{ args.appt_date|parse_date|time:"g:i A" }}.  
            # If the appointment is cancelled, Text back CANCEL.
            q1 = render_to_string('tasks/appts/reminder.html', {'patient': self.patient, 'args': self.args})
        r1 = sms.Response('ok', r'ok|OK|Ok')
        r2 = sms.Response('cancel', r'cancel|no', callback=self.cancel)
        m1 = sms.Message(q1, [r1,r2])
    
        # m2
        m2 = sms.Message('See you soon.', [])
        
        # m3
        m3 = sms.Message('Ok, canceling reminders as you requested.', [])
        
        self.graph = { m1: [m2, m3],
                       m2: [],
                       m3: [] }
        
        self.interaction = sms.Interaction(self.graph, m1, self.__class__.__name__ + '_interaction')


    def cancel(self, *args, **kwargs):
        session_id = kwargs['session_id']
        session = Session.objects.get(pk=session_id)        

        # set up alert
        alert_args = {}
        if self.patient and session_id is not None:
            alert_args['url'] = '/taskmanager/patients/%d/history/#session_%d' % (self.patient.id, session_id)
        alert_args.update(args)
        Alert.objects.add_alert("Appointment Canceled", arguments=alert_args, patient=self.patient)

        # deactivate all the old scheduled tasks on this process
        # since the statemachine ends after this callback, no need to cancel any response reminders...
        ScheduledTask.objects.filter(process=session.process).update(active=False)



