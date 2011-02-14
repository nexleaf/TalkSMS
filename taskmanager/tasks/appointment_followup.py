# tasks/appointment_followup.py

import sms

from datetime import datetime, timedelta
from parsedatetime import parsedatetime
import json, re

from django.template.loader import render_to_string
from taskmanager.models import *
import taskscheduler

from task import BaseTask

class AppointmentFollowup(BaseTask):
    RETRY_COUNT = 2 # sends it up to two more times before giving up
    RETRY_TIMEOUT = 60*24 # 60*24 = 1 day
    
    def __init__(self, user, args=None):

        BaseTask.__init__(self)
        
        self.args = args
        print 'in appointmentrequest: self.args: %s; type(self.args):%s' % (self.args, type(self.args))
        
        if isinstance(user, sms.User):
            self.user = user
            self.patient = Patient.objects.get(address=self.user.identity)
        else:
            raise ValueError('unknown type given for user: %s' % user)

        # (old) r2 = sms.Response('8/30/2010 16:30:00', r'\d+/\d+/\d+\s\d+:\d+:\d+', label='datetime', callback=self.reschedule_reminder)

        r_feedback = sms.Response('feedback', match_regex=r'(feedback)', label='feedback', callback=self.store_feedback)
        r_missed = sms.Response('missed', match_regex=r'(missed)', label='missed', callback=self.missed_appt)

        # message asking them for feedback after their appointment
        m1 = sms.Message(
            render_to_string('tasks/appts/followup.html', {'patient': self.patient, 'args': self.args}),
            [r_feedback, r_missed],
            label='resp', retries=AppointmentFollowup.RETRY_COUNT, timeout=AppointmentFollowup.RETRY_TIMEOUT)

        # message sent when user provides feedback in the form 'feedback <my message here>'
        m_thanks = sms.Message('Thank you for your feedback.', [], label='thanks')

        # message sent when user missed their appointment
        m_missed = sms.Message('You will receive a new request to reschedule within a few days.', [], label='missed')
        
        self.graph = { m1: [m_thanks, m_missed],
                       m_thanks: [],
                       m_missed: [] }

        # self.interaction = sms.Interaction(self.graph, m1, self.__class__.__name__ + '_interaction')
        super(AppointmentFollowup, self).setinteraction(graph=self.graph, initialnode=m1, label='interaction')


    # developer is required to implement save()
    def save(self):
        print 'in %s.save(): ' % (self.__class__.__name__)
        # save whatever you like in the parameter blob
        return json.dumps({})

    # developer required to implement restore():
    def restore(self, pb_str):
        print 'in %s.restore() stub' % (self.__class__.__name__)
        pb = json.loads(pb_str)

        
    @staticmethod
    def match_date(msgtxt):
        pdt = parsedatetime.Calendar()
        (res, retcode) = pdt.parse(msgtxt)
        if retcode == 0:
            return False
        else:
            return res
    
    def store_feedback(self, *args, **kwargs):
        comment = kwargs['response']
        session_id = kwargs['session_id']

        # strip off the "feedback " prefix
        comment =  comment[comment.index(" ")+1:]

        print 'patient feedback: %s' % (comment)

        alert_data = {'feedback': comment}
        if self.patient and session_id is not None:
            alert_data['url'] = '/taskmanager/patients/%d/history/#session_%d' % (self.patient.id, session_id)
        alert_data.update(args)
        Alert.objects.add_alert("Appointment Feedback", arguments=alert_data, patient=self.patient)

    def missed_appt(self, *args, **kwargs):
        session_id = kwargs['session_id']

        print 'patient missed their appointment'

        alert_data = {'feedback': comment}
        if self.patient and session_id is not None:
            alert_data['url'] = '/taskmanager/patients/%d/history/#session_%d' % (self.patient.id, session_id)
        alert_data.update(args)
        Alert.objects.add_alert("Appointment Missed", arguments=alert_data, patient=self.patient)
    
    # FAISAL: not currently used
    def reschedule_reminder(self, *args, **kwargs):
        ndatetime = kwargs['response']
        session_id = kwargs['session_id']
        
        print 'in %s: user responsed with date: %s' % (self.__class__, kwargs['response'])
        print 'args: %s kwargs: %s' % (args, kwargs)
        print 'self.args: %s' % (self.args)

        pdt = parsedatetime.Calendar()
        (res, retval) = pdt.parse(ndatetime)
        if retval == 0:
            raise ValueError("Unable to parse date time: %s" % (ndatetime))
        # get the first 6 values from teh stuct... the rest we do not care about
        t = datetime(*res[0:7])

        # support cens gui: app_date used to display appointment time only
        # Tuesday, 5:30pm, November 03, 2010
        appttime = t.strftime("%m/%d/%Y %I:%M%p")
        # make sure we pass on the appointment date
        self.args['appt_date'] = appttime
        print 'self.args: %s' % (self.args)

        # sched a reminder.
        d1 = {'task': 'Appointment Reminder','user': self.user.identity,'args': self.args,'schedule_date': t,'session_id': session_id}
    
        try:
            taskscheduler.schedule(d1)
        except Exception as e:
            print '%s' % (e)

        
        
