# sms.py: TalkSMS library

import sys, json, re, traceback, string
from collections import deque
import itertools
from taskmanager.models import *

class Response(object):

    def __init__(self, text, match_regex=None, match_callback=None, label='', callback=None, *args, **kwargs):
        if match_regex is None and match_callback is None:
            raise ValueError('Response.match_regex OR Response.match_callback must be set')
        self.match_callback = None
        self.match_regex = None

        if match_callback is not None:
            if not match_callback(text):
                raise ValueError('Respones.match_vallback must not return None or False for Response.text')
            self.match_callback = match_callback

        if match_regex is not None:
            if not re.compile(match_regex, re.I).match(text):
                raise ValueError('Response.match_regex must re.match() Response.text')
            
            self.match_regex = re.compile(match_regex, re.I)

        self.text = text

        if not label:
            raise ValueError('Response requires a unique label string.')
        self.label = label
        
        if callback:
            self.callback = callback
            self.args = args
            self.kwargs = kwargs
        else:
            self.callback = None
                
    
    def match(self, sometext):
        'return None if there is no match, and the MatchObject otherwise'
        if self.match_callback is not None:
            return self.match_callback(sometext)
        if self.match_regex is not None:
            return self.match_regex.match(sometext)
        raise UnboundLocalError('No match regex or callback set.')

    def __str__(self):
        return '%s:%s' % (self.__class__.__name__, (self.label if self.label else repr(self) ))


class Message(object):
    # timeout in mins
    DEFAULT_TIMEOUT = 30
    # retries
    DEFAULT_RETRIES = 2
    
    def __init__(self, question, responselist=[], retries=None, timeout=None, do_not_send=False, \
                 custom_message_callback=None, no_match_callback=None, label=''):
        self.question = question
        self.responselist = responselist
        if retries == None:
            self.retries = self.DEFAULT_RETRIES
        else:
            # TODO: sanity check
            self.retries = retries
        if timeout == None:
            self.timeout = self.DEFAULT_TIMEOUT
        else:
            # TODO: sanity check
            self.timeout = timeout

        # error handling callback so we can deal with providin
        self.no_match_callback = no_match_callback

        # called during build_send_str
        self.custom_message_callback = custom_message_callback

        # used for leaf nodes where we do not want to send a repsonse
        self.do_not_send = do_not_send

        self.sentcount = 0
        
        if not label:
            raise ValueError('Response requires a unique tasknamespace identifier.')
        self.label = label
        
    
    def __str__(self):
        return '%s:%s %s' % ( self.__class__.__name__, \
                             (self.label if self.label else repr(self)), \
                             [str(r) for r in self.responselist] )


class Interaction(object):

    def __init__(self, graph, initialnode, label=''):

        Interaction.isvalid(graph, initialnode)

        if label:
            self.label = self.__class__.__name__
        else:
            self.label = label
        if not label:
            raise ValueError('Response requires a unique label string.')
        self.label = label
            
        self.initialnode = initialnode
        self.graph = graph

    def mapsTo(self, m, r):
        """
        say i is an Interaction with graph g.
        then m,m1 are Messages, m->m1 is an edge, and r is
        the transition mapping m to m1 in g.
        then i.mapsTo(m,r) returns m1
        """
        if not isinstance(m, Message):
            raise TypeError ('%s in not Message type' % (str(m)))
        if not isinstance(r, Response):
            raise TypeError ('%s is not Response type' % (str(m)))
        if not r in m.responselist:
            raise ValueError ('Response %s is not in %s responslist' % (str(r),str(m)))
        if not m in self.graph.keys():
            raise ValueError ('%s is not a key in this Interaction graph.' % (str(m)))
        
        return self.graph[m][m.responselist.index(r)]

    @classmethod
    def isvalid(cls, graph, initialnode):
        # check that each msg node has the same number of responses as children
        for msg in graph.keys():
            if not len(graph[msg]) == len(msg.responselist):
                raise ValueError("bad mapping.")
        # check initialnode is in interaction graph
        if not initialnode in graph:
            raise ValueError("missing initial message node in interaction graph.")
        # TODO: check ensure no cycles in interaction graph


    def __str__(self):
        'returns a bfs of the graph.'
        s = '\t'
        q = deque()
        string = ''
        q.append( (self.initialnode, 0) )
        while q:
            cn,n = q.popleft()
            string += s*n + ( cn.label if cn.label else str(cn) )  + ' : \n'
            for r,m in zip(cn.responselist, self.graph[cn]):
                string += s*n + ( r.label if r.label else str(r) ) + ' -> ' \
                              + ( m.label if m.label else str(m) ) + '\n'
                if m.responselist:
                    q.append( (m, n+1) )
            string += '\n'
        string += ('.' if not q else str(q)) 
        return string


class Cycle(object):
    # cyclic counter supporting the same interface as itertools.cycle() while using much less memory for large max's

    def __init__(self, max):
        self.max = max
        self.__c = -1

    def reset(self, r):
        # if (0 <= reset < max+1)
        if r in range(0,self.max+1):
            self.__c = r
        else:
            # return 0 first time next() or peek() is called.
            self.__c = -1
            
    @property
    def count(self):
        return self.__c

    def next(self):
        if self.__c < self.max:
            self.__c = self.__c + 1
        else:
            self.__c = 0
        return self.__c
    
    def peek(self):
        if self.__c < self.max:
            return self.__c + 1
        else:
            return 0
        

class User(object):

    MAXMSGID = 99
    
    def __init__(self, identity=None, firstname=None, lastname=None, label=None):

        # identity/identityType corresponds to backends defined in settings.py

        if identity is None:
            raise ValueError("Phone number or email required.")
        elif re.match(r'.+@.+', identity):
            self.identity = identity
            self.identityType = 'email'
        elif re.match(r'^\+\d+', identity):
            self.identity = identity
            self.identityType = 'phone'
        else:
            raise ValueError("Unknown identity type.")

        self.firstname = firstname
        self.lastname = lastname

        if label is None:
            self.label = self.__class__.__name__
        else:
            self.label = label

        # user.msgid.next() get's the next msgid
        #self.msgid = Cycle(User.MAXMSGID)

    @property
    def username(self):
        return self.firstname + ' ' + self.lastname
        

class StateMachine(object):
      """
      StateMachine keeps track of the flow through an Interaction graph.
      """
      # max number of times a message is sent when expecting a reply
      #MAXSENTCOUNT = 3
      # time to resend a message in minutes

      #TIMEOUT = 10
      
      def __init__(self, app, user, task, session_id, label=''):
          self.app = app
          self.log = app
          
          # support cens gui
          self.session_id = session_id
          
          self.task = task
          self.interaction = task.interaction
          self.user = user
          self.label = label
          
          #self.msgid = self.user.msgid.next()
          self.tasknamespace_override = task.tasknamespace_override
          self.tnsid = self.interaction.initialnode.label

          self.done = False
          
          self.last_response = ''
          
          # current node in the interaction graph
          self.node = self.interaction.initialnode
          

      def finish(self):
          """done. tell taskmanager to move me from the live list to the dead list..."""
          self.log.debug('in StateMachine.finish()')
          self.done = True
          # support cens gui
          self.app.session_close(self.session_id)


      def schedule_retry(self):
          self.log.debug('in StateMachine.schedule_retry. self.tnsid: %s', self.tnsid)
          if self.node.timeout == 0:
              # this is the 'just send an bail case', we set a timeout anyway so we can cleanup the sm
              self.node.timeout = self.node.DEFAULT_TIMEOUT
          
          # We increment this here... because... ???
          self.node.sentcount += 1
          
          # TODO
          # TODO: Convert as args isntead of dictionary and call taskscheduler.schedule_timeout() (callbacks will come through ajax_POST_timeout)
          # TODO
          # TODO: call Faisals scheduler through the taskscheduler.schedule_timeout()
          # TODO
          d = {'callback':'taskmanager.app.callresend',
               'minutes':self.node.timeout,
               'repetitions':self.node.retries,
               #'msgid':self.msgid,
               'tnsid': self.tnsid,
               'identity':self.user.identity }        
          self.app.schedule_response_reminder(d)


      def clear_retry(self):
          # called when we want any timeouts associated with this machine to be deactivated.
          # This should be called every time we get a message in that matches this state machine
          # so we do not have stale timeouts firing when we do not need them
          self.log.debug('in StateMachine.clear_retry. self.tnsid: %s', self.tnsid)
          self.app.clear_response_reminder(self.tnsid, self.user.identity)      
      
      def setup_retry_finish_fail(self, no_decrement_retry=False):
          self.log.debug('in StateMachine.setup_retry_finish_fail. self.tnsid: %s', self.tnsid)
          self.log.debug('self.node: %s, self.node.retries: %s' % ( str(self.node), self.node.retries ))

          self.clear_retry() # anything stale in the DB? setup a new schedule
          #
          # TODO: make retcode here some actual static vars or inner class here instead of string
          #
          retcode = 'fail'
          # when we are done, we may still want to send a message, so must return 'finish'. The
          # do_not_send varriable will setup things so there is no final response
          if not self.node.responselist:
              self.finish()
              return 'finish'
          
          # LOGIC:
          # If the message has never been set (sentcount == 0)
          #    if retries == 0:
          #1       if timeout == 0:
          #          should send the message once! This is a 'just send the message and bail'
          #          to handle this case, we set a timeout anyway so this sm can 'finish'
          #2       if timeout > 0:
          #          schedule_response_reminder()
          #    if retries > 0:
          #3       if timeout == 0:
          #          ERROR CASE! Should not happen, does not make sense
          #4       if timeout > 0:
          #          schedule_response_reminder()
          # If the message has been sent (sentcount > 0)
          #5    if retries == 0:
          #       finish()                              ***
          #    if retries > 0:
          #6       if timeout == 0:
          #          ERROR CASE! Should not happen, does not make sense
          #7       if timeout > 0:
          #          scheduler_response_reminder()

          # LOGIC REDUCES TO:
          # always set timeout, even if 0.
          # sentcount == 0
          #    send a message no matter what
          # sentcount > 0
          #    send a message is retries > 0

          # CASE 1, 2, 3, 4
          if self.node.sentcount == 0:
              self.schedule_retry()
              self.log.debug('Sending message without expecging any respones! tnsid: %s' % (self.tnsid))
              retcode = 'retry'
          else: # self.node.sentcount > 0
              # CASE 5
              if self.node.retries == 0:
                  self.finish()
                  self.log.debug('finished, sentcount %d, retries 0, self.tnsid: %s', self.node.sentcount, self.tnsid)
                  retcode = 'fail'
              # CASE 6 and 7
              else: # retries in > 0
                  self.schedule_retry()
                  self.log.debug('decremented self.node.retries: %s; self.tnsid: %s', self.node.retries, self.tnsid)
                  retcode = 'retry'

          # only start decrementing after the first full try
          if self.node.retries > 0 and self.node.sentcount > 1 and no_decrement_retry is False:
              self.node.retries = self.node.retries - 1
          return retcode
      
      def handle_timeout(self):
          # we run self.setup_retry_or_finish() to see if there are any retries left
          self.clear_retry()
          self.setup_retry_finish_fail()
      
      def handle_message(self, message):
          # Process the input.
          # If something matched we advanced to the next node.
          # If nothing matched we ask for a retry with the retcode and provide an optional error response

          self.log.debug('in StateMachine.handle_message(): handling message %s' % (message))
                    
          assert(message is not None)
          self.last_response = message
          rnew = message

          # If we set a custom error message or a custom response, we set this var.
          # Return this always. higher up code checks for None otherwise uses it as response.
          retstring = None
          retcode = "ok"
          #
          # TODO: make retcode be some actul static variable instead of strings
          #
          
          # check if the new response matches anything in the response list.
          # Current policy is to accept the first match and move on.
          # If we reached this point, there should always be something in repsonselist because
          # we would have called finish() on the message we got previously
          matchidx = -1
          for i in range(len(self.node.responselist)):
              matchres = self.node.responselist[i].match(rnew)
              self.log.debug('tried match, got %s', matchres)
              if matchres is not False and matchres is not None:
                  matchidx = i
                  break
          
          self.log.debug('found match at idx %s (if -1, no match)', matchidx)

          # clear any scheduled reminders so we do not get callbacks
          self.clear_retry()
          if matchidx >= 0:

              self.log.debug('found response match')
              response = self.node.responselist[matchidx]
 
              # advance to the next node
              self.node = self.interaction.mapsTo(self.node, response)
              self.log.debug('advanced current node to: %s', self.node)
              
              ##
              ## This is where we determine what the next expected tasknamespace string is
              ##
              if self.tasknamespace_override is not None:
                  self.tnsid = self.tasknamespace_override
              else:
                  self.tnsid = self.node.label

              # call response obj's developer defined callback
              if response.callback is not None:
                  self.log.debug('calling %s callback', response)
                  # Sendv back rnew, session_id
                  response.kwargs['response'] = rnew
                  response.kwargs['session_id'] = self.session_id
                  result = response.callback(*response.args, **response.kwargs)
                  self.log.debug('callback result: %s', result)                  
              
          else: #matchidx == -1
              # no match, so call custom error callback, otherwise code will
              self.log.debug('response did not match expected list of responses OR we are done')
              if self.node.no_match_callback is not None:
                  self.log.debug('calling custom error callback %s', self.node)
                  retstring = self.node.no_match_callback(node=self.node, response=rnew, session_id=self.session_id)
                  self.log.debug('got response string %s', retstring)
              retcode = "retry"
                  
          return (retstring, retcode)
          #self.setup_retry_or_finish() # now called from tm

class TaskManager(object):
    """
    TM holds a list of all statemachines, and manages messages to them.
    TM also interacts with the Scheduler to post/get user; task; arguments, in order to schedule start of
    future interactions. (tasks are statemachines....)
    """

    TRYS = 3
    
    def __init__(self, app):
        self.app = app
        self.log = app

        self.log.debug('in TaskManager.run(): Talk App: %s' % self.app)

        self.numbers = re.compile('^\d+')
        self.badmsgs = {}

        # maintain a list of all statemachines
        self.uism = []
        

    def addstatemachines(self, *statemachines):
        for sm in statemachines:
            if sm not in self.uism:
                self.uism.append(sm)
                self.log.debug('in TaskManager.addstatemachines(): len(self.uism): %s'  % len(self.uism))                
                assert(len(self.uism) > 0)


    def scrub_statemachines(self):
        """remove done statemachine from user's and taskmanager's lists"""

##        scrublist = []
        try:
##            for sm in self.uism:
##                if sm.done:
##                    scrublist.append(sm)
##            for sm in scrublist:
##                self.log.debug('in TaskManager.scrub_statemachines(): deleting statemachine: %s from self.uism', s,)
##                i = self.uism.index(sm)
##                self.uism.pop(i)
            self.uism = filter(lambda x: not x.done, self.uism)
        except ValueError:
            self.log.error('statemachine is not in self.uism')
            return
        except NameError:
            self.log.error('statemachine is not defined')
            return

        
    @staticmethod
    def build_send_str(node, tnsid, received_msg=None):
        print 'in TaskManager.build_send_str(): node.retries: %d, node.sentcount %d' % (node.retries, node.sentcount)

        basetext = ''
        # call the message objets developer defined custom message callback to get a string
        if node.custom_message_callback is not None:
            print 'calling custom response callback for %s' % (node.label)
            # FAISAL: added a parameter to the callback so we can get at the user's text, if it exists
            basetext = node.custom_message_callback(node, received_msg) # what else should we pass in?
            print 'got response string %s' % (basetext)
        else:
            basetext = node.question
            
        text = ''.join(basetext)

        if node.responselist:
            text += ' Type \"%s\" before your reply.' % (tnsid)
        
        return text


    def findstatemachine(self, tnsid, identity):
        self.log.debug('in tm.findstatemachine(): tnsid:%s, identity: %s', tnsid, identity)

        cl = []
        statemachine = None

        for sm in self.uism:
            self.log.debug('candidate: %s %s %s %s %s', sm, sm.tnsid, sm.node.label, sm.user.identity, sm.done)
        
        self.scrub_statemachines()
        
        for sm in self.uism:
            if sm.tnsid == tnsid and sm.user.identity == identity:
                self.log.debug('found candidate: %s', sm)
                cl.append(sm)
                
        if len(cl) > 1:
            self.log.error('found more than one statemachine, candidate list: %s', cl)
        elif len(cl) == 0:
            self.log.debug('found no matching statemachine, candidate list: %s', cl)
        else:
            assert(len(cl)==1)
            self.log.debug('found unique statemachine: %s', cl[0])
            statemachine = cl[0]

        return statemachine

    def save_curr_statemachine(self, statemachine):
        # FAISAL: FIXME: adding catch-all exception handler here so that it doesn't bring down the system, at least
        try:
            # save current state
            d = {'t_pblob' : statemachine.task.save(),
                 's_tnsid' : statemachine.tnsid,
                 's_done' : statemachine.done,
                 's_node' : statemachine.node.label,
                 's_last_response' : statemachine.last_response,
                 'm_sentcount' : statemachine.node.sentcount,
                 'm_retries' : statemachine.node.retries,
                 'm_timeout' : statemachine.node.timeout }
            self.app.savetask(statemachine.session_id, **d)
        except:
            # FAISAL: post an administrative alert, but let things continue
            # extract exception info
            cla, exc, trbk = sys.exc_info()
            excName = cla.__name__

            # post an exception alert targeting the task manager service
            alert_data = {'taskname': str(statemachine.task), 'name': excName, 'traceback': traceback.format_exc()}
            Alert.objects.add_alert("Task Save Exception", arguments=alert_data, patient=statemachine.task.patient)
    
    def send_curr_message(self, statemachine):
        # Send the current message for this state machine. Only call this on init or from timeout
        # handler (it does not happen in the tm.recv() and sm.handle_message() code paths). Must check
        # that sm.done is not ture before calling this
        #
        self.log.debug('in tm.send_curr_message()')
        
        # We set the next tasknamespace to look for in the handler that figured out what the next node was
        text = TaskManager.build_send_str(statemachine.node, statemachine.tnsid)
        self.log.debug('in TaskManager.send_curr_message(): node.retries: %i, preparing to send text: %s', statemachine.node.retries, text)
        self.app.log_message(statemachine.session_id, text, True)
        self.app.send(statemachine.user.identity, statemachine.user.identityType, text)
    
    
    def handle_timeout(self, tnsid=None, identity=None):
        self.log.debug('in tm.handle_timeout():')        
        sm = self.findstatemachine(tnsid, identity)

        #
        # TODO: Check if THIS IS BROKEN WHEN USING the tasknamespace_override feature
        # ... not sure this is broken since any outstanding scheduled reminders/retry/timeouts are cleared now
        # with clear_retry()
        #
        if sm and not sm.done:
            assert(isinstance(sm, StateMachine)==True)
            assert(sm.tnsid==tnsid)

            self.log.debug('statemachine: %s; currentnode: %s; statemachine.node.retries: %s', sm, sm.node, sm.node.retries)

            # Check is retry limit reached
            sm.handle_timeout()
            if sm.done:
                self.log.debug('done or reached retry limit, not sending anything')
            else:
                self.send_curr_message(sm)
            self.save_curr_statemachine(sm)
        else:
            self.log.debug('statemachine has incr to a new node or is done, no need to send a response reminder')
    
    
    
    def recv(self, rmessage):
        self.log.debug('in TaskManager.recv(): ')

        response = 'Command not understood.'
        message_matched = False
        
        # Always check for UIT
        # user-initiated-task? see if the message contains a keyword associated with a task
        if self.app.createdbuserandtask(rmessage):
            self.scrub_statemachines()
            response = None
            message_matched = True
        else:
            # fall-through response string
            response = 'Response not understood. Please type the message identifier before your response.'
            
            # strip off msgid and text from the repsonse

            # first, split the message into rtnsid and rtext
            parts = rmessage.text.split(None, 1)
            rtnsid = parts[0].lower() # FIXME: forcing this lower for now to see if it causes a match
            if len(parts) > 1:
                rtext = parts[1]
            else:
                rtext = "" # FIXME: there's no message, leave it blank and fix this one later
            
            # FAISAL: removed spurious assert that seems to exist solely to prevent modifications in another file
            # why is this here?
            # assert(b==rtnsid)

            # FAISAL: not sure what the below does...i imagine it gets the first line in the text
            # but why would there be multiple lines?
            # rtext = rtext.splitlines()[0].strip()

            self.log.debug('found msgid in response' +\
                           'rmsgid: \'%s\'; rtext: \'%s\'; peer: \'%s\'' % (rtnsid, rtext, rmessage.connection.identity))           

            # first, remove task if done
            self.scrub_statemachines()

            # then, find the correct statemachine
            for sm in self.uism:

                # NOTE: We probably need some types of checks here... if the developer has set the same label in various
                # tasks then we may have problems
                
                # sanity check out to log
                self.log.debug('            sm.user.identity: \'%s\',', sm.user.identity)
                self.log.debug('rmessage.connection.identity: \'%s\';', rmessage.connection.identity)
                self.log.debug('sm.tnsid: \'%s\'; rtnsid: \'%s\'', sm.tnsid, rtnsid)
                self.log.debug('##### sm.user.identity==rmessage.connection.identity -> %s', sm.user.identity==rmessage.connection.identity)
                self.log.debug('#####                          sm.tnsid==int(rtnsid) -> %s', sm.tnsid==rtnsid )

                if (sm.user.identity == rmessage.connection.identity) and (sm.tnsid == rtnsid) :
                    self.log.debug('found statemachine: %s', sm)
                    message_matched = True

                    # support cens gui
                    # log received msg
                    self.app.log_message(sm.session_id, rmessage.text, False)

                    (optional_response, retcode) = sm.handle_message(rtext)
                    if retcode is "ok":
                        retcode = sm.setup_retry_finish_fail()
                    else:
                        # if they sent a response can could not match we do not want to decrement the retry counter
                        retcode = sm.setup_retry_finish_fail(no_decrement_retry=True)
                    # handle_message checks for a match, if there was a match, advance to the
                    # next node. If there was no match, stay on the same node.
                    if retcode is 'fail':
                        response = None
                        self.log.debug('no more retries, failing')
                    elif retcode is 'finish':
                        if sm.node.do_not_send is False:
                            # FAISAL: now passing the user's text to the response builder so we have access to it in the response callback
                            response = TaskManager.build_send_str(sm.node, sm.tnsid, received_msg=rtext)
                            self.log.debug('and response = %s, do_not_send: %s' % (response, sm.node.do_not_send))
                            self.app.log_message(sm.session_id, response, True)
                        else:
                            response = None
                    else: #retcode is 'retry': #indicates proceed normally or
                        if optional_response is not None:
                            response = optional_response
                        else:
                            response = TaskManager.build_send_str(sm.node, sm.tnsid, received_msg=rtext)
                        self.log.debug('and response = %s' % (response))
                        self.app.log_message(sm.session_id, response, True)
                        
                    # save current state
                    self.save_curr_statemachine(sm)

                    # already found and processed, so leave
                    break
        
        # Too hacky. Need to redo entire function to make this better. Probably should
        # return extra boolean along with message instead?
        if not message_matched:
            raise NotImplementedError("Can not match message to any task")
        
        return response
                

    def run(self):
        """ start up all statemachines"""
        self.log.debug('in TaskManager.run(): self.uism: %s' % self.uism)
        # send the first messages. once the statemachines are running,
        # responses will be ping-ponged back and forth from App.handle() to self.recv()
        for sm in self.uism:
            if sm.done:
                continue
            if sm.node == sm.interaction.initialnode and sm.node.sentcount == 0:
                # This is the init case
                sm.setup_retry_finish_fail(no_decrement_retry=True)
                self.send_curr_message(sm)
                self.save_curr_statemachine(sm)
            else: #if sm.node.sentcount > 0:
                # This is the case if the system has come down, and then comes back up and is waiting for a response
                # We need to set the timers, but we do not need to send anything
                sm.setup_retry_finish_fail(no_decrement_retry=True)
                self.save_curr_statemachine(sm)

            




    



