from django.db import models
from taskmanager.models import Session

class SerializedTasks(models.Model):

    #consider
    #session = models.ForeignKey(Session)

    # orig args sent to task
    t_args = models.CharField(max_length=500)
    # parameter blob: json_self.args from the task
    t_pblob = models.CharField(max_length=500)

    ## serialized attributes for sms.StateMachine, representing state at last .save()
    s_app = models.CharField(max_length=50)
    # we will use this as a foreign key into the Session/taskmanager_session table
    s_session_id = models.IntegerField(max_length=50)

    # tasknamespace id's can be saved as json strings so that switching between simple id types (string, int)
    #    doesn't change the db model.
    s_tnsid = models.CharField(max_length=50)

    s_done = models.BooleanField(max_length=50)
    # label of the message node that's currently referenced in the statemachine as self.node.
    s_node = models.CharField(max_length=50)
    s_event = models.CharField(max_length=50)
    # last response left in statemachine.mbox
    s_mbox = models.CharField(max_length=150)

    ## serialized attributes for sms.Message 
    m_sentcount = models.IntegerField(max_length=5)
    
    ## serialized attributes for sms.Interaction
    # label for the initial node
    i_initialnode = models.CharField(max_length=30) 
    

    
    def __unicode__(self):
        return """
    t_args: %s
    t_pblob: %s
    s_app: %s
    s_session_id: %s
    s_tnsid: %s
    s_done: %s
    s_node: %s
    s_event: %s
    s_mbox: %s
    m_sentcount: %s
    i_initialnode: %s
        """ % (self.t_args,\
               self.t_pblob,\
               self.s_app,\
               self.s_session_id,\
               self.s_tnsid, \
               self.s_done,\
               self.s_node,\
               self.s_event,\
               self.s_mbox,\
               self.m_sentcount,\
               self.i_initialnode)
