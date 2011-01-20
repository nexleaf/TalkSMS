# tasks/appointment_reminder.py

import sms

from datetime import datetime, timedelta
import json, re

from django.template.loader import render_to_string
from taskmanager.models import *

from task import BaseTask

class AppointmentReminder(BaseTask):
    def __init__(self, user, args=None):

        BaseTask.__init__(self)

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
            q1 = render_to_string('tasks/appts/reminder_nocancel.html', {'patient': self.patient, 'args': self.args})
        else: 
            q1 = render_to_string('tasks/appts/reminder.html', {'patient': self.patient, 'args': self.args})

        r1 = sms.Response('ok', match_regex=r'ok')
        r2 = sms.Response('cancel', match_regex=r'cancel|no', callback=self.cancel)
        r_stop = sms.Response('stop', match_regex=r'stop', label='stop', callback=self.stopped)

        # the initial reminder message
        m1 = sms.Message(
            q1,
            [r1, r2, r_stop],
            label='appt')

        # user ok'd appointment
        m2 = sms.Message(
            'See you soon.', [],
            label='appt')

        # user cancelled appointment
        m3 = sms.Message(
            'Thank you for letting us know. Remember to also actually cancel your appointment with your care provider.', [],
            label='appt')

        # user wants all messages stopped
        m_stop = sms.Message(
            'Ok, stopping messages now. Thank you for participating.', [],
            label='appt')
        
        self.graph = { m1: [m2, m3, m_stop],
                       m2: [],
                       m3: [],
                       m_stop: [] }
        
        # self.interaction = sms.Interaction(graph=self.graph, initialnode=m1, label='interaction')
        super(AppointmentReminder, self).setinteraction(graph=self.graph, initialnode=m1, label='interaction')

    def stopped(self, *args, **kwargs):
        response = kwargs['response']
        session_id = kwargs['session_id']

        # set the halted status on the patient since they sent a stop
        if self.patient:
            self.patient.halted = True

        alert_args = {}
        if self.patient and session_id is not None:
            alert_args['url'] = '/taskmanager/patients/%d/history/#session_%d' % (self.patient.id, session_id)
        alert_args.update(args)
        Alert.objects.add_alert("Messages Stopped", arguments=alert_args, patient=self.patient)

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

    def save(self):
        print 'in %s.save(): ' % (self.__class__.__name__)
        # save whatever you like in the parameter blob
        return json.dumps({})

    # developer required to implement restore():
    def restore(self, pb_str):
        print 'in %s.restore() stub' % (self.__class__.__name__)
        pb = json.loads(pb_str)


