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

        # (old) r2 = sms.Response('8/30/2012 16:30:00', r'\d+/\d+/\d+\s\d+:\d+:\d+', label='datetime', callback=self.schedule_reminders)

        # first we set up all the expected responses
        # idealy this'd be directly before each message, but most of these responses are repeated in this case
        r_stop = sms.Response('stop', match_regex=r'stop', label='stop', callback=self.appointment_cancelled_alert)
        r_need_date_and_time = sms.Response('asdf', match_callback=AppointmentRequest.match_non_date_and_time, label='non_datetime')
        r_stalling = sms.Response('ok', match_regex=r'ok', label='stalling')
        r_valid_appt = sms.Response('today at 3pm', match_callback=AppointmentRequest.match_date_and_time, label='datetime', callback=self.schedule_reminders)
        
        # lists of responses that'll be used for every node that takes the same input as the initial
        initial_responses = [r_stop, r_stalling, r_need_date_and_time, r_valid_appt]

        # message sent asking the user to schedule an appt. and to text us back the date and time
        m_initial = sms.Message(
            render_to_string('tasks/appts/request.html', {'patient': self.patient, 'args': self.args}),
            initial_responses)
        
        # message sent when the user decides to stop
        m_stop = sms.Message('Ok, stopping messages now. Thank you for participating.', [])

        # message sent if the user doesn't include both date and time
        # this replicates the expected responses of the initial node because it basically is the initial node
        m_need_date_and_time = sms.Message(
            'Please respond with both the date and the time of the appointment you scheduled (e.g. 1/15/2011 8:30pm).',
            initial_responses)

        # message sent when the user delays us by saying 'ok'; we prompt them for more info when they're ready
        # this replicates the expected responses of the initial node because it basically is the initial node
        m_stalling = sms.Message(
            'Please respond with both the date and the time of the appointment when you\'ve scheduled it, or \'stop\' if you don\'t want to schedule one now.',
            initial_responses)
        
        # message sent when the user sends us a valid date and time
        # the response that leads here actually sets up the appointments
        m_valid_appt = sms.Message(render_to_string('tasks/appts/response.html', {'args': self.args}), [])

        # lists of transitions that'll be used for every node that takes the same input as the initial
        # this needs to match up pairwise with initial_responses :\
        initial_transitions = [m_stop, m_stalling, m_need_date_and_time, m_valid_appt]
        
        self.graph = { m_initial: initial_transitions,
                       m_stop: [],
                       m_need_date_and_time: initial_transitions,
                       m_stalling: initial_transitions,
                       m_valid_appt: []
                       }

        self.interaction = sms.Interaction(self.graph, m_initial, self.__class__.__name__ + '_interaction')

    
    @staticmethod
    def match_date_or_time(msgtxt):
        pdt = parsedatetime.Calendar()
        (res, retcode) = pdt.parse(msgtxt)
        if retcode == 0:
            return False
        else:
            return res
        
    @staticmethod
    def match_non_date_and_time(msgtxt):
        pdt = parsedatetime.Calendar()
        (res, retcode) = pdt.parse(msgtxt)
        if retcode == 3:
            return False
        else:
            return res
        
    @staticmethod
    def match_date_and_time(msgtxt):
        pdt = parsedatetime.Calendar()
        (res, retcode) = pdt.parse(msgtxt)
        if retcode != 3:
            return False
        else:
            return res
        
    
    def appointment_cancelled_alert(self, *args, **kwargs):
        response = kwargs['response']
        session_id = kwargs['session_id']

        # set the halted status on the patient since they sent a stop
        if self.patient:
            self.patient.halted = True
            self.patient.save()

        alert_args = {}
        if self.patient and session_id is not None:
            alert_args['url'] = '/taskmanager/patients/%d/history/#session_%d' % (self.patient.id, session_id)
        alert_args.update(args)
        Alert.objects.add_alert("Messages Stopped", arguments=alert_args, patient=self.patient)



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
        # get the first 6 values from the stuct... the rest we do not care about
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
        
        testing = False
        if testing:
            # easier to track msgs
            s = timedelta(seconds=300) # 5 minutes
            a = t+s    # first reminder 5 minutes after datetime reply
            b = t+2*s  # second is 10 minutes after
            c = t+3*s  # third is 15 after
            f = t+4*s  # follow sent 20 hour after
        else:
            # faisal: commented out the above; we're going to use parsedatetime instead for readability
            a = datetime(*pdt.parse("2 days ago at 3:00pm", t)[0][0:7]) # two days before
            b = datetime(*pdt.parse("1 day ago at 8:00pm", t)[0][0:7]) # one night before
            c = datetime(*pdt.parse("2 hours ago", t)[0][0:7]) # two hours before appointment
            f = datetime(*pdt.parse("in 6 hours", t)[0][0:7]) # followup, six hours after

            # check if the followup is going to be after 10pm -- if so, move it to 10am the next day
            if f.hour >= 22:
                f += timedelta(days=1)
                f = f.replace(hour=10)

        # if 'schedule_date' is earlier than now, the scheduled event will be sent immediately
        
        try:
            # reminders (only schedule these if they're in the future)
            if a > datetime.now():
                d1 = {'task': 'Appointment Reminder','user': self.user.identity,'args': self.args,'schedule_date': a,'session_id': session_id}
                taskscheduler.schedule(d1)
            if b > datetime.now():
                d2 = {'task': 'Appointment Reminder','user': self.user.identity,'args': self.args,'schedule_date': b,'session_id': session_id}
                taskscheduler.schedule(d2)
            if c > datetime.now():
                d3 = {'task': 'Appointment Reminder','user': self.user.identity,'args': self.args,'schedule_date': c,'session_id': session_id}
                taskscheduler.schedule(d3)
                
            # followup
            d4 = {'task': 'Appointment Followup','user': self.user.identity,'args': self.args,'schedule_date': f,'session_id': session_id}
            taskscheduler.schedule(d4)
        except Exception as e:
            print '%s' % (e)

        
