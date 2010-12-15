import sys

from django.shortcuts import render_to_response
from django.http import HttpResponseRedirect, HttpResponseNotFound, HttpResponse
from django.core.urlresolvers import reverse
from django.template import RequestContext
from taskmanager.models import *
from django.views.decorators.csrf import csrf_protect

from datetime import datetime

@csrf_protect
def process_details(request, processid):
    context = {
        'process': Process.objects.get(pk=processid)
    }
    return render_to_response('dashboard/details/process.html', context, context_instance=RequestContext(request))

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

@csrf_protect
def scheduledtask_details(request, taskid):
    context = {
        'task': ScheduledTask.objects.get(pk=taskid)
    }
    return render_to_response('dashboard/details/scheduledtask.html', context, context_instance=RequestContext(request))


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

@csrf_protect
def session_details(request, sessionid):
    context = {
        'session': Session.objects.get(pk=sessionid)
    }
    return render_to_response('dashboard/details/session.html', context, context_instance=RequestContext(request))

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

@csrf_protect
def patient_details(request, patientid):
    context = {
        'patient': Patient.objects.get(pk=patientid)
    }
    return render_to_response('dashboard/details/patient.html', context, context_instance=RequestContext(request))

def patient_command(request, patientid):
    if request.method == "POST" and request.is_ajax():
        command = request.POST.get('command')
        patient = Patient.objects.get(pk=patientid)

        # dispatch on different commands
        if command == "halt":
            # set patient's status to halted
            patient.halted = True
            patient.save()
            return HttpResponse("REQUIRES_REFRESH")
        elif command == "unhalt":
            # set patient's status to un-halted
            patient.halted = False
            patient.save()
            return HttpResponse("REQUIRES_REFRESH")

        return HttpResponse("CMD_NOT_FOUND")

    # and render the default view
    return process_details(request, processid)
