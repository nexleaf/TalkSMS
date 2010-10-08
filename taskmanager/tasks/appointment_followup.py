# tasks/appointment_followup.py

import sms

from datetime import datetime, timedelta
from parsedatetime import parsedatetime
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
        # resolves to:
        # How was your {{ args.appt_type }}? Reply with 'comment' and feedback; or a time (10/1/2020 16:30:00) to reschedule.
        q1 = render_to_string('tasks/appts/request.html', {'patient': self.patient, 'args': self.args})
        r1 = sms.Response('comment', match_regex=r'comment|COMMENT', label='comment', callback=self.store_feedback)
        #r2 = sms.Response('8/30/2010 16:30:00', r'\d+/\d+/\d+\s\d+:\d+:\d+', label='datetime', callback=self.reschedule_reminder)
        r2 = sms.Response('8/30/2010 16:30:00', match_callback=AppointmentFollowup.match_date, label='datetime', callback=self.reschedule_reminder)
        m1 = sms.Message(q1, [r1,r2])

        # m2
        q2 = 'Thank you for your feedback.'
        m2 = sms.Message(q2, [])

        # m3
        q3 = 'Ok, you will be sent a reminder to reschedule as you have requested.'
        m3 = sms.Message(q3, [])
        
        self.graph = { m1: [m2, m3],
                       m2: [],
                       m3: [] }

        self.interaction = sms.Interaction(self.graph, m1, self.__class__.__name__ + '_interaction')
    
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

        print 'patient feedback: %s' % (feedback)

        alert_data = {'feedback': comment}
        if self.patient and session_id is not None:
            alert_data['url'] = '/taskmanager/patients/%d/history/#session_%d' % (self.patient.id, session_id)
        alert_data.update(args)
        Alert.objects.add_alert("Appointment Feedback", arguments=alert_data, patient=self.patient)
    

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

        #t = datetime.strptime(ndatetime, "%m/%d/%Y %H:%M:%S")

        appttime = t.isoformat()
        # make sure we pass on the appointment date
        self.args['appt_date'] = appttime
        print 'self.args: %s' % (self.args)        

        # sched a reminder. 
        d1 = {'task': 'Appointment Reminder','user': self.user.identity,'args': self.args,'schedule_date': t,'session_id': session_id}

        try:
            taskscheduler.schedule(d1)
        except Exception as e:
            print '%s' % (e)

        
        
