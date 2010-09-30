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
import taskscheduler

class AppointmentRequest(object):
    def __init__(self, user, args=None):

        self.args = args

        # hack...this doesn't seem to be set anywhere else
        if 'contact_number' not in self.args:
            self.args['contact_number'] = '+13105555555'

        print 'in appointmentrequest: self.args: %s; type(self.args):%s' % (self.args, type(self.args))
        
        if isinstance(user, sms.User):
            self.user = user
            self.patient = Patient.objects.get(address=self.user.identity)
        else:
            raise ValueError('unknown type given for user: %s' % user)


        # m1
        # something like: 
        # Hello {{ patient.first_name }}, you're due for a {{ args.appt_type }}. 
        # Call {{ args.contact_number }} to schedule.  
        # Text me back a date and time (like 10/1/2012 16:30:00) after you schedule. Text STOP to stop messages
        q1 = render_to_string('tasks/appts/request.html', {'patient': self.patient, 'args': self.args})
        r1 = sms.Response('stop', r'stop|STOP', label='stop', callback=self.appointment_cancelled_alert)
        r2 = sms.Response('8/30/2012 16:30:00', r'\d+/\d+/\d+\s\d+:\d+:\d+', label='datetime', callback=self.schedule_reminders)
        m1 = sms.Message(q1, [r1,r2])
        # m2
        q2 = 'Ok, stopping messages now. Thank you for participating.'
        m2 = sms.Message(q2, [])
        # m3
        # something like:
        # Thank you; your {{ args.appt_type }} is scheduled for {{ appt_date|date:"n/d" }} at {{ appt_date|time:"g:i A" }}. 
        # You'll be reminded two days before, the night before, and the morning of your appointment.
        q3 = render_to_string('tasks/appts/rescheduled.html', {'args': self.args})
        m3 = sms.Message(q3, [])
        
        self.graph = { m1: [m2, m3],
                       m2: [],
                       m3: [] }

        self.interaction = sms.Interaction(self.graph, m1, self.__class__.__name__ + '_interaction')


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
        t = datetime.strptime(ndatetime, "%m/%d/%Y %H:%M:%S")
        s = timedelta(days=1)
        i = timedelta(microseconds=1)

        appttime = t.isoformat()
        # make sure we pass on the appointment date
        self.args['appt_date'] = appttime
        print 'self.args: %s' % (self.args)        

        # easier to track msgs
        testing = True
        if testing:
            s = timedelta(seconds=900) # 15 minutes
            a = t+s    # first reminder 15 minutes after datetime reply
            b = t+2*s  # second is 30 minutes after
            c = t+3*s  # third is 45 after
            f = t+4*s  # follow sent 1 hour after
        else: 
            # actually, -3, -2, -1 days for reminders; +1 day for followup
            a = t-3*s  # two days before
            b = t-2*s  # one night before
            c = t-s+i  # morning of appointment
            f = t+s+i  # followup, one day after...

        # if 'schedule_date' is earlier than now, the scheduled event will be sent immediately

        # sched 3 reminders. 
        d1 = {'task': 'Appointment Reminder','user': self.user.identity,'args': self.args,'schedule_date': a,'session_id': session_id}
        d2 = {'task': 'Appointment Reminder','user': self.user.identity,'args': self.args,'schedule_date': b,'session_id': session_id}
        d3 = {'task': 'Appointment Reminder','user': self.user.identity,'args': self.args,'schedule_date': c,'session_id': session_id}
        # sched followup
        d4 = {'task': 'Appointment Followup','user': self.user.identity,'args': self.args,'schedule_date': f,'session_id': session_id}

        try:
            # reminders
            taskscheduler.schedule(d1)
            taskscheduler.schedule(d2)
            taskscheduler.schedule(d3)
            # followup
            taskscheduler.schedule(d4)
        except Exception as e:
            print '%s' % (e)

        
