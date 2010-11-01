from django.db import models
from taskmanager.models import Session

class SerializedTasks(models.Model):

    #consider
    #session = models.ForeignKey(Session)

    # parameter blob: json_self.args from the task
    pblob = models.CharField(max_length=500)
    
    ## serialized attributes for sms.StateMachine, representing state at last .save()
    s_app = models.CharField(max_length=50)
    # we will use this as a foreign key into the Session/taskmanager_session table
    s_session_id = models.IntegerField(max_length=50)

    s_msgid = models.IntegerField(max_length=50)
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
    
    ##  serialized attributes for sms.User
    u_nextmsgid = models.IntegerField(max_length=5)


    
    
