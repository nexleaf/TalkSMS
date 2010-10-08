# tasks/taskscheduler.py


from taskmanager.models import *
import json

from datetime import datetime

def schedule(newtask):
    try:
        print 'in taskscheduler.schedule():'
        session = Session.objects.get(pk=newtask['session_id'])
        print 'session: %s', session
        nt = ScheduledTask(
            patient = Patient.objects.get(address=newtask['user']),
            task = Task.objects.get(name=newtask['task']),
            process = session.process,
            arguments = json.dumps(newtask['args']),
            #schedule_date = datetime.strptime(newtask['schedule_date'], "%Y-%m-%dT%H:%M:%S")
            schedule_date = newtask['schedule_date']
        )
        print 'nt: %s' % (nt)
        nt.save()
        print 'saved nt'
    except Exception as e:
        print 'problem scheduling newtask: %s' % (e)
        raise
