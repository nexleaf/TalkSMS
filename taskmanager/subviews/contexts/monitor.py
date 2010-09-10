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
def merge_contextuals(context, request, itemid):
    # update our context if it isn't already
    request.session['context'] = 'monitor'
    
    context.update({
        'context': 'monitor',
        'selected_itemid': itemid,
        'current_page': request.path
        })

@login_required
def templates(request, itemid):
    field_vars = {
        'section': 'templates',
        'tasktemplates': TaskTemplate.objects.filter(task__id=itemid)
        }
    
    merge_contextuals(field_vars, request, itemid)
    return render_to_response('dashboard/contexts/monitor/templates.html', field_vars, context_instance=RequestContext(request))

@login_required
def messages(request, itemid):
    field_vars = {
        'section': 'messages',
        'task': Task.objects.get(pk=itemid),
        'templates': Task.objects.get(pk=itemid).templates.all()
        }
    
    merge_contextuals(field_vars, request, itemid)
    return render_to_response('dashboard/contexts/monitor/messages.html', field_vars, context_instance=RequestContext(request))

@login_required
def default(request):
    # add in the list of users so we can draw the user chooser
    field_vars = {}
    
    # and render the full page
    merge_contextuals(field_vars, request, None)
    return render_to_response('dashboard/contexts/monitor/main.html', field_vars, context_instance=RequestContext(request))
