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
        
        # this is awkward for messaging (please refer to the spec). 
        # a cleaner solution is two reminder tasks like: 'Reminder' and 'Cancellable Reminder'
        # below you must support both response (ok and cancel) which would allow a user to cancel when you don't want them to...

        # m1
        if 'nocancel' in self.args:
            # resolves to:
            # {% load parse_date %}Your {{ args.appt_type }} is approaching. Reply 'ok' to confirm.
            q1 = render_to_string('tasks/appts/reminder_nocancel.html', {'patient': self.patient, 'args': self.args})
        else: 
            # resolves to:
            #{% load parse_date %}Your {{ args.appt_type }} is approaching. Reply 'cancel' to cancel it or 'ok' to confirm.
            q1 = render_to_string('tasks/appts/reminder.html', {'patient': self.patient, 'args': self.args})
        r1 = sms.Response('ok', r'ok|OK|Ok')
        r2 = sms.Response('cancel', r'cancel|no', callback=self.cancel)
        m1 = sms.Message(q1, [r1,r2])
    
        # m2
        q2 = 'See you soon.'
        m2 = sms.Message(q2, [])
        
        # m3
        q3 = 'Ok, canceling reminders as you requested.'
        m3 = sms.Message(q3, [])
        
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
        # the statemachine ends after this callback, no need to cancel any response reminders.
        ScheduledTask.objects.filter(process=session.process).update(active=False)



