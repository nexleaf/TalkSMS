# tasks/taskscheduler.py


from taskmanager.models import *
import json

from datetime import datetime

def schedule(newtask):
    try:
        print 'in taskscheduler.schedule():'
        print 'newtask: %s', newtask


        if 'session_id' in newtask:
            session = Session.objects.get(pk=newtask['session_id'])
            print 'session: %s', session
            process = session.process
        else:
            session = None
            process = None
            
        if 'args' in newtask:
            arguments = json.dumps(newtask['args'])
        else:
            arguments = json.dumps({})

        nt = ScheduledTask(
            patient = Patient.objects.get(address=newtask['user']),
            task = Task.objects.get(name=newtask['task']),
            process = process,
            arguments = arguments,
            schedule_date = newtask['schedule_date']
        )
        print 'nt: %s' % (nt)
        nt.save()
        print 'saved nt'
    except Exception as e:
        print 'problem scheduling newtask: %s' % (e)
        raise
