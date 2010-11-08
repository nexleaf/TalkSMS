import sms
from taskmanager.tasks.models import SerializedTasks

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
        
        # need to restore this:

        ## pblob restored by instantiating the task in app
        # pblob = {'args': '{"appt_type": "Echo heart test"}'}

        ## shouldn't need to restore app name?
        # s_app = taskmanager

        ## session_id handled by app
        # s_session_id = 4

        ## all of this can be restored by app? hmm...i forgot why needed this base class.
        ## ...i don't need the base class...
        ##    i have the session_id, so lookup task_id in the session table, then use that to find task name, reinstantiate,
        ##    at that point i have a statemachine, so update

        ## restored in statemachine
        # s_msgid = 3
        # s_done = 1
        # s_node = m3
        # s_event = EXIT
        # s_mbox = 10 min
        # m_sentcount = 1

        ## not used really...since task will initialize but, good to have maybe?...i don't need to worry about it.
        # i_initialnode = m1

        ## ahh, this is important. user.msgid needs to be restored with the u_nextmsgid from the last save() before the restore...hmm.
        ## app.system_restore() can do this: for each user, find u_nextmsgid with the latest timestamp, and restore user with that.
        # u_nextmsgid = 4
                                                      


        
