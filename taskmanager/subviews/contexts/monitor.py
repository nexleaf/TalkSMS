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
def merge_contextuals(context, request, serviceid):
    # update our context if it isn't already
    request.session['context'] = 'monitor'
    
    context.update({
        'context': 'monitor',
        'services': Service.objects.all(),
        'selected_serviceid': serviceid,
        'current_page': request.path
        })

@csrf_protect
@login_required
def status(request, serviceid):
    field_vars = {
        'section': 'status',
        'service': Service.objects.get(pk=serviceid)
        }

    # figure out which specific template to use to render the status page
    # if no custom template for this service exists, use the default template (i.e. 'no status for this service' page)
    target_page = {
        'Task Manager': 'dashboard/contexts/monitor/status_taskmanager.html',
        'Scheduler': 'dashboard/contexts/monitor/status_scheduler.html'
        }.get(field_vars['service'].name, 'dashboard/contexts/monitor/status.html')
    
    merge_contextuals(field_vars, request, serviceid)
    return render_to_response(target_page, field_vars, context_instance=RequestContext(request))

@csrf_protect
@login_required
def alerts(request, serviceid):
    field_vars = {
        'section': 'alerts',
        'service': Service.objects.get(pk=serviceid),
        }

    # add last reviewed on to field vars if it's present
    if 'alerts_reviewed_on' in request.session and serviceid in request.session['alerts_reviewed_on']:
        field_vars['alerts_reviewed_on'] = request.session['alerts_reviewed_on'][serviceid]

    if 'show_all' in request.GET:
        # just show all of them
        field_vars['alerts'] = Alert.objects.filter(alert_type__service__id=serviceid)
        field_vars['show_all'] = True
    elif 'from' in request.GET:
        # parse at least the from field, and preferably the to field as well
        p = pdt.Calendar()
        from_clean = urllib.unquote(request.GET['from'].replace('+',' '))
        from_time = p.parse(from_clean)
        from_datetime = datetime.fromtimestamp(time.mktime(from_time[0]))

        field_vars['from'] = from_clean
        if 'custom' in request.GET: field_vars['custom'] = 'true'

        if 'to' not in request.GET or request.GET['to'].strip() == "":
            # use only the from field
            field_vars['alerts'] = Alert.objects.filter(alert_type__service__id=serviceid,add_date=from_datetime)
        else:
            # attempt to parse to, since it's here
            to_clean = urllib.unquote(request.GET['to'].replace('+',' '))
            to_time = p.parse(to_clean)

            field_vars['to'] = to_clean
            
            if (to_time[1] > 0):
                # it was parseable, make the range reflect this
                to_datetime = datetime.fromtimestamp(time.mktime(to_time[0]))
                field_vars['alerts'] = Alert.objects.filter(alert_type__service__id=serviceid,add_date__gte=from_datetime,add_date__lte=to_datetime)
            else:
                # it was unparseable, just use from
                field_vars['alerts'] = Alert.objects.filter(service__id=serviceid,add_date__gte=from_datetime)
    elif 'alerts_reviewed_on' in request.session and serviceid in request.session['alerts_reviewed_on']:
        field_vars['alerts'] = Alert.objects.filter(alert_type__service__id=serviceid, add_date__gte=request.session['alerts_reviewed_on'][serviceid])
    else:
        # the default is also just to show all records (perhaps combine with first clause somehow)
        field_vars['alerts'] = Alert.objects.filter(alert_type__service__id=serviceid)
    
    merge_contextuals(field_vars, request, serviceid)
    return render_to_response('dashboard/contexts/monitor/alerts.html', field_vars, context_instance=RequestContext(request))

@csrf_protect
@login_required
def default(request):
    # add in the list of users so we can draw the user chooser
    field_vars = {}
    
    # and render the full page
    merge_contextuals(field_vars, request, None)
    return render_to_response('dashboard/contexts/monitor/main.html', field_vars, context_instance=RequestContext(request))

# =================================================================
# ==== Form for marking alerts reviewed
# =================================================================
        
@login_required
def mark_alerts_reviewed(request):
    if request.method == 'POST':
        serviceid = request.POST['serviceid']

        # check if the alerts_reviewed_on dict already exists and create it if not
        if 'alerts_reviewed_on' not in request.session:
            request.session['alerts_reviewed_on'] = {serviceid: datetime.now()}
        else:
            request.session['alerts_reviewed_on'][serviceid] = datetime.now()

        # fixed a little gotcha where the session isn't saved if you alter a nested object
        request.session.modified = True

        return HttpResponseRedirect(request.POST['return_page'])
        
