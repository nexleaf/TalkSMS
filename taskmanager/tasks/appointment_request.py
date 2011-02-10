# tasks/appointment_request.py

# task as a config file:
#    * you determine the structure of the interaction as a graph. 
#      messages sent are nodes, responses are transitions. 
#      final nodes have no responses, and an initial node must be defined.
#      each response, or transition, affects change by calling an optional user-defined callback
#    * once a task object is instantiated, sms.TaskManager.run() (called from app.py) 
#      starts the statemachine, sends out the first message, and handles responses 
#      tracing a path through the graph which is the interaction.

#    * implement save(), restore(): ...

#    * (future) authorship also becomes a possiblity since it would be easier to have a 
#      task set-up from the gui.


import sms

from datetime import datetime, timedelta
import json, re

from django.template.loader import render_to_string
from taskmanager.models import *
from parsedatetime import parsedatetime
import taskscheduler

from task import BaseTask

class AppointmentRequest(BaseTask):
    RETRY_COUNT = 2 # sends it up to two more times before giving up
    RETRY_TIMEOUT = 240 # 240 minutes = 4 hours
    
    def __init__(self, user, args=None):

        BaseTask.__init__(self)

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
            initial_responses,
            label='remind', retries=AppointmentRequest.RETRY_COUNT, timeout=AppointmentRequest.RETRY_TIMEOUT)
        
        # message sent when the user decides to stop
        m_stop = sms.Message(
            'Ok, stopping messages now. Thank you for participating.', [],
            label='remind')

        # message sent if the user doesn't include both date and time
        # this replicates the expected responses of the initial node because it basically is the initial node
        m_need_date_and_time = sms.Message(
            'Please respond with both the date and the time of the appointment you scheduled (e.g. 1/15/2011 8:30pm).',
            initial_responses,
            label='remind', retries=AppointmentRequest.RETRY_COUNT, timeout=AppointmentRequest.RETRY_TIMEOUT)

        # message sent when the user delays us by saying 'ok'; we prompt them for more info when they're ready
        # this replicates the expected responses of the initial node because it basically is the initial node
        m_stalling = sms.Message(
            'Please respond with both the date and the time of the appointment when you\'ve scheduled it, or \'stop\' if you don\'t want to schedule one now.',
            initial_responses,
            label='remind', retries=AppointmentRequest.RETRY_COUNT, timeout=AppointmentRequest.RETRY_TIMEOUT)
        
        # FAISAL: left to demonstrate no match callback parameter
        # m1 = sms.Message(q1, [r1,r2], label='m1', no_match_callback=self.no_match_test)
        
        # message sent when the user sends us a valid date and time
        # the response that leads here actually sets up the appointments
        m_valid_appt = sms.Message(
            "returned by custom msg callback", [],
            label='remind', custom_message_callback=self.valid_appt_msg_callback)

        # lists of transitions that'll be used for every node that takes the same input as the initial
        # this needs to match up pairwise with initial_responses :\
        initial_transitions = [m_stop, m_stalling, m_need_date_and_time, m_valid_appt]

        # define a super class with .restore() in it. below, user will call createGraph(), createInteraction()
        # which remember handles to graph and interaction. when .restore() is called it just updates the node we're at searching with the label.
        self.graph = { m_initial: initial_transitions,
                       m_stop: [],
                       m_need_date_and_time: initial_transitions,
                       m_stalling: initial_transitions,
                       m_valid_appt: []
                       }

        super(AppointmentRequest, self).setinteraction(graph=self.graph, initialnode=m_initial, label='interaction')


    def no_match_test(self, node, response, session_id):
        return "I want some representation of a future date dummy"
    
    def custom_message_test(self, message_obj):
        t = datetime.now()
        return "Stopping messages at %s. Thank you for participating" % (t)

    def valid_appt_msg_callback(self, message_obj, received_msg):
        # parse out the date so we can tell it to them in the message
        # this is guaranteed to work since it's gone through validation already
        pdt = parsedatetime.Calendar()
        (res, retval) = pdt.parse(received_msg)
        t = datetime(*res[0:7])
        appttime = t.strftime("%m/%d/%Y %I:%M%p")

        print "*** CALLBACK GOT THE FOLLOWING TEXT: " + str(received_msg) + ", parsed as: " + str(appttime)

        # return them a message that includes the time they selected in the message body (finally! :D)
        return render_to_string('tasks/appts/response.html', {'args': self.args, 'appttime': appttime})

    
    # developer is required to implement save()
    # we save (most of) the stuff above, so what does the developer require in the functions below
    # 
    # self.args
    # ...
    #
    def save(self):
        print 'in %s.save(): ' % (self.__class__.__name__)
        # save whatever you like in the parameter blob
        pb = {}
        pb['args'] = self.args
        # # example of saving more stuff
        # pb['data2'] = json.dumps(self.data2)
        # pb['data1'] = json.dumps(self.data1)         
        return json.dumps(pb)

    # developer required to implement restore():
    def restore(self, pb_str):
        print 'in %s.restore() stub' % (self.__class__.__name__)
        pb = json.loads(pb_str)
        self.args = pb['args']

    # uits: user can send in this string to immediately schedule this task
    @staticmethod
    def get_user_init_string():
        return "apptreq"

    # uits: these strings narrow down the request to the type of task needed.
    @classmethod
    def determine_task_type(cls, message):
        # parses message and tries to figure out the sub task type
        # if message has a keyword, determine taskname, tasktype, args and return them
        
        print 'in appointment request.determin_task_type():'

        keywords = ('dexa', 'provider', 'echo', 'ekg', 'blood')
        msg = str(message.text).lower()

        for word in keywords:
            if msg.find(word) > -1:
                tt = TaskTemplate.objects.filter(task__className__exact=cls.__name__, name__icontains=word)[0]
                print 'tt.task.id: %s' % tt.task.id
                t = Task.objects.get(pk=tt.task.id)
                print 't.name: %s; tt.name: %s, tt.arguments: %s' % (t.name, tt.name, tt.arguments)
                arguments = eval(tt.arguments)

                if word is 'blood':
                    if msg.find('fasting') > -1:
                        arguments['requires_fasting'] = 1
                    else:
                        arguments['requires_fasting'] = 0
                        
                print 't.name: %s; tt.name: %s; arguments: %s' % (t.name, tt.name, arguments)
                return (t.name, tt.name, arguments)

        # no match found
        return None

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
        # FAISAL: changed the date output format b/c parsedatetime doesn't read past the day of the week :\
        appttime = t.strftime("%m/%d/%Y %I:%M%p")
        # make sure we pass on the appointment date
        self.args['appt_date'] = appttime
        print 'self.args: %s' % (self.args)
        
        testing = True
        if testing:
            # easier to track msgs
            s = timedelta(seconds=120) # 5 minutes
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

