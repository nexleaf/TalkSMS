from django import template
from django.template import Library
from django.template import Template, Context
from django.template.loader import render_to_string
from taskmanager.models import *

import json

register = Library()

@register.filter
def display_alert(alert,summary=False):
    try:
        field_vars = {'alert': alert, 'status': alert.alert_type.status, 'args': json.loads(alert.arguments), 'is_summary': summary}

        fv_context = Context(field_vars)
        
        # render the title and possibly the body to variables
        title_template = Template(alert.alert_type.title_template)
        field_vars['title'] = title_template.render(fv_context)
        message_template = Template(alert.alert_type.message_template)
        if not summary: field_vars['message'] = message_template.render(fv_context)

        # render the template with the alert as its context
        return render_to_string('alerts/Alert.html', field_vars)
    except:
        return ""

# =================================================
# === alert HUD custom tag
# =================================================

@register.inclusion_tag("alerts/Alert_HUD.html", takes_context=True)
def alert_HUD(context):
    # get the task data collector service
    service = Service.objects.get(name="Task Data Collector")
    # if it doesn't exist, we can't do much
    if service == None: return {}
    # get the ID of the service, too
    serviceid = str(service.id)
        
    # grab list of pending alerts
    request = context['request']
    if 'alerts_reviewed_on' in request.session and serviceid in request.session['alerts_reviewed_on']:
        # they've marked this service before, so only get the pending alerts for this one
        pending_alerts = Alert.objects.filter(alert_type__service__id=serviceid, add_date__gte=request.session['alerts_reviewed_on'][serviceid])
    else:
        # if they've never marked their alerts read before, all alerts are pending
        pending_alerts = Alert.objects.filter(alert_type__service__id=serviceid)
    
    return {"serviceid": serviceid, "pending_alerts": pending_alerts, "request": context['request']}
