from django.db import models

class SerializedTasks(models.Model):

    # parameter blob: json_self.args from the task
    pblob = models.CharField(max_length=500)
    
    # serialized attributes for sms.StateMachine, representing state at last .save()
    s_app = models.CharField(max_length=50)
    s_session_id = models.CharField(max_length=5)
    s_msgid = models.CharField(max_length=5)
    s_done = models.CharField(max_length=5)
    s_node = models.CharField(max_length=50)
    s_event = models.CharField(max_length=20)
    s_mbox = models.CharField(max_length=150)

    # serialized attributes for sms.Message 
    m_sentcount = models.CharField(max_length=5)
    
    # serialized attributes for sms.Interaction
    i_initialnode = models.CharField(max_length=30)  # should be a label for a specific node
    
    # serialized attributes for sms.User
    u_nextmsgid = models.CharField(max_length=5)


    
    
