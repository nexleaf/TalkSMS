# tasks/appointment_followup.py

import sms

from datetime import datetime, timedelta
import json, re

from django.template.loader import render_to_string
from taskmanager.models import *
import taskscheduler

class AppointmentFollowup(object):
    def __init__(self, user, args=None):

        self.args = args
        print 'in appointmentrequest: self.args: %s; type(self.args):%s' % (self.args, type(self.args))
        
        if isinstance(user, sms.User):
            self.user = user
            self.patient = Patient.objects.get(address=self.user.identity)
        else:
            raise ValueError('unknown type given for user: %s' % user)


        # m1
        # something like:
        # Hello {{ patient.first_name }}. You recently had {{ args.appt_type }}. 
        # Please reply with COMMENT followed by your feedback to help us improve our service. 
        # If you missed the appointment and want to be reminded to reschedule, text back a date.
        q1 = render_to_string('tasks/appts/request.html', {'patient': self.patient, 'args': self.args})
        r1 = sms.Response('comment', r'comment|COMMENT', label='comment', callback=self.store_feedback)
        r2 = sms.Response('8/30/2010 16:30', r'\d+/\d+/\d+\s\d+:\d+', label='date', callback=self.reschedule_reminder)
        m1 = sms.Message(q1, [r1,r2])

        # m2
        m2 = sms.Message('Thank you for your feedback.', [])

        # m3
        m3 = sms.Message('Ok, you will be sent a reminder to reschedule as you have requested.', [])
        
        self.graph = { m1: [m2, m3],
                       m2: [],
                       m3: [] }

        self.interaction = sms.Interaction(self.graph, m1, self.__class__.__name__ + '_interaction')


    def store_feedback(self, *args, **kwargs):
        comment = kwargs['response']
        session_id = kwargs['session_id']

        print 'patient feedback: %s' % (feedback)

        alert_data = {'feedback': comment}
        if self.patient and session_id is not None:
            alert_data['url'] = '/taskmanager/patients/%d/history/#session_%d' % (self.patient.id, session_id)
        alert_data.update(args)
        Alert.objects.add_alert("Appointment Feedback", arguments=alert_data, patient=self.patient)
    

    def schedule_new_appointment(self, *args, **kwargs):
        ndatetime = kwargs['response']
        session_id = kwargs['session_id']
        
        print 'in %s.%s: user responsed with date: %s' % (self.__class__, self.__class__.__name__, kwargs['response'])        
        t = datetime.strptime(ndatetime, "%m/%d/%Y %H:%M:%S")

        # make sure we pass on the appointment date
        self.args['appt_date'] = t
        appttime = t.isoformat()

        # sched a reminder. 
        d1 = {'task': 'Appointment Reminder','user':self.user.identity,'args': self.args,'schedule_date': t ,'session_id':session_id}

        try:
            taskscheduler.schedule(d1)
        except Exception as e:
            print '%s' % (e)

        
        
