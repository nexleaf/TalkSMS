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
        # keep until persistence is implemented
        self.smsusers = []

        # initialize TalkSMS
        self.tm = sms.TaskManager(self)
        self.debug('app.Taskmanager init time: %s', datetime.now())

        # restore serialized tasks, if any        
        self.system_restore()
        self.debug('app.Taskmanager finished system_restore(), time: %s', datetime.now())

        # start TalkSMS
        self.tm.run()
        self.debug('app.Taskmanager start time: %s', datetime.now())


    def handle (self, message):
        self.debug('in App.handle(): message type: %s, message.text: %s', type(message),  message.text)
        response = self.tm.recv(message)
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

        # create task t
        if not args:
            t = eval(module)(smsuser)
        else:
            t = eval(module)(smsuser, args)

        # create a new session in db (sessions are only killed when statemachines are done)
        session = Session(patient=patient, task=task, process=process, state='initializing')
        session.save()

        # create and start task
        sm = sms.StateMachine(self, smsuser, t, session.id)

        # create and save initial state of this new task as SerializedTask
        d = {'t_args' : postargs['arguments'],
             't_pblob' : sm.task.save(),
             's_app' : self,
             's_session_id' : session.id,
             's_msgid' : sm.msgid,
             's_done' : sm.done,
             's_node' : sm.node.label,
             's_event' : sm.event,
             's_mbox' : sm.mbox if sm.mbox else '',
             'm_sentcount' : sm.node.sentcount,
             'i_initialnode' : sm.task.interaction.initialnode.label,
             'u_nextmsgid' : smsuser.msgid.peek() }
        st = SerializedTasks(**d)
        st.save()        

        self.tm.addstatemachines(sm)
        self.tm.run()
        
        return {'status': 'OK'}


    def savetask(self, s_session_id, **kwargs):
        self.debug('in App.savetask(): session id: %s, ' )
        # cols from task_serializedtasks
        keys = ['t_args', 't_plob', 's_msgid', 's_done', 's_node', 's_event', 's_mbox', 'm_sentcount', 'i_initialnode', 'u_nextmsgid']

        # what happens when there is more than one match here?
        # .get() raises an exection if there is more than one match
        st = SerializedTasks.objects.get(pk=s_session_id)
        self.debug('cur st: %s', st)

        for k in keys:
            if k in kwargs:
                # if kwargs['s_mbox'] == None:
                if (k is 's_mbox') and (not kwargs[k]):
                    # st.s_mbox = ''
                    object.__setattr__(st, k, '')
                else:
                    # st.k = kwargs[k]
                    object.__setattr__(st, k, kwargs[k]) 
        
        st.save()
        
        self.debug('new st: %s', st)


    def system_restore(self, *args, **kwargs):

        self.debug('in App.system_restore():')
        
        # find live tasks
        # sts = SerializedTasks.objects.filter(s_done=False)
        
        # return all saved task
        sts = SerializedTasks.objects.all()

        for st in sts:
            session = Session.objects.filter(pk=st.s_session_id)
            # many sm's for each session so, there will always be one session.
            assert(len(session)==1)

            self.debug('found matching sessions: %s', session[0])
            self.debug('found session: ')
            self.debug('id:             %s', session[0].id)
            self.debug('patient_id:     %s', session[0].patient_id)
            self.debug('task_id:        %s', session[0].task_id)
            self.debug('process_id:     %s', session[0].process_id)
            self.debug('add_date:       %s', session[0].add_date)
            self.debug('completed:      %s', session[0].completed)
            self.debug('completed_date: %s', session[0].completed_date)
            self.debug('timeout_date:   %s', session[0].timeout_date)
            self.debug('state:          %s', session[0].state)
            
            # find or create smsuser
            patient = Patient.objects.get(pk=session[0].patient_id)
            smsuser = self.finduser(patient.address, patient.first_name, patient.last_name)
            # need to be careful about setting the users's msgid...
            smsuser.msgid.reset(st.s_msgid-1)

            self.debug('resetting user.msgid: %s', st.s_msgid-1)

            # make sure smsusers in memory are reset to their last state
            if st.s_done:
                self.debug('\n\npassing restore of dead st: %s', st)
                # if there is no live statemachine, we want to restore user to the state it was after this sm was created.
                # (helps when there are no live statemachines at restore)
                self.debug('increment user id %s from: %s to: %s', smsuser.identity, smsuser.msgid.count, smsuser.msgid.next())
                continue

            self.debug('\n\nrestoring st: %s', st)

            # re-create task
            task = Task.objects.get(pk=session[0].task_id)
            t_args = eval(json.loads(st.t_args))
            __import__(task.module, globals(), locals(), [task.className])   
            module = '%s.%s' % (task.module, task.className)
            print module
            print type(module)
            if not t_args:
                t = eval(module)(smsuser)
            else:
                t = eval(module)(smsuser, t_args)
            # restore task state
            print 'st.t_pblob: %s' % st.t_pblob
            t.restore(st.t_pblob)
            
            # restore statemachine state, sm.msgid is incremented to st.u_nextmsgid at init
            sm = sms.StateMachine(self, smsuser, t, st.s_session_id)
            #sm.msgid = st.s_msgid
            #assert(smsuser.msgid.peek() == st.u_nextmsgid)
            self.debug('\nsm.msgid (from smsuser.msgid.count): %s\nsmsuser.msgid.peek(): %s\nst.u_nextmsgid: %s\n',
                       smsuser.msgid.count, smsuser.msgid.peek(), st.u_nextmsgid)
            sm.done = False if st.s_done==0 else True
            # find correct node in graph which matches the label we saved
            for node in sm.interaction.graph.keys():
                if node.label is st.s_node:
                    sm.node = node
            sm.node.sentcount = st.m_sentcount
            sm.event = st.s_event
            sm.mbox = None if st.s_mbox is '' else st.s_mbox
            
            # hmm, should we add a list of the new sm's to tm after the loop?
            self.tm.addstatemachines(sm)
        

    def sync():
        # calls .restore() for each sms object sent
        print 'STUB: app.sync()'

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
