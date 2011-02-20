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

from taskmanager.models import *
import taskscheduler

from task import BaseTask

class mediabus(BaseTask):
    
    def __init__(self, user, args=None):

        # why is this here?
        BaseTask.__init__(self)

        self.args = args

        print 'in mediabus: self.args: %s; type(self.args):%s' % (self.args, type(self.args))
        
        self.user = user

        if 'message' not in self.args.keys():
            raise Exception('No message in args')

        message = args['message']
        firstword = str(message).lower().split(None, 1)[0]

        # Store to DB

        # Thank you message
        m_thank = sms.Message("Thank you for your input! Gracias por su participacion!", [], label='thankyouresponse', retries=0, timeout=0)
        
        # define a super class with .restore() in it. below, user will call createGraph(), createInteraction()
        # which remember handles to graph and interaction. when .restore() is called it just updates the node we're at searching with the label.
        self.graph = { m_thank: [] }

        super(mediabus, self).setinteraction(graph=self.graph, initialnode=m_thank, label='mediabusinteraction')
        

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
    def match_user_init(message):
        try:
            firstword = str(message.text).lower().split(None, 1)[0]
            thenumber = int(firstword)
        except Exception as e:
            return False, None, None, None
        
        args = {'message': message.text}
        
        return True, "mediabus", "mediabus", args


