import sms
from taskmanager.tasks.models import SerializedTasks

class Task(object):
    """base class for tasks"""
    
    def __init__(self, graph=None, interaction=None, currentnode=None):
        print 'in Task.__init__():'
        self.interaction = interaction

    def setinteraction(self, graph, initialnode, label):
        self.interaction = sms.Interaction(graph=graph, initialnode=initialnode, label=label)

                                                      


        
