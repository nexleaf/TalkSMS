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
            print 'session: %s' % session
            process = session.process
        else:
            session = None

        if 'process_id' in newtask:
            process = Process.objects.get(pk=newtask['process_id'])
            print 'process: %s' % process
        else:
            print 'no process_id in newtask while adding this scheduled task'
            # do nothing...
            
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
