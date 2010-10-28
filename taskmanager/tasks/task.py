import sms
#from taskmanager.tasks.models import SerializedTasks
#from taskmanager.models import *

class Task(object):
    """base class for tasks"""
    
    def __init__(self, graph=None, interaction=None, currentnode=None):
        print 'in Task.__init__():'
        self.graph = graph
        self.interaction = interaction
        self.currentnode = currentnode

    def setgraph(self, graph):
        self.graph = graph

    def setinteraction(self, node, label):
        self.currentnode = node
        self.interaction = sms.Interaction(graph=self.graph, initialnode=self.currentnode, label=label)

    def restore(self):
        print 'STUB:  Task.restore()'

