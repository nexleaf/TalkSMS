import sys, json, re
from datetime import datetime, timedelta

import rapidsms
from rapidsms.contrib.scheduler.models import EventSchedule, ALL

import tasks.sms as sms
import tasks.appointment_request
import tasks.appointment_reminder
import tasks.appointment_followup

from taskmanager.models import *
from taskmanager.tasks.models import SerializedTasks

class App(rapidsms.apps.base.AppBase):

    def start(self):
        self.counter = 0

        # keep until persistence is implemented
        self.smsusers = []
        # since we're just starting, any existing sessions must be complete
        Session.objects.filter(completed=False).update(completed=True, completed_date=datetime.now(), state='router_restarted')

        # initialize and start TalkSMS
        self.tm = sms.TaskManager(self)
        self.tm.run()
        self.debug('app.Taskmanager start time: %s', datetime.now())

        # restore serialized tasks, if any
        self.system_restore()
        self.debug('app.Taskmanager finished system_restore(), time: %s', datetime.now())


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


    def resend(self, msgid=None, identity=None):
        self.debug('in App.resend():')        
        sm = self.findstatemachine(msgid, identity)

        if sm and not sm.done:
            assert(isinstance(sm, sms.StateMachine)==True)
            assert(sm.msgid==msgid)

            self.debug('statemachine: %s; currentnode: %s; statemachine.node.sentcount: %s', sm, sm.node, sm.node.sentcount)
            # if we're still waiting for a response, send a reminder and update sentcount
            #if (sm.node.sentcount < sms.StateMachine.MAXSENTCOUNT):
            #    self.debug('sm.node.sentcount incremented to: %s', sm.node.sentcount)                
            sm.kick()
            self.tm.send(sm)
        else:
            self.debug('statemachine has incr to a new node or is done, no need to send a response reminder')


    # schedules reminder to respond messages
    def schedule_response_reminders(self, d):
        self.debug('in App.schedulecallback(): self.router: %s', self.router)
        cb = d.pop('callback')
        m = d.pop('minutes')
        reps = d.pop('repetitions')
        self.debug('callback:%s; minutes:%s; repetitions:%s; kwargs:%s',cb,m,reps,d)
        
        t = datetime.now()
        s = timedelta(minutes=m)
    
        # for n in [(t + 1*s), (t + 2*s), ... (t + r+s)], where r goes from [1, reps+1)
        for st in [t + r*s for r in range(1,reps+1)]:
            self.debug('scheduling a reminder to fire after %s', st)
            schedule = EventSchedule(callback=cb, minutes=ALL, callback_kwargs=d, start_time=st, count=1)
            schedule.save()               
                      

    # support cens gui
    def log_message(self, session_id, message, outgoing):
        session = Session.objects.get(pk=session_id)
        nm = SessionMessage(
            session = session,
            message=message,
            outgoing=outgoing
            )
        nm.save()


    def findstatemachine(self, msgid, identity):
        self.debug('in App.findstatemachine(): msgid:%s, identity: %s', msgid, identity)

        cl = []
        statemachine = None

        for sm in self.tm.uism:
            if sm.done:
                self.tm.scrub(sm)
            else:
                if (sm.msgid == msgid) and (sm.user.identity == identity):
                    self.debug('found candidate: %s', sm)
                    cl.append(sm)
                
        if len(cl) > 1:
            self.error('found more than one statemachine, candidate list: %s', cl)
        elif len(cl) == 0:
            self.debug('found no matching statemachine, candidate list: %s', cl)
        else:
            assert(len(cl)==1)
            self.debug('found unique statemachine: %s', cl[0])
            statemachine = cl[0]

        return statemachine
        
                                        
    def ajax_GET_status(self, getargs, postargs=None):
        # gutted, it's not used
        return {'status':'OK'}


    def session_updatestate(self, session_id, state):
        self.debug('in app.session_updatestate():')
        session = Session.objects.get(pk=session_id)
        translate = { 'SEND_MESSAGE'     : 'sending message',
                      'WAIT_FOR_RESPONSE': 'waiting for response',
                      'HANDLE_RESPONSE'  : 'processing response',
                      'EXIT'             : 'done' }
        session.state = translate[state]
        session.save()
        

    def session_close(self, session_id):
        # the statemachine is done, mark session closed
        session = Session.objects.get(pk=session_id)        
        session.completed_date = datetime.now()
        session.completed = True
        self.debug('in app.session_close():')
        session.save()


    def finduser(self, identity=None, firstname=None, lastname=None):
        self.debug('in App.finduser(): identity: %s, firstname: %s, lastname: %s', identity, firstname, lastname)
        
        # will eventually be a db lookup
        for a in self.smsusers:
            if identity in a.identity:
                self.debug('returning existing smsuser: %s', a)
                return a

        # talksms doesn't yet know of this user, create one.
        try:

            self.debug('attempting to create a new smsuser')
            b = sms.User(identity=identity, firstname=firstname, lastname=lastname)
            self.smsusers.append(b)

        except Exception as e:

            b = None
            self.error('Could not create user using identity: %s; Exception: %s', identity, e)
            
        self.debug('returning new smsuser: %s', b)
        return b


    def ajax_POST_exec(self, getargs, postargs=None):
        task = Task.objects.get(pk=postargs['task'])
        patient = Patient.objects.get(pk=postargs['patient'])
        args = eval(json.loads(postargs['arguments']))
        
        if 'process' in postargs:
            process = Process.objects.get(pk=postargs['process'])
        else:
            process = None

        self.debug('in app.ajax_POST_exec(): found process: %s', process)
        
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

        print '%s: dir(t): %s' % (20*'#', dir(t))
        print '%s: inspect.getmemebers(t): %s' % (20*'#', inspect.getmembers(t))

        # create a new session in db (sessions are only killed when statemachines are done)
        session = Session(patient=patient, task=task, process=process, state='initializing')
        session.save()
        # create a new SerializedTask ...
        # st = SerializedTask()
        # hmm...maybe i want SerializedTask in the main db.
        # it would be nice to access session, instead of replicating it in a completely different db.

        # create and start task
        sm = sms.StateMachine(self, smsuser, t.interaction, session.id)
        self.tm.addstatemachines(sm)
        self.tm.run()
        
        return {'status': 'OK'}



    def system_restore(self, *args, **kwargs):
        # find things prev stored: task, <user>, args, and where we left off (currentnode)..?.
        serializedtasks = SerializedTasks.objects.all()
        
        for st in serializedtasks:
            # ____:instantiate task(<user>, args) as in ajax_POST_exec():
            
            smsuser = self.finduser(patient.address, patient.first_name, patient.last_name)
            __import__(task.module, globals(), locals(), [task.className])   
            module = '%s.%s' % (task.module, task.className)
            print module
            print type(module)
            if not args:
                t = eval(module)(smsuser)
            else:
                t = eval(module)(smsuser, args)


            session = Session(patient=patient, task=task, process=process, state='initializing')
            session.save()

            sm = sms.StateMachine(self, smsuser, t.interaction, session.id)
            # reset to where it was (call sync()) which restores: msgid, currentnode(using unique label), sentcount...
            # sm.restore() OR
            for each object in t:
                object.restore()
                #how do i get the list of objects? use inspect, dir()...details?
                    
            # <start up>: return not-done sm to TaskManager.uism.
            self.tm.addstatemachines(sm)
            # ____
        
        
        #___
        # details: what's the expected msgid?
        

    def sync():
        # calls .restore() for each sms object sent 

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

    # rapidsms.contrib.scheduler marks each entry with EventSchedule.active=0 after it's fired.
    app.resend(kwargs['msgid'], kwargs['identity'])
