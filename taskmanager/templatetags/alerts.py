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
