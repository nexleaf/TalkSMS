import sys

from django.shortcuts import render_to_response
from django.http import HttpResponseRedirect, HttpResponseNotFound, HttpResponse
from django.core.urlresolvers import reverse
from django.template import RequestContext

from django.contrib.auth.decorators import login_required

from taskmanager.models import *

from datetime import datetime
import parsedatetime.parsedatetime as pdt
import parsedatetime.parsedatetime_consts as pdc

# for parsing argument lists
import json, urllib

# merges in the variables for this context
# call this right before you render to response
def merge_contextuals(context, request, patientid):
    # update our context if it isn't already
    request.session['context'] = 'patients'
    
    context.update({
        'context': 'patients',
        'selected_patientid': patientid,
        'current_page': request.path,
        'patients': Patient.objects.all()
        })

@login_required
def processes(request, patientid):
    field_vars = {
        'section': 'processes',
        'tasktemplates': TaskTemplate.objects.all(),
        'pending_processes': Process.objects.get_pending_processes().filter(patient__id=patientid).order_by('add_date'),
        'current_processes': Process.objects.get_current_processes().filter(patient__id=patientid).order_by('add_date'),
        'completed_processes': Process.objects.get_completed_processes().filter(patient__id=patientid).order_by('add_date'),
        }
    
    merge_contextuals(field_vars, request, patientid)
    return render_to_response('dashboard/contexts/patients/processes.html', field_vars, context_instance=RequestContext(request))

@login_required
def tasks(request, patientid):
    field_vars = {
        'section': 'tasks',
        'tasktemplates': TaskTemplate.objects.all(),
        'pending_tasks': ScheduledTask.objects.filter(patient__id=patientid,completed=False).order_by('schedule_date'),
        'current_sessions': Session.objects.get_current_sessions().filter(patient__id=patientid).order_by('add_date'),
        'completed_sessions': Session.objects.get_completed_sessions().filter(patient__id=patientid).order_by('add_date'),
        }
    
    merge_contextuals(field_vars, request, patientid)
    return render_to_response('dashboard/contexts/patients/tasks.html', field_vars, context_instance=RequestContext(request))

@login_required
def history(request, patientid):
    field_vars = {
        'section': 'history',
        'patient': Patient.objects.get(pk=patientid)
        }
        
    if 'from' in request.GET:
        # parse at least the from field, and preferably the to field as well
        p = pdt.Calendar()
        from_clean = urllib.unquote(request.GET['from'].replace('+',' '))
        from_time = p.parse(from_clean)
        from_datetime = datetime.fromtimestamp(time.mktime(from_time[0]))

        field_vars['from'] = from_clean
        if 'custom' in request.GET: field_vars['custom'] = 'true'

        if 'to' not in request.GET or request.GET['to'].strip() == "":
            # use only the from field
            field_vars['processes'] = Process.objects.filter(patient__id=patientid,add_date=from_datetime)
        else:
            # attempt to parse to, since it's here
            to_clean = urllib.unquote(request.GET['to'].replace('+',' '))
            to_time = p.parse(to_clean)

            field_vars['to'] = to_clean
            
            if (to_time[1] > 0):
                # it was parseable, make the range reflect this
                to_datetime = datetime.fromtimestamp(time.mktime(to_time[0]))
                field_vars['processes'] = Process.objects.filter(patient__id=patientid,add_date__gte=from_datetime,add_date__lte=to_datetime)
            else:
                # it was unparseable, just use from
                field_vars['processes'] = Process.objects.filter(patient__id=patientid,add_date__gte=from_datetime)
    else:
        field_vars['processes'] = Process.objects.filter(patient__id=patientid)
    
    merge_contextuals(field_vars, request, patientid)
    return render_to_response('dashboard/contexts/patients/history.html', field_vars, context_instance=RequestContext(request))

@login_required
def calendar(request, patientid):
    field_vars = {
        'section': 'calendar',
        'patient': Patient.objects.get(pk=patientid),
        'processes': Process.objects.filter(patient__id=patientid),
        'tasks':  ScheduledTask.objects.filter(patient__id=patientid)
        }
    
    merge_contextuals(field_vars, request, patientid)
    return render_to_response('dashboard/contexts/patients/calendar.html', field_vars, context_instance=RequestContext(request))

@login_required
def default(request):
    # add in the list of users so we can draw the user chooser
    field_vars = {}
    
    # and render the full page
    merge_contextuals(field_vars, request, None)
    return render_to_response('dashboard/contexts/patients/main.html', field_vars, context_instance=RequestContext(request))

# =================================================================
# ==== Forms for adding Users, ScheduledTasks, Processes
# =================================================================

from django import forms

# the custom prefix used for custom argument fields
CUSTOM_FIELD_PREFIX = "_custom_arg_"

@login_required
def add_patient(request):
    if request.method == 'POST':
        np = Patient(
            address = request.POST['address'],
            first_name = request.POST['first_name'],
            last_name = request.POST['last_name']
            )
        np.save()

        # return HttpResponseRedirect(reverse('taskmanager.views.scheduler'))
        # we redirect them to the patient's new process page
        return HttpResponseRedirect('/taskmanager/patients/%d/processes/' % (np.id))

@login_required
def add_scheduled_task(request):
    if request.method == 'POST':
        template = TaskTemplate.objects.get(pk=int(request.POST['task']))

        p = pdt.Calendar()
        parsed_date = p.parse(request.POST['scheduled_date'] + " " + request.POST['scheduled_time'])
        parsed_datetime = datetime.fromtimestamp(time.mktime(parsed_date[0]))
        
        nt = ScheduledTask(
            patient = Patient.objects.get(pk=int(request.POST['patient'])),
            task = template.task,
            schedule_date = parsed_datetime,
            arguments = template.arguments
            )
        nt.save()

        # return HttpResponseRedirect(reverse('taskmanager.views.scheduler'))
        return HttpResponseRedirect(request.POST['return_page'])

@login_required
def add_scheduled_process(request):
    global CUSTOM_FIELD_PREFIX
    
    if request.method == 'POST':
        template = TaskTemplate.objects.get(pk=int(request.POST['task']))
        patient = Patient.objects.get(pk=int(request.POST['patient']))

        p = pdt.Calendar()
        parsed_date = p.parse(request.POST['scheduled_date'] + " " + request.POST['scheduled_time'])
        parsed_datetime = datetime.fromtimestamp(time.mktime(parsed_date[0]))

        # collect the custom arguments into a dict
        custom_args = {}
        for k in request.POST:
            if k.startswith(CUSTOM_FIELD_PREFIX):
                custom_args[k[len(CUSTOM_FIELD_PREFIX):]] = request.POST[k]
        # update the original arguments with the custom ones
        combined_args = json.loads(template.arguments)
        combined_args.update(custom_args)
        # and delete any keys that are still 'templated'
        for k in filter(lambda x: str(combined_args[x]).startswith("?"), combined_args):
            del combined_args[k]

        # create a Process under which to group these tasks
        np = Process(
            name=template.name,
            creator=request.user.get_profile(),
            patient=patient
            )
        np.save()

        try:
            nt = ScheduledTask(
                patient = patient,
                task = template.task,
                process = np,
                schedule_date = parsed_datetime,
                arguments = json.dumps(combined_args)
            )
            nt.save()
        except:
            # remove the process we just added
            np.delete()
            # and continue the exception
            raise

        # return HttpResponseRedirect(reverse('taskmanager.views.scheduler'))
        return HttpResponseRedirect(request.POST['return_page'])

# ===================================================================
# === AJAX routine for getting a tasktemplate's custom fields
# ===================================================================

def get_tasktemplate_fields(request, tasktemplateid):
    global CUSTOM_FIELD_PREFIX

    template = TaskTemplate.objects.get(pk=int(tasktemplateid))

    arguments = json.loads(template.arguments)
    response = HttpResponse()

    row_template = "\t<tr><td class=\"label\">%(label)s:</td><td>%(control)s</td></tr>\n"

    response.write("<table class=\"vertical nested_table\">\n")

    # loop through the top-level arguments whose values are prefixed with "?"
    for k in arguments:
        val = arguments[k][1::]
        label = k.replace("_"," ")

        if val == "CheckboxInput":
            response.write(row_template % {'label': label, 'control': '<input type="checkbox" name="%s%s" />' % (CUSTOM_FIELD_PREFIX, k)})
        elif val == "TextInput":
            response.write(row_template % {'label': label, 'control': '<input type="text" name="%s%s" />' % (CUSTOM_FIELD_PREFIX, k)})
        else:
            response.write(row_template % {'label': label, 'control': '%s' % arguments[k]})

    response.write("</table>\n")

    return response
