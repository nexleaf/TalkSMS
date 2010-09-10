import sys

from django.shortcuts import render_to_response
from django.http import HttpResponseRedirect, HttpResponseNotFound, HttpResponse
from django.core.urlresolvers import reverse
from django.template import RequestContext

from django.contrib.auth.decorators import login_required

from taskmanager.models import *
import dbtemplates.models

from datetime import datetime
import parsedatetime.parsedatetime as pdt
import parsedatetime.parsedatetime_consts as pdc

# for parsing argument lists
import json, urllib

# merges in the variables for this context
# call this right before you render to response
def merge_contextuals(context, request, taskid):
    # update our context if it isn't already
    request.session['context'] = 'tasks'
    
    context.update({
        'context': 'tasks',
        'selected_taskid': taskid,
        'current_page': request.path,
        'tasks': Task.objects.all()
        })

@login_required
def templates(request, taskid):
    field_vars = {
        'section': 'templates',
        'tasktemplates': TaskTemplate.objects.filter(task__id=taskid)
        }
    
    merge_contextuals(field_vars, request, taskid)
    return render_to_response('dashboard/contexts/tasks/templates.html', field_vars, context_instance=RequestContext(request))

@login_required
def messages(request, taskid):
    field_vars = {
        'section': 'messages',
        'task': Task.objects.get(pk=taskid),
        'templates': Task.objects.get(pk=taskid).templates.all()
        }
    
    merge_contextuals(field_vars, request, taskid)
    return render_to_response('dashboard/contexts/tasks/messages.html', field_vars, context_instance=RequestContext(request))

@login_required
def default(request):
    # add in the list of users so we can draw the user chooser
    field_vars = {}
    
    # and render the full page
    merge_contextuals(field_vars, request, None)
    return render_to_response('dashboard/contexts/tasks/main.html', field_vars, context_instance=RequestContext(request))

# =================================================================
# ==== Forms for adding Users, ScheduledTasks, Processes
# =================================================================

from django import forms

# the custom prefix used for custom argument fields
CUSTOM_FIELD_PREFIX = "_custom_arg_"

@login_required
def update_template(request):
    if request.method == 'POST':
        obj = TaskTemplate.objects.get(pk=request.POST['tasktemplateid'])
        obj.arguments = request.POST['arguments']
        obj.save()

        # return HttpResponseRedirect(reverse('taskmanager.views.scheduler'))
        # we redirect them to the patient's new process page
        return HttpResponseRedirect(request.POST['return_page'])

@login_required
def update_message(request):
    if request.method == 'POST':
        obj = dbtemplates.models.Template.objects.get(pk=request.POST['templateid'])
        obj.content = request.POST['content']
        obj.save()

        # return HttpResponseRedirect(reverse('taskmanager.views.scheduler'))
        # we redirect them to the patient's new process page
        return HttpResponseRedirect(request.POST['return_page'])
