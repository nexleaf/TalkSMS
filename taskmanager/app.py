import sys, json, re
from datetime import datetime, timedelta

import rapidsms
import rapidsms.contrib.scheduler.app as sched
from rapidsms.contrib.scheduler.models import EventSchedule, ALL

import tasks.sms as sms

from taskmanager.models import *


class App(rapidsms.apps.base.AppBase):
    def start(self):
        # maps patients to their state machines -- indexed for now
        # self.dispatch = {}
        # holds references to dynamically loaded machine classes
        # self.machines = {}

        # list of tasks, or sms.statemachines
        self.tasklist = []

        # keep until persistence is implemented
        # since we're just starting, any existing sessions must be complete
        Session.objects.filter(completed=False).update(completed=True, completed_date=datetime.now(), state='router_restarted')

        # instead of importing tasks we allow the admin to define tasks through the interface.
        # replaces:
        # import tasks.appointment_request
        # import tasks.appointment_reminder
        # import tasks.appointment_followup
        tasks = Task.objects.all()
        self.debug('Task.objects.all(): %s', tasks)        

        # for task in tasks:
        #     curModule = __import__(task.module, globals(), locals(), [task.className])
        #     self.debug('__import__(task.module, globals(), locals(), [task.className]): %s',curModule)
        #     self.machines[task.id] = curModule.__dict__[task.className]
        #     self.debug('curModule.__dict__[task.className]: %s', curModule.__dict__[task.className])

        # initialize and start TalkSMS
        self.tm = sms.TaskManager(self)
        self.tm.run()
        self.debug('app.Taskmanager start time: %s', datetime.now())
        
##### DONE
    # def handle(self, message):
    #     self.debug("got message %s", message.text)

    #     # we found a patient; let them handle the message
    #     if message.peer in self.dispatch:
    #         result = self.dispatch[message.peer].handle(message)

    #         # look up our Session to either update or remove it depending on the result
    #         session = self.dispatch[message.peer].session
            
    #         # if the result is None, consider it handled and deattach this machine
    #         if result == None:
    #             # mark session as completed
    #             session.completed_date = datetime.now()
    #             session.completed = True
    #             session.save()
    #             # also delete the machine instance itself from our dispatch
    #             del self.dispatch[message.peer]
    #             return True
    #         else:
    #             # set the Session's state to reflect the machine's internal state
    #             try:
    #                 session.state = self.dispatch[message.peer].get_state()
    #             except:
    #                 session.state = sys.exc_info()[0] # we can't set the state because we don't know it :|
    #             session.save()
    #             return result

    #     # it's not for a subscribed patient, so we can't handle it
    #     return False

    def handle (self, message):
        self.debug('in App.handle(): message type: %s, message.text: %s', type(message),  message.text)
        response = self.tm.recv(message)
        self.debug("message.subject: %s; responding: %s", message.subject, response)
        message.respond(response)


    def send(self, ident, s):
        self.debug('in App.send():')
        try:
            from rapidsms.models import Backend 
            bkend, createdbkend = Backend.objects.get_or_create(name="email")        
            conn, createdconn = rapidsms.models.Connection.objects.get_or_create(backend=bkend, identity=ident)
            message = rapidsms.messages.outgoing.OutgoingMessage(conn, s)
            # email just for testing now, removing subject allows easy msg generalization 
            # message.subject='testing '+ str(self.__class__)
            if message.send():
                self.debug('sent message.text: %s', s)
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
                sm.node.sentcount += 1
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
        for statemachine in self.tasklist:
            # only serialize the db objects
            instances.append({
                'session': statemachine.session,
                'patient': Patient.objects.get(address=statemachine.user.identity),
                'args': json.loads('{"argstub":"0"}'),
                'state': statemachine.event
                })
        return instances

##### DONE?
    # def ajax_POST_exec(self, getargs, postargs=None):
    #     task = Task.objects.get(pk=postargs['task'])
    #     patient = Patient.objects.get(pk=postargs['patient'])
    #     args = json.loads(postargs['arguments'])

    #     if 'process' in postargs:
    #         process = Process.objects.get(pk=postargs['process'])
    #     else:
    #         process = None

    #     # === first of all, check if the patient already has a running session
    #     # === if they do, end it before we proceed
    #     if patient.address in self.dispatch:
    #         # get the session from the dispatch table
    #         session = self.dispatch[patient.address].session
    #         # mark session as completed
    #         session.completed_date = datetime.now()
    #         session.completed = True
    #         session.state = 'preempted' # mark it as having been preempted
    #         session.save()
    #         # also delete the machine instance itself from our dispatch
    #         del self.dispatch[patient.address]

    #     # === at this point, we're sure that the patient has no running session

    #     # create a new Session in the db to manage this machine instance
    #     session = Session(patient=patient, task=task, process=process, state='unknown')
    #     session.save()
        
    #     # attempt to create a state machine for the given task
    #     self.dispatch[patient.address] = self.machines[task.id](session, self.router, patient, args)
    #     # run the start event on the machine (which may put us in a terminal or nonterminal state)
    #     result = self.dispatch[patient.address].start()
    #     session.state = self.dispatch[patient.address].get_state()

    #     # check if the machine completed immediately (e.g. it doesn't wait for input)
    #     if result == None:
    #         # mark session as completed
    #         session.completed_date = datetime.now()
    #         session.completed = True
    #         # remove from dispatch table
    #         del self.dispatch[patient.address]

    #     # save the session regardless of what happens
    #     session.save()
            
    #     # since we haven't returned yet, it must mean we're good
    #     return {'status': 'OK'}

    def session_updatestate(self, session_id, state):
        session = Session.objects.get(pk=session_id)
        session.state = state
        session.save()

    def session_close(self, session_id):
        # the statemachine is done, mark session closed
        session = Session.objects.get(pk=session_id)        
        session.completed_date = datetime.now()
        session.completed = True
        session.state = 'preempted'
        session.save()

    def ajax_POST_exec(self, getargs, postargs=None):
        self.debug("in app.ajax_POST_exec:")
        task = Task.objects.get(pk=postargs['task'])
        patient = Patient.objects.get(pk=postargs['patient'])
        args = json.loads(postargs['arguments'])
        if 'process' in postargs:
            process = Process.objects.get(pk=postargs['process'])
        else:
            process = None
        
        print 'printing args: %s; type: %s' % (args, type(args))

        # returns existing user, otherwise returns a new user 
        smsuser = self.finduser(patient.address, patient.first_name, patient.last_name)

        tasks = Task.objects.all()
        for task in tasks:
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
        self.tasklist.append(t)
        sm = sms.StateMachine(self, smsuser, t.interaction, session.id)
        self.tm.addstatemachines(sm)
        self.tm.run()

        # save the session regardless of what happens
        session.save()
        
        return {'status': 'OK'}


    def ajax_POST_timeout(self, getargs, postargs=None):
        patient = Patient.objects.get(pk=postargs['patient'])
        session = Session.objects.get(pk=postargs['session'])

    #     # determine if we have a running instance of this session
    #     if patient.address not in self.dispatch:
    #         return {'error': 'PATIENT NOT FOUND'}

    #     # now check if the current session for this patient is indeed this session
    #     if self.dispatch[patient.address].session.id != session.id:
    #         return {'error': 'SESSION NOT FOUND'}

    #     # ok, we've verified that we have a running session of this machine
    #     # let's send it a timeout message and see what happens
    #     result = self.dispatch[patient.address].timeout()
    #     session.state = self.dispatch[patient.address].get_state()

    #     # check if the machine wants to exit
    #     if result == None:
    #         # mark session as completed
    #         session.completed_date = datetime.now()
    #         session.completed = True
    #         session.state = 'exited_on_timeout' # mark it as having timed out
    #         # remove from dispatch table
    #         del self.dispatch[patient.address]
    #     elif result == True:
    #         # clear the timeout, at least, since we've handled it
    #         # but allow the machine to continue running
    #         session.timeout_date = None

    #     # save the session regardless of what happens
    #     session.save()

    #     # since we haven't returned yet, it must mean we're good
        return {'status': 'ajax_POST_timeout_STUB'}


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
