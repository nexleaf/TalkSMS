import sys

from django.shortcuts import render_to_response
from django.http import HttpResponseRedirect, HttpResponseNotFound, HttpResponse
from django.core.urlresolvers import reverse
from django.template import RequestContext

from django.contrib.auth.decorators import login_required

from taskmanager.models import *

# for parsing argument lists
import json, urllib

@login_required
def default(request):
    # if they hadn't viewed a context, just give them the default 'patients' context
    if 'context' not in request.session:
        request.session['context'] = 'patients'

    # render their last-viewed context (for now, until we get some kind of "main dashboard" context)
    return HttpResponseRedirect('/taskmanager/' + str(request.session['context']) + '/')
