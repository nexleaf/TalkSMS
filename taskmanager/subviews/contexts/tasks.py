import sys

from django.shortcuts import render_to_response
from django.http import HttpResponseRedirect, HttpResponseNotFound, HttpResponse
from django.core.urlresolvers import reverse
from django.template import RequestContext

from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_protect

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

@csrf_protect
@login_required
def templates(request, taskid, tasktemplateid=None):
    field_vars = {
        'section': 'templates',
        'tasktemplates': TaskTemplate.objects.filter(task__id=taskid)
        }

    if tasktemplateid:
        field_vars['selected_tasktemplateid'] = tasktemplateid
        field_vars['tasktemplate'] = TaskTemplate.objects.get(pk=tasktemplateid)
        field_vars['value_types'] = {'checkbox': '?CheckboxInput', 'textbox': '?TextInput'}

        # attempt to decode json data if present...if not, just bleh it out
        try:
            field_vars['args_dict'] = json.loads(field_vars['tasktemplate'].arguments)
        except:
            field_vars['args_dict'] = {}
    
    merge_contextuals(field_vars, request, taskid)
    return render_to_response('dashboard/contexts/tasks/templates.html', field_vars, context_instance=RequestContext(request))

@csrf_protect
@login_required
def messages(request, taskid):
    field_vars = {
        'section': 'messages',
        'task': Task.objects.get(pk=taskid),
        'templates': Task.objects.get(pk=taskid).templates.all()
        }
    
    merge_contextuals(field_vars, request, taskid)
    return render_to_response('dashboard/contexts/tasks/messages.html', field_vars, context_instance=RequestContext(request))

@csrf_protect
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
def add_tasktemplate(request):
    if request.method == 'POST':
        np = TaskTemplate(
            name = request.POST['templatename'],
            task = Task.objects.get(pk=request.POST['selected_taskid'])
            )
        np.save()

        # return HttpResponseRedirect(reverse('taskmanager.views.scheduler'))
        # we redirect them to the patient's new process page
        return HttpResponseRedirect('/taskmanager/tasks/%s/templates/%d/' % (request.POST['selected_taskid'], np.id))


@login_required
def update_template(request):
    if request.method == 'POST':
        obj = TaskTemplate.objects.get(pk=request.POST['editing_tasktemplateid'])

        # we have a variable number of fields here
        # first we need to collect all the associated fields
        # then we need to create an arguments structure, serialize it to JSON, then stuff it into the template
        args_dict = {}
        
        for (idx,param,value) in [(int(i.split("__")[2]), i.split("__")[3], request.POST[i]) for i in request.POST if i.startswith("__argsdict__")]:
            if idx not in args_dict: args_dict[idx] = {}
            args_dict[idx][param] = value

        final_dict = {}
        for i in args_dict:
            if args_dict[i]["value"] != "?Static":
                final_dict[args_dict[i]["label"]] = args_dict[i]["value"]
            else:
                final_dict[args_dict[i]["label"]] = args_dict[i]["value_ext"]
            
        obj.arguments = json.dumps(final_dict, sort_keys=True)
        obj.save()

        # return HttpResponseRedirect(reverse('taskmanager.views.scheduler'))
        # we redirect them to the patient's new process page
        return HttpResponseRedirect(request.POST['return_page'])

@login_required
def update_messages(request):
    if request.method == 'POST':
        # iterate through all of the elements in the POST that start with "arguments__"
        # i know it's crazy, but my brain needed a little puzzle...it shouldn't be any less efficient than doing it manually
        for (id,value) in [(int(i.split("__")[1]), request.POST[i]) for i in request.POST if i.startswith("content__")]:
            obj = dbtemplates.models.Template.objects.get(pk=id)
            obj.content = value
            obj.save()

        # return HttpResponseRedirect(reverse('taskmanager.views.scheduler'))
        # we redirect them to the patient's new process page
        return HttpResponseRedirect(request.POST['return_page'])
