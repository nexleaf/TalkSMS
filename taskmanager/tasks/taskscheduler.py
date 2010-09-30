# tasks/taskscheduler.py


from taskmanager.models import *
import json

def schedule(d):
    print 'in taskscheduler.schedule():'
    session = Session.objects.get(pk=d['session_id'])
    print 'session: %s', session
    nt = ScheduledTask(
        patient = Patient.objects.get(address=d['user']),
        task = Task.objects.get(name=d['task']),
        process = session.process,
        arguments = json.dumps(d['args']),
        schedule_date = d['schedule_date']
    )
    print 'nt: %s' % (nt)
    nt.save()        
