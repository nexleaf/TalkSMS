from twisted.web import server, resource
from twisted.internet import reactor
from twisted.web.client import Agent
from twisted.web.http_headers import Headers
from stringprod import StringProducer

import sys, json
from datetime import datetime

from django.core.management.base import BaseCommand, CommandError
from taskmanager.models import *

TARGET_SERVER = 'http://localhost:8001/taskmanager/exec'
TARGET_TIMEOUT_SERVER = 'http://localhost:8001/taskmanager/timeout'
QUIET_HOURS = {'start': 22, 'end': 8}

# used by check_schedule() to determine if it can send tasks
# and by showJSONStatus() to let the interface know we're sleeping
def isQuietHours():
    global QUIET_HOURS
    return (not QUIET_HOURS is None) and (datetime.now().hour >= QUIET_HOURS['start'] or datetime.now().hour <= QUIET_HOURS['end'])


# =========================================================================================
# === HTTP interface definition
# =========================================================================================

class HTTPCommandBase(resource.Resource):
    isLeaf = False
    
    def __init__(self):
        resource.Resource.__init__(self)
        
    def getChild(self, name, request):
        if name == '':
            return self
        return resource.Resource.getChild(self, name, request)
    
    def render_GET(self, request):
        print "[GET] /"
        return "scheduler interface"

class HTTPStatusCommand(resource.Resource):
    def __init__(self):
        resource.Resource.__init__(self)
        
    def showJSONStatus(self, all_tasks=True):
        if all_tasks:
            tasks = ScheduledTask.objects.all()
        else:
            tasks = ScheduledTask.objects.get_pending_tasks()

        # apply extra filtering and sorting, regardless of the source
        tasks = tasks.filter(completed=False,active=True).order_by('-schedule_date')

        # stores the list of tasks that we'll be sending to the caller
        tasklist = []

        for task in tasks:
            tasklist.append({
                'id': task.id,
                'target': task.task.name,
                'arguments': json.loads(task.arguments),
                'schedule_date': task.schedule_date.ctime(),
                'completed': task.completed
                })

        return json.dumps({'status': ('running', 'sleeping')[isQuietHours()], 'tasks': tasklist})
    
    def showStatus(self, all_tasks=True):
        out = "<table>"
        out += "<tr class='header'><td>ID</td><td>Target</td><td>Arguments</td><td>Schedule Date</td><td>Completed</td></tr>"
        
        if all_tasks:
            tasks = ScheduledTask.objects.all()
        else:
            tasks = ScheduledTask.objects.get_pending_tasks()

        for task in tasks:
            out += '''
            <tr>
                <td>%(id)s</td><td>%(target)s</td><td>%(arguments)s</td><td>%(schedule_date)s</td><td>%(completed)s</td>
            </tr>''' % {'id': task.id, 'target': task.task.name, 'arguments': task.arguments, 'schedule_date': task.schedule_date, 'completed': task.completed}

        return str('''
        <html>
            <head>
            <style>.header td { font-weight: bold }</style>
            </head>
            <body>%s</body>
        </html>''' % (out))
    
    isLeaf = True
    def render_GET(self, request):
        if 'html' in request.args:
            print "[GET] /status"
            return self.showStatus('alltasks' in request.args)
        else:
            print "[GET] /status (json)"
            return self.showJSONStatus('alltasks' in request.args)
    
class HTTPScheduleCommand(resource.Resource):
    def __init__(self):
        resource.Resource.__init__(self)
    
    isLeaf = True
    def render_GET(self, request):
        print "[GET] /schedule"
        return "<html>schedule via POST</html>"
    
    def render_POST(self, request):
        print "[POST] /schedule"

        # nab the information from the post
        try:
            newtask = json.load(request.content)

            if 'process' in postargs:
                process = Process.objects.get(pk=postargs['process'])
            else:
                process = None
            
            nt = ScheduledTask(
                patient = Patient.objects.get(address=newtask['patient']).id,
                task = Task.objects.get(name=newtask['task']).id,
                process = process,
                arguments = newtask['arguments'],
                completed = False,
                schedule_date = datetime.strptime(newtask['schedule_date'], "%Y-%m-%dT%H:%M:%S.%f")
            )
            nt.save()
            
            print "Task scheduled: " + str(task)
        except:
            print "ERROR: could not schedule task " + str(task)
            print "INFO: ", sys.exc_info()[0]
            
        return "<html>this is correct</html>"


# =========================================================================================
# === task database access methods
# =========================================================================================

def task_finished(response, sched_taskid):
    t = ScheduledTask.objects.get(pk=sched_taskid)
    t.completed = True
    t.result = response.code
    t.completed_date = datetime.now()
    t.save()
    print "- finished %s (%d) w/code %s" % (t.task.name, sched_taskid, str(response.code))

def task_errored(response, sched_taskid):
    t = ScheduledTask.objects.get(pk=sched_taskid)
    t.result = response.getErrorMessage()
    t.save()
    print "- errored out on task %s (%d), reason: %s" % (t.task.name, sched_taskid, response.getErrorMessage())
    response.printTraceback()

def session_timeout_finished(response, sessionid):
    t = Session.objects.get(pk=sessionid)
    print "- timed out %s (%d) w/code %s" % (t.task.name, sessionid, str(response.code))

def session_timeout_errored(response, sessionid):
    t = Session.objects.get(pk=sessionid)
    print "- errored out on timing out %s (%d), reason: %s" % (t.task.name, sessionid, response.getErrorMessage())
    response.printTraceback()


# =========================================================================================
# === actual scheduling methods
# =========================================================================================

def check_schedule():
    # the server we should poke, defined at the top of this file
    global TARGET_SERVER
    # and our quiet hours settings
    global QUIET_HOURS

    # before we do anything, make sure it's not "quiet hours" (10pm to 9am)
    # if it is, do nothing and run this method later
    # FIXME: move the quiet hours settings into a file, the interface, whatever...they shouldn't be hardcoded
    if isQuietHours():
        # check again in 30 minutes...this is kind of silly, but hey
        print "*** Quiet hours are in effect (%d:00 to %d:00, currently: %d:00), calling again in 30 minutes..." % (QUIET_HOURS['start'], QUIET_HOURS['end'], datetime.now().hour)
        reactor.callLater(60*30, check_schedule)
        return
    
    tasks = ScheduledTask.objects.get_due_tasks()
    
    for sched_task in tasks[0:1]:
        agent = Agent(reactor)

        # ensure that the user is not halted -- if they are, we can't execute this task :\
        if sched_task.patient.halted:
            # print "ERROR: Cannot execute task: %s (%d), user is in the halt status" % (sched_task.task.name, sched_task.id)
            continue
        
        print "Executing task: %s (%d)" % (sched_task.task.name, sched_task.id)

        payload_dict = {
            'patient': sched_task.patient.id,
            'task': sched_task.task.id,
            'arguments': json.dumps(sched_task.arguments)
            }

        if sched_task.process:
            payload_dict['process'] = sched_task.process.id

        payload = "&".join(map(lambda x: "%s=%s" % (x, payload_dict[x]), payload_dict))

        d = agent.request(
            'POST',
            TARGET_SERVER,
            Headers({
                    "Content-Type": ["application/x-www-form-urlencoded;charset=utf-8"],
                    "Content-Length": [str(len(payload))]
                    }),
            StringProducer(payload))

        d.addCallback(task_finished, sched_taskid=sched_task.id)
        d.addErrback(task_errored, sched_taskid=sched_task.id)
        
    # run again in a bit
    reactor.callLater(30, check_schedule)

def check_timeouts():
    # the server we should poke, defined at the top of this file
    global TARGET_TIMEOUT_SERVER
    
    sessions = Session.objects.get_timedout_sessions()
    
    for session in sessions:
        agent = Agent(reactor)
        
        print "Timing out session: %s (%d)" % (session.task.name, session.id)

        payload_dict = {
            'patient': session.patient.id,
            'session': session.id
            }

        payload = "&".join(map(lambda x: "%s=%s" % (x, payload_dict[x]), payload_dict))

        d = agent.request(
            'POST',
            TARGET_TIMEOUT_SERVER,
            Headers({
                    "Content-Type": ["application/x-www-form-urlencoded;charset=utf-8"],
                    "Content-Length": [str(len(payload))]
                    }),
            StringProducer(payload))

        d.addCallback(session_timeout_finished, sessionid=session.id)
        d.addErrback(session_timeout_errored, sessionid=session.id)
        
    # run again in a bit
    reactor.callLater(30, check_timeouts)


# =========================================================================================
# === twisted entrypoint and django command definitions
# =========================================================================================

def main(port=8080,noquiet=None):
    # check params for quiet hours disabling setting
    if noquiet:
        global QUIET_HOURS
        QUIET_HOURS = None
        print "*** quiet hours have been disabled for this run"
        
    # construct the resource tree
    root = HTTPCommandBase()
    root.putChild('status', HTTPStatusCommand())
    root.putChild('schedule', HTTPScheduleCommand())

    print "Running scheduler on port %d..." % (int(port))
    
    site = server.Site(root)
    reactor.callLater(3, check_schedule)
    reactor.callLater(5, check_timeouts)
    reactor.listenTCP(int(port), site)
    reactor.run()

if __name__ == '__main__':
    main()

# to allow this to be executed as a django command...
class Command(BaseCommand):
    args = '<port> <noquiet>'
    help = 'Runs the scheduler via twisted (weird, i know)'

    def handle(self, *args, **options):
        main(*args)

