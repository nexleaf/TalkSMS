# tasks.appointment_request.AppointmentRequest

import sms

from datetime import datetime, timedelta
import json, re

from django.template.loader import render_to_string
from taskmanager.models import *


class AppointmentRequest(object):
    def __init__(self, user, args):

        if args:
            self.args = args
        else:
            self.args = None

        if isinstance(user, sms.User):
            self.user = user
        else:
            raise ValueError('unknown type given for user: %s' % user)

        # m1
        # q1 = """Hello {firstname}, you're due for a checkup with {drname} soon.
        #         If you would like to schedule one now, text me back a preferred date and time like this (mm/dd/yyyy hh:mm:ss).
        #         Or respond with 'no' if you don't want to
        #         schedule anything now.""".format(firstname=self.user.firstname, drname=self.drname)
        q1 = 'q1; args: %s' % (args) 
        r1 = sms.Response('no', r'n|N', 'no')
        r2 = sms.Response('8/30/2010 16:30:00', r'\d+/\d+/\d+\s\d+:\d+:\d+', label='datetime', callback=self.schedule_new_appointment)
        m1 = sms.Message(q1, [r1,r2])

        # m2
        q2 = 'q2'
        m2 = sms.Message(q2, [])

        # m3
        q3 = 'q3'
        m3 = sms.Message(q3, [])
        
        self.graph = { m1: [m2, m3],
                       m2: [],
                       m3: [] }

        self.interaction = sms.Interaction(self.graph, m1, self.__class__.__name__ + '_interaction')

    
    def schedule_new_appointment(self, *args, **kwargs):
        ndatetime = kwargs['response']
        session_id = kwargs['session_id']
        
#        assert(re.match(r'\d+/\d+/\d+\s\d+:\d+', ndatetime) is not None)
        print 'in %s.%s: user responsed with date: %s' % (self.__class__, self.__class__.__name__, kwargs['response'])

        # search appointment calendar for nearest open appointment returning datetime (ndatetime used here)
        t = datetime.strptime(ndatetime, "%m/%d/%Y %H:%M:%S")
        s = timedelta(days=3)
        i = timedelta(microseconds=1)

        appttime = t.isoformat()
        remindertime = (t-s+i).isoformat()
        
        # scheduler does this by executing immediately, any new tasks scheduled to start before 'now':
        # if remindertime is earlier than now,
        #   schedule the reminder to be sent immediately.

        #callback_args = json.JSONEncoder().encode([self.drname, appttime])
        d = {'task': 'Appointment Reminder', 'user':self.user.identity, 'args': [self.drname, appttime], 'schedule_date':remindertime, 'session_id':session_id}
        #pf = [('sarg', json.dumps(d))]
        
        try:
            sms.TaskManager.schedule(d)
        except:
            print 'error: could not schedule a new appointment'

        
