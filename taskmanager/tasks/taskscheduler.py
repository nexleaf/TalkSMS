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

def schedule_task(task, user, args, schedule_date, session_id):
    try:
        print 'in taskscheduler.schedule():'
        print 'task %s, user %s, args %s, schedule_date %s, session_id %s' % (task, user, args, schedule_date, session_id)

        # TODO:
        # check user != None
        # check date is sane
        # check ask is sane
        # ... these can eventually be checked when we POST to the scheulder, it can return error codes

        if session_id != None:
            session = Session.objects.get(pk=session_id)
            print 'session: %s' % session
            process = session.process
        else:
            session = None
            process = None

        # removed process_id check... was not being set anywhere in task code

        if args != None:
            arguments = json.dumps(newtask['args'])
        else:
            arguments = json.dumps({})

        nt = ScheduledTask(
            patient = Patient.objects.get(address=user),
            task = Task.objects.get(name=task),
            process = process,
            arguments = arguments,
            schedule_date = schedule_date
        )
        print 'nt: %s' % (nt)
        nt.save()
        print 'saved nt'
    except Exception as e:
        print 'problem scheduling newtask: %s' % (e)
        raise


def schedule_timeout():
    try:
        # We have been using the rapidsms timer/scheduler functions to scheduler reminders/timeouts.
        # Instead we should use the external scheduler.
        # Here we replace app.schedule_response_reminders()
        # In addition to this, app.ajax_POST_timeout() needs to be repopulated to replace app.callresend() and app.resend()
        #
        a = None
    except Exception as e:
        print 'problem scheduling newtask: %s' % (e)
        raise
