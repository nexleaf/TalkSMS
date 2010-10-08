# tasks/appointment_request.py

# task as a config file:
#    * you determine the structure of the interaction as a graph. 
#      messages sent are nodes, responses are transitions. 
#      final nodes have no responses, and an initial node must be defined.
#      each response, or transition, affects change by calling an optional user-defined callback
#    * once a task object is instantiated, sms.TaskManager.run() (called from app.py) 
#      starts the statemachine, sends out the first message, and handles responses 
#      tracing a path through the graph which is the interaction.  
#    * (future) authorship also becomes a possiblity since it would be easier to have a 
#      task set-up from the gui...

import sms

from datetime import datetime, timedelta
import json, re

from django.template.loader import render_to_string
from taskmanager.models import *
from parsedatetime import parsedatetime
import taskscheduler

class AppointmentRequest(object):
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
        # Hi {{ patient.first_name }}. Please schedule a {{ args.appt_type }}. 
        # Reply with a time (like 10/1/2012 16:30:00), or 'stop' to quit. 
        q1 = render_to_string('tasks/appts/request.html', {'patient': self.patient, 'args': self.args})
        r1 = sms.Response('stop', match_regex=r'stop|STOP', label='stop', callback=self.appointment_cancelled_alert)
        #r2 = sms.Response('8/30/2012 16:30:00', r'\d+/\d+/\d+\s\d+:\d+:\d+', label='datetime', callback=self.schedule_reminders)
        r2 = sms.Response('8/30/2012 16:30:00', match_callback=AppointmentRequest.match_date, label='datetime', callback=self.schedule_reminders)
        m1 = sms.Message(q1, [r1,r2])
        # m2
        q2 = 'Ok, stopping messages now. Thank you for participating.'
        m2 = sms.Message(q2, [])
        # m3
        # resolves to:
        # Great, we set up 3 appt. reminders and a followup for you.
        q3 = render_to_string('tasks/appts/rescheduled.html', {'args': self.args})
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
            
    
    def appointment_cancelled_alert(self, *args, **kwargs):
        response = kwargs['response']
        session_id = kwargs['session_id']

        alert_args = {}
        if self.patient and session_id is not None:
            alert_args['url'] = '/taskmanager/patients/%d/history/#session_%d' % (self.patient.id, session_id)
        alert_args.update(args)
        Alert.objects.add_alert("Appointment Canceled", arguments=alert_args, patient=self.patient)



    def schedule_reminders(self, *args, **kwargs):
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
        s = timedelta(days=1)
        i = timedelta(microseconds=1)

        # support cens gui: appt_date used to display the appointment time only
        #                     Tuesday, 5:30pm, November 03, 2010
        appttime = t.strftime("%A %I:%M%p, %B %d, %Y")
        # make sure we pass on the appointment date
        self.args['appt_date'] = appttime
        print 'self.args: %s' % (self.args)        

        testing = True
        if testing:
            # easier to track msgs
            s = timedelta(seconds=900) # 15 minutes
            a = t+s    # first reminder 15 minutes after datetime reply
            b = t+2*s  # second is 30 minutes after
            c = t+3*s  # third is 45 after
            f = t+4*s  # follow sent 1 hour after
        else: 
            # actually, -3, -2, -1 days for reminders; +1 day for followup
            # NOTE: If we are one or two days before appointment, need to do the right thing here
            # so they do not get too many reminders
            a = t-3*s  # two days before
            b = t-2*s  # one night before
            c = t-s+i  # morning of appointment
            f = t+s+i  # followup, one day after...

        # if 'schedule_date' is earlier than now, the scheduled event will be sent immediately

        # sched 3 reminders. 
        d1 = {'task': 'Appointment Reminder','user': self.user.identity,'args': self.args,'schedule_date': a.isoformat(),'session_id': session_id}
        d2 = {'task': 'Appointment Reminder','user': self.user.identity,'args': self.args,'schedule_date': b.isoformat(),'session_id': session_id}
        d3 = {'task': 'Appointment Reminder','user': self.user.identity,'args': self.args,'schedule_date': c.isoformat(),'session_id': session_id}
        # sched followup
        d4 = {'task': 'Appointment Followup','user': self.user.identity,'args': self.args,'schedule_date': f.isoformat(),'session_id': session_id}

        try:
            # reminders
            taskscheduler.schedule(d1)
            taskscheduler.schedule(d2)
            taskscheduler.schedule(d3)
            # followup
            taskscheduler.schedule(d4)
        except Exception as e:
            print '%s' % (e)

        
