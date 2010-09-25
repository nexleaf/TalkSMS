import sys, json, re
from datetime import datetime, timedelta

import rapidsms
import rapidsms.contrib.scheduler.app as sched
from rapidsms.contrib.scheduler.models import EventSchedule, ALL

import tasks.sms as sms
import tasks.appointment_request
import tasks.appointment_reminder
import tasks.appointment_followup

from taskmanager.models import *


class App(rapidsms.apps.base.AppBase):
    def start(self):

        self.counter = 0
        # keep until persistence is implemented
        # since we're just starting, any existing sessions must be complete
        Session.objects.filter(completed=False).update(completed=True, completed_date=datetime.now(), state='router_restarted')

        # initialize and start TalkSMS
        self.tm = sms.TaskManager(self)
        self.tm.run()
        self.debug('app.Taskmanager start time: %s', datetime.now())

    def handle (self, message):
        self.debug('in App.handle(): message type: %s, message.text: %s', type(message),  message.text)
        response = self.tm.recv(message)
        #self.debug("message.subject: %s; responding: %s", message.subject, response)
        message.respond(response)


    def send(self, identity, identityType, text):
        self.debug('in App.send():')
        try:
            from rapidsms.models import Backend 
            bkend, createdbkend = Backend.objects.get_or_create(name=identityType)        
            conn, createdconn = rapidsms.models.Connection.objects.get_or_create(backend=bkend, identity=identity)
            message = rapidsms.messages.outgoing.OutgoingMessage(conn, text)
            
            if identityType is 'email':
                message.subject='testing '+ str(self.__class__)

            if message.send():
                self.debug('sent message.text: %s', text)
        except Exception as e:
            self.debug('problem sending outgoing message: createdbkend?:%s; createdconn?:%s; exception: %s', createdbkend, createdconn, e)

    # schedules reminder to respond messages
    def schedule_response_reminders(self, d):
        self.debug('in App.schedulecallback(): self.router: %s', self.router)
        cb = d.pop('callback')
        m = d.pop('minutes')
        reps = d.pop('repetitions')
        self.debug('callback:%s; minutes:%s; repetitions:%s; kwargs:%s',cb,m,reps,d)
        
        t = datetime.now()
        s = timedelta(minutes=m)
        one = timedelta(minutes=1)
    
        # for n in [(t + 1*s), (t + 2*s), ... (t + r+s)], where r goes from [1, reps+1)
        for n in [t + r*s for r in range(1,reps+1)]:
            st,et = n,n+one
            self.debug('scheduling a reminder to fire between [%s, %s]', st, et)
            schedule = EventSchedule(callback=cb, minutes=ALL, callback_kwargs=d, start_time=st, end_time=et)
            schedule.save()               
              
    def resend(self, msgid=None, identity=None):
        self.debug('in App.resend():')        
        statemachine = self.findstatemachine(msgid, identity)

        if statemachine:
            assert(isinstance(statemachine, sms.StateMachine)==True)
            assert(statemachine.msgid==msgid)
            sm = statemachine
            cn = statemachine.node

            self.debug('sm: %s; cn: %s; sm.node: %s; sm.node.sentcount: %s', sm, cn, sm.node, sm.node.sentcount)
            # if we're still waiting for a response, send a reminder and update sentcount
            if (sm.node.sentcount < sms.StateMachine.MAXSENTCOUNT):
                self.debug('sm.node.sentcount incremented to: %s', sm.node.sentcount)
                self.tm.send(statemachine)
        

    def findstatemachine(self, msgid, identity):
        self.debug('in App.findstatemachine(): msgid:%s, identity: %s', msgid, identity)
        cl = []
        for sm in self.tm.uism:
            if (sm.msgid == msgid) and (sm.user.identity == identity):
                cl.append(sm)
                
        if len(cl) > 1:
            self.error('found more than one statemachine, candidate list: %s', cl)
            statemachine = None
        elif len(cl) == 0:
            self.debug('found no matching statemachine, candidate list: %s', cl)
            statemachine = None
        else:
            assert(len(cl)==1)
            self.debug('found statemachine: %s', cl)
            statemachine = cl[0]

        return statemachine
        

    def finduser(self, identity=None, firstname=None, lastname=None):
        """find or create user"""
        # should be a db look up
        for statemachine in self.tm.uism:
            if statemachine.user.identity in identity:
                return statemachine.user
        try:
            user = sms.User(identity=identity, firstname=firstname, lastname=lastname)
        except Exception as e:
            user = None
            self.error('Could not create user using identity: %s; Exception: %s', identity, e)
        return user

                                        
    def ajax_GET_status(self, getargs, postargs=None):
        instances = []
        for statemachine in self.tm.uism:
            # only serialize the db objects
            instances.append({
                'session': statemachine.session,
                'patient': Patient.objects.get(address=statemachine.user.identity),
                'args': {},
                'state': statemachine.event
                })
        self.debug('in app.ajax_GET_status(): instances: %s', instances)
        #return instances
        return {'status':'OK'}


    def session_updatestate(self, session_id, state):
        session = Session.objects.get(pk=session_id)
        session.state = state
        self.debug('in app.session_updatestate():')
        session.save()
        

    def session_close(self, session_id):
        # the statemachine is done, mark session closed
        session = Session.objects.get(pk=session_id)        
        session.completed_date = datetime.now()
        session.completed = True
        self.debug('in app.session_close():')
        session.save()



    def ajax_POST_exec(self, getargs, postargs=None):
        task = Task.objects.get(pk=postargs['task'])
        patient = Patient.objects.get(pk=postargs['patient'])
        args = eval(json.loads(postargs['arguments']))
        
        if 'process' in postargs:
            process = Process.objects.get(pk=postargs['process'])
        else:
            process = None
        
        print 'printing args: %s; type: %s' % (args, type(args))

        # returns existing user, otherwise returns a new user 
        smsuser = self.finduser(patient.address, patient.first_name, patient.last_name)

        __import__(task.module, globals(), locals(), [task.className])   
        module = '%s.%s' % (task.module, task.className)


        print module
        print type(module)
        if not args:
            t = eval(module)(smsuser)
        else:
            t = eval(module)(smsuser, args)

        # create a new session in db (sessions are only killed when statemachines are done)
        session = Session(patient=patient, task=task, process=process, state='unknown')
        session.save()

        # create and start task
        sm = sms.StateMachine(self, smsuser, t.interaction, session.id)
        self.tm.addstatemachines(sm)
        self.tm.run()

        # save the session regardless of what happens
        session.save()

        self.counter = self.counter + 1
        
        return {'status': 'OK'}


    def ajax_POST_timeout(self, getargs, postargs=None):
        patient = Patient.objects.get(pk=postargs['patient'])
        session = Session.objects.get(pk=postargs['session'])

        # gutted
        print ('in app.ajax_POST_timeout: patient: %s; session: %s', patient, session)

        return {'status': 'OK'}


def callresend(router, **kwargs):
    from datetime import datetime
    
    app = router.get_app('taskmanager')
    assert (app.router==router)
    
    app.debug('found app/taskmanager:%s', app)
    app.debug('%s', datetime.now())
    app.debug('router: %s; received: kwargs:%s' % (router, kwargs))

### need to delete last event from the db:
    # look up by kwargs and if now > insert timestamp...    
    app.resend(kwargs['msgid'], kwargs['identity'])
