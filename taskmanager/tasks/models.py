from django.db import models

class SerializedTasks(model.Model):

    # parameter blob: json_self.args from the task
    pblob = models.CharField(max_length=500)
    
    # serialized attributes for sms.Message 
    m_sentcount = models.Integer()
    
    # serialized attributes for sms.Interaction
    i_initialnode = models.CharField(max_length=30)
    
    # serialized attributes for sms.User
    u_nextmsgid = models.Integer()

    # serialized attributes for sms.StateMachine
    s_app = models.CharField()
    s_session_id = models.Integer()
    s_msgid = models.Integer()
    s_done = models.CharField()
    s_node = models.CharField()
    s_event = models.CharField()
    s_mbox = models.CharField()
    

    
    
