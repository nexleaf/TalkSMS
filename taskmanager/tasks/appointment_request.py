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
    def __init__(self, user, args=None):

        BaseTask.__init__(self)

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
        r1 = sms.Response('stop', match_regex=r'stop|STOP', label='r1', callback=self.appointment_cancelled_alert)
        
        #r2 = sms.Response('8/30/2012 16:30:00', r'\d+/\d+/\d+\s\d+:\d+:\d+', label='datetime', callback=self.schedule_reminders)
        r2 = sms.Response('8/30/2012 16:30:00', match_callback=AppointmentRequest.match_date, label='r2', callback=self.schedule_reminders)
        m1 = sms.Message(q1, [r1,r2], label='m1')
        
        # m2
        q2 = 'Ok, stopping messages now. Thank you for participating.'
        m2 = sms.Message(q2, [], label='m2')
        
        # m3
        # resolves to:
        # Great, we set up 3 appt. reminders and a followup for you.
        q3 = render_to_string('tasks/appts/rescheduled.html', {'args': self.args})
        m3 = sms.Message(q3, [], label='m3')

        # define a super class with .restore() in it. below, user will call createGraph(), createInteraction()
        # which remember handles to graph and interaction. when .restore() is called it just updates the node we're at searching with the label.
        graph = { m1: [m2, m3],
                  m2: [],
                  m3: [] }
        
        # set self.graph
        self.graph = graph
        # set self.interaction
        # self.interaction =  sms.Interaction(graph=self.graph, initialnode=m1, label='interaction')
        super(AppointmentRequest, self).setinteraction(graph=self.graph, initialnode=m1, label='interaction')
        

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

