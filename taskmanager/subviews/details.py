import sys

from django.shortcuts import render_to_response
from django.http import HttpResponseRedirect, HttpResponseNotFound, HttpResponse
from django.core.urlresolvers import reverse
from django.template import RequestContext
from taskmanager.models import *

from datetime import datetime

def process_details(request, processid):
    context = {
        'process': Process.objects.get(pk=processid)
    }
    return render_to_response('dashboard/details/process.html', context)

def process_command(request, processid):
    if request.method == "POST" and request.is_ajax():
        command = request.POST.get('command')
        process = Process.objects.get(pk=processid)

        # dispatch on different commands
        if command == "deactivate":
            # remove all pending tasks
            process.get_pending_tasks().delete()
            # time out all running sessions
            process.get_current_sessions().update(timeout_date=datetime.now())
            return HttpResponse("REQUIRES_REFRESH")
        elif command == "remove":
            process.delete()
            return HttpResponse("REQUIRES_REFRESH")

        return HttpResponse("CMD_NOT_FOUND")

    # and render the default view
    return process_details(request, processid)

def scheduledtask_details(request, taskid):
    context = {
        'task': ScheduledTask.objects.get(pk=taskid)
    }
    return render_to_response('dashboard/details/scheduledtask.html', context)

def scheduledtask_command(request, taskid):
    if request.method == "POST" and request.is_ajax():
        command = request.POST.get('command')
        task = ScheduledTask.objects.get(pk=taskid)

        # dispatch on different commands
        if command == "remove":
            task.delete()
            return HttpResponse("REQUIRES_REFRESH")

        return HttpResponse("CMD_NOT_FOUND")

    # and render the default view
    return scheduledtask_details(request, taskid)

def session_details(request, sessionid):
    context = {
        'session': Session.objects.get(pk=sessionid)
    }
    return render_to_response('dashboard/details/session.html', context)

def session_command(request, sessionid):
    if request.method == "POST" and request.is_ajax():
        command = request.POST.get('command')
        task = Session.objects.get(pk=sessionid)

        # dispatch on different commands
        if command == "timeout":
            session.timeout_date = datetime.now()
            session.save()
            return HttpResponse("REQUIRES_REFRESH")

        return HttpResponse("CMD_NOT_FOUND")

    # and render the default view
    return session_details(request, sessionid)

def patient_details(request, patientid):
    context = {
        'patient': Patient.objects.get(pk=patientid)
    }
    return render_to_response('dashboard/details/patient.html', context)
