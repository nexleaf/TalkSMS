# sms.py: TalkSMS library

import string
import re
from collections import deque
import itertools

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

    def __init__(self, question, responselist=[], autoresend=0, label=''):
        self.question = question
        self.responselist = responselist
        self.autoresend = autoresend

        if not label:
            raise ValueError('Response requires a unique label string.')
        self.label = label
        
        self.sentcount = 0

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
        self.msgid = Cycle(User.MAXMSGID)

    @property
    def username(self):
        return self.firstname + ' ' + self.lastname
        

class StateMachine(object):
      """
      StateMachine keeps track of the flow through an Interaction graph.
      """
      # max number of times a message is sent when expecting a reply
      MAXSENTCOUNT = 3
      # time to resend a message in minutes
      TIMEOUT = 60*24
      
      def __init__(self, app, user, task, session_id, label=''):
          self.app = app
          self.log = app

          # support cens gui
          self.session_id = session_id

          self.task = task
          self.interaction = task.interaction
          self.user = user
          self.label = label
          
          # msgid is incremented only during init (here), and in handle_response() when a message node has a non-empty responselist,
          # (that is, when we need to send a new message to track)
          self.msgid = self.user.msgid.next()
          self.done = False

          # current node in the interaction graph
          self.node = self.interaction.initialnode
          self.event = 'SEND_MESSAGE'
          self.handler = { 'SEND_MESSAGE'     : self.send_message,
                           'WAIT_FOR_RESPONSE': self.wait_for_response,
                           'HANDLE_RESPONSE'  : self.handle_response,
                           'EXIT'             : self.close }
          self.mbox = None


      def send_message(self):     
          self.log.debug('in StateMachine.send_message(): self.event: %s; self.msgid: %s', self.event, self.msgid)
          self.log.debug('self.node: %s, self.node.sentcount: %s' % ( str(self.node), self.node.sentcount ))

          if self.node.sentcount < StateMachine.MAXSENTCOUNT:

              if not self.node.responselist:

                  self.event = 'EXIT'

              else:

                  self.event = 'WAIT_FOR_RESPONSE'

                  # if this is the first time we're sending this message,
                  # schedule at most 3 resend's each spaced out by TIMEOUT minutes from now.
                  if self.node.sentcount == 0:
                      d = {'callback':'taskmanager.app.callresend',
                           'minutes':StateMachine.TIMEOUT,
                           'repetitions':StateMachine.MAXSENTCOUNT,
                           'msgid':self.msgid,
                           'identity':self.user.identity }                 
                      self.app.schedule_response_reminders(d)

              # this is the only place sentcount should be incremnted
              self.node.sentcount += 1
              self.log.debug('incremented self.node.sentcout: %s; self.msgid: %s', self.node.sentcount, self.msgid)
              
          else:

              self.log.debug('(current message node reached maxsentcount, exiting StateMachine %s)' % self.label )
              self.event = 'EXIT'


              
      def wait_for_response(self):
          self.log.debug('in StateMachine.wait_for_response(): self.event: %s' % self.event)

          # wait_for_response() is called only when there is a response (left in mbox)
          # if there isn't one there, it means a call-back timer was triggered,
          # which kicked the statemachine with no package in mbox.
          if not self.mbox:

              self.log.debug('(timer timed_out while waiting for response; resending)')
              self.event = 'SEND_MESSAGE'

          else:

              self.event = 'HANDLE_RESPONSE'
          


      def handle_response(self):
          self.log.debug('in StateMachine.handle_response(): self.event: %s', self.event)

          assert(self.mbox is not None)
          rnew = self.mbox
          self.log.debug('rnew: \'%s\'', rnew)

          # FAISAL: quick hack to evaluate responses in order and choose the first one that matches
          
          # iterate through the possible responses
          # execute the first non-false, non-None match and break
          # if nothing matches, post a debug message and quit

          foundmatch = False # if this is still false, we didn't find anything ;_;

          for response in self.node.responselist:
              result = response.match(rnew)

              if result != False and result != None:
                  foundmatch = True
                  
                  self.log.debug('found response match')
     
                  # advance to the next node
                  self.node = self.interaction.mapsTo(self.node, response)
                  self.log.debug('advanced current node to: %s', self.node)

                  # increment msgid every time we handle a response
                  # this throws away a msgid periodically but, we don't guarentee an ordered sequence, just an increasing one...
                  self.msgid = self.user.msgid.next()
                  self.log.debug('incrementing self.msgid to: %s', self.msgid)

                  # call response obj's developer defined callback
                  if hasattr(response, 'callback'):
                      self.log.debug('calling %s callback', response)
                      # send back rnew, session_id
                      response.kwargs['response'] = rnew
                      response.kwargs['session_id'] = self.session_id
                      result = response.callback(*response.args, **response.kwargs)
                      self.log.debug('callback result: %s.', result)
                  
                  # ...and quit looking for more
                  break

          if not foundmatch:
            self.log.debug('response did not match expected list of responses, attempting to resend')

##          # did the new response match anything in the responselist?
##          matches = [r.match(rnew) for r in self.node.responselist]
##          matchcount = len(matches) - (matches.count(None) + matches.count(False))
##          self.log.debug('matches: %s', matches)          
##          self.log.debug('matchcount: %s', matchcount)          
##
##          if matchcount == 1:
##
##              self.log.debug('found response match')
##              # find index for the match
##              i = [m is not None and m is not False for m in matches].index(True)
##              response = self.node.responselist[i]
## 
##              # advance to the next node
##              self.node = self.interaction.mapsTo(self.node, response)
##              self.log.debug('advanced current node to: %s', self.node)
##
##              # increment msgid every time we handle a response
##              # this throws away a msgid periodically but, we don't guarentee an ordered sequence, just an increasing one...
##              self.msgid = self.user.msgid.next()
##              self.log.debug('incrementing self.msgid to: %s', self.msgid)
##
##              # call response obj's developer defined callback
##              if hasattr(response, 'callback'):
##                  self.log.debug('calling %s callback', response)
##                  # send back rnew, session_id
##                  response.kwargs['response'] = rnew
##                  response.kwargs['session_id'] = self.session_id
##                  result = response.callback(*response.args, **response.kwargs)
##                  self.log.debug('callback result: %s.', result)
##                            
##          elif matchcount == 0: 
##
##              self.log.debug('response did not match expected list of responses, attempting to resend')
##
##          else:
##
##              self.log.debug('rnew: %s, matched more than one response in response list, attempting to resend', rnew)

          # processed input, now reply
          self.event = 'SEND_MESSAGE'

          
      def close(self):
          """done. tell taskmanager to move me from the live list to the dead list..."""
          self.log.debug('in StateMachine.close(): self.event: %s' % self.event)
          self.done = True
          # support cens gui
          self.app.session_close(self.session_id)
          
              
      def kick(self, package=None):
          self.log.debug('in StateMachine.kick(): self.event: %s' % self.event)

          while not self.done:
              self.mbox = package
              self.handler[self.event]()

              # support cens gui
              self.app.session_updatestate(self.session_id, self.event)

              if self.event == 'WAIT_FOR_RESPONSE':
                  break



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


    def scrub(self, statemachine):
        """remove statemachine from user's and taskmanager's lists"""
        assert(statemachine in self.uism)
        assert(len(self.uism) > 0)
        assert(statemachine.done)

        try:
            i = self.uism.index(statemachine)
            self.log.debug('in TaskManager.scrub(): deleting statemachine: %s from self.uism', statemachine)
            self.uism.pop(i)            
        except ValueError:
            self.log.error('statemachine is not in self.uism')
            return
        except NameError:
            self.log.error('statemachine is not defined')
            return

        
    @staticmethod
    def build_send_str(node, msgid):
        text = ''.join(node.question)

        if (node.sentcount > 1):
          text += ' (resending, attempt %d of %d)' % (node.sentcount, TaskManager.TRYS)
        if node.responselist:
          text += ' Type \"%d\" before your reply.' % (msgid)

        print 'in TaskManager.build_send_str(): node.sentcount: %s' % node.sentcount

        return text


    # the first send is app.start() -> tm.run() -> sm.kick() -> app.send().
    # then each message is received (or ping-ponged back and forth)
    # by app.handle() -> app.recv() -> sm.kick() which
    # returns a string, 'response' along the same route.     
    def send(self, statemachine):
        # edge-case: sentcount<=max since it's called after last inc of sentcount
        if statemachine.node.sentcount <= StateMachine.MAXSENTCOUNT:
            text = TaskManager.build_send_str(statemachine.node, statemachine.msgid)
            self.log.debug('in TaskManager.send(): node.sentcount: %s, preparing to send text: %s', statemachine.node.sentcount, text)
            self.app.log_message(statemachine.session_id, text, True)
            self.app.send(statemachine.user.identity, statemachine.user.identityType, text)

            # save current state
            d = {'t_pblob' : statemachine.task.save(),
                 's_msgid' : statemachine.msgid,
                 's_done' : statemachine.done,
                 's_node' : statemachine.node.label,
                 's_event': statemachine.event,
                 's_mbox' : statemachine.mbox if statemachine.mbox else '',
                 'm_sentcount' : statemachine.node.sentcount,
                 'u_nextmsgid' : statemachine.user.msgid.peek() }
            self.app.savetask(statemachine.session_id, **d)

        else:
            self.log.debug('in TaskManager.send(): not sending, statemachine.node.sentcount:%s > MAX', statemachine.node.sentcount)
        

    def recv(self, rmessage):
        self.log.debug('in TaskManager.recv(): ')

        response = 'Command not understood.'
        nid = self.numbers.match(rmessage.text)
        
        if not nid:
            # user-initiated-task? see if the message contains a keyword associated with a task
            if self.app.createdbuserandtask(rmessage):
                response = None
        else:
            # fall-through response string
            response = 'Response not understood. Please prepend the message id number to your response.'
            
            # strip off msgid and text from the repsonse 
            rmsgid = nid.group()
            a,b,rtext = rmessage.text.partition(str(rmsgid))
            assert(b==rmsgid)
            rtext = rtext.splitlines()[0].strip()
            self.log.debug('found msgid in response' +\
                      'rmsgid: \'%s\'; rtext: \'%s\'; peer: \'%s\'' % (rmsgid, rtext, rmessage.connection.identity))           

            # first, exfoliate
            for sm in self.uism:
                if sm.done:
                    self.log.debug('preparing to delete statemachine: %s', sm)
                    self.scrub(sm)

            # then, find the correct statemachine
            for sm in self.uism:
                
                # sanity check out to log
                self.log.debug('            sm.user.identity: \'%s\',', sm.user.identity)
                self.log.debug('rmessage.connection.identity: \'%s\';', rmessage.connection.identity)
                self.log.debug('sm.msgid: \'%s\'; rmsgid: \'%s\'', sm.msgid, rmsgid)
                self.log.debug('##### sm.user.identity==rmessage.connection.identity -> %s', sm.user.identity==rmessage.connection.identity)
                self.log.debug('#####                          sm.msgid==int(rmsgid) -> %s', sm.msgid==int(rmsgid) )

                if (sm.user.identity == rmessage.connection.identity) and (sm.msgid == int(rmsgid)) :
                    self.log.debug('found statemachine: %s', sm)

                    # support cens gui
                    # log received msg
                    self.app.log_message(sm.session_id, rmsgid + ' ' + rtext, False)

                    sm.kick(rtext)
                    response = TaskManager.build_send_str(sm.node, sm.msgid)
                    self.log.debug('and response = %s' % response)

                    # support cens gui
                    # log reply
                    self.app.log_message(sm.session_id, response, True)

                    # save current state
                    d = {'t_pblob' : sm.task.save(),
                         's_msgid' : sm.msgid,
                         's_done' : sm.done,
                         's_node' : sm.node.label,
                         's_event': sm.event,
                         's_mbox' : sm.mbox if sm.mbox else '',
                         'm_sentcount' : sm.node.sentcount,
                         'u_nextmsgid' : sm.user.msgid.peek() }
                    self.app.savetask(sm.session_id, **d)

                    # already found and processed, so leave
                    break

        return response
                

    def run(self):
        """ start up all statemachines"""
        self.log.debug('in TaskManager.run(): self.uism: %s' % self.uism)
        # send the first messages. once the statemachines are running,
        # responses will be ping-ponged back and forth from App.handle() to self.recv()
        for sm in self.uism:
            if sm.node == sm.interaction.initialnode and sm.node.sentcount == 0:
                sm.kick()
                self.send(sm)





    



