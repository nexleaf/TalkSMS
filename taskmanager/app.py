import rapidsms
import sys, json, re

from taskmanager.models import *
from datetime import datetime

class App(rapidsms.app.App):
    def start(self):
        # maps patients to their state machines -- indexed for now
        self.dispatch = {}
        # holds references to dynamically loaded machine classes
        self.machines = {}

        # since we're just starting, any existing sessions must be complete
        Session.objects.filter(completed=False).update(completed=True, completed_date=datetime.now(), state='router_restarted')

        # also load up all the different kinds of state machines
        tasks = Task.objects.all()

        for task in tasks:
            curModule = __import__(task.module, globals(), locals(), [task.className])
            self.machines[task.id] = curModule.__dict__[task.className]
        
    def handle(self, message):
        self.debug("got message %s", message.text)

        # we found a patient; let them handle the message
        if message.peer in self.dispatch:
            result = self.dispatch[message.peer].handle(message)

            # look up our Session to either update or remove it depending on the result
            session = self.dispatch[message.peer].session
            
            # if the result is None, consider it handled and deattach this machine
            if result == None:
                # mark session as completed
                session.completed_date = datetime.now()
                session.completed = True
                session.save()
                # also delete the machine instance itself from our dispatch
                del self.dispatch[message.peer]
                return True
            else:
                # set the Session's state to reflect the machine's internal state
                try:
                    session.state = self.dispatch[message.peer].get_state()
                except:
                    session.state = sys.exc_info()[0] # we can't set the state because we don't know it :|
                session.save()
                return result

        # it's not for a subscribed patient, so we can't handle it
        return False

    def ajax_GET_status(self, getargs, postargs=None):
        instances = []
        for machine in self.dispatch:
            # only serialize the db objects
            instances.append({
                'session': machine.session,
                'patient': machine.patient,
                'args': machine.args,
                'state': machine.state
                })
            
        return instances

    def ajax_POST_exec(self, getargs, postargs=None):
        task = Task.objects.get(pk=postargs['task'])
        patient = Patient.objects.get(pk=postargs['patient'])
        args = json.loads(postargs['arguments'])

        if 'process' in postargs:
            process = Process.objects.get(pk=postargs['process'])
        else:
            process = None

        # === first of all, check if the patient already has a running session
        # === if they do, end it before we proceed
        if patient.address in self.dispatch:
            # get the session from the dispatch table
            session = self.dispatch[patient.address].session
            # mark session as completed
            session.completed_date = datetime.now()
            session.completed = True
            session.state = 'preempted' # mark it as having been preempted
            session.save()
            # also delete the machine instance itself from our dispatch
            del self.dispatch[patient.address]

        # === at this point, we're sure that the patient has no running session

        # create a new Session in the db to manage this machine instance
        session = Session(patient=patient, task=task, process=process, state='unknown')
        session.save()
        
        # attempt to create a state machine for the given task
        self.dispatch[patient.address] = self.machines[task.id](session, self.router, patient, args)
        # run the start event on the machine (which may put us in a terminal or nonterminal state)
        result = self.dispatch[patient.address].start()
        session.state = self.dispatch[patient.address].get_state()

        # check if the machine completed immediately (e.g. it doesn't wait for input)
        if result == None:
            # mark session as completed
            session.completed_date = datetime.now()
            session.completed = True
            # remove from dispatch table
            del self.dispatch[patient.address]

        # save the session regardless of what happens
        session.save()
            
        # since we haven't returned yet, it must mean we're good
        return {'status': 'OK'}

    def ajax_POST_timeout(self, getargs, postargs=None):
        patient = Patient.objects.get(pk=postargs['patient'])
        session = Session.objects.get(pk=postargs['session'])

        # determine if we have a running instance of this session
        if patient.address not in self.dispatch:
            return {'error': 'PATIENT NOT FOUND'}

        # now check if the current session for this patient is indeed this session
        if self.dispatch[patient.address].session.id != session.id:
            return {'error': 'SESSION NOT FOUND'}

        # ok, we've verified that we have a running session of this machine
        # let's send it a timeout message and see what happens
        result = self.dispatch[patient.address].timeout()
        session.state = self.dispatch[patient.address].get_state()

        # check if the machine wants to exit
        if result == None:
            # mark session as completed
            session.completed_date = datetime.now()
            session.completed = True
            session.state = 'exited_on_timeout' # mark it as having timed out
            # remove from dispatch table
            del self.dispatch[patient.address]
        elif result == True:
            # clear the timeout, at least, since we've handled it
            # but allow the machine to continue running
            session.timeout_date = None

        # save the session regardless of what happens
        session.save()

        # since we haven't returned yet, it must mean we're good
        return {'status': 'OK'}
