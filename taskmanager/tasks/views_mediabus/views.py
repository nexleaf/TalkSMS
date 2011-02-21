import sys

from django.core.urlresolvers import reverse
from django.shortcuts import render_to_response
from django.contrib.auth.decorators import login_required
from django.template import RequestContext, Context, loader
from django.core.paginator import Paginator, InvalidPage, EmptyPage
from django.http import HttpResponseRedirect, HttpResponseNotFound, HttpResponse

from taskmanager.tasks.models import *
from taskmanager.models import *

@login_required
def datadisplay(request):

    msgdata = MediaBusRawLog.objects.all()
    paginator = Paginator(msgdata, 50)

    try:
        page = int(request.GET.get('page', '1'))
    except ValueError:
        page = 1
    
    try:
        d = paginator.page(page)
    except (EmptyPage, InvalidPage):
        d = paginator.page(paginator.num_pages)

    t = loader.get_template('mediabus/datadisplay.html')
    c = RequestContext(request, {'msgout': d, 'mdata': msgdata})
    return HttpResponse(t.render(c))


@login_required
def unmatched(request):

    msgdata = UnmatchedMessages.objects.all()
    paginator = Paginator(msgdata, 50)

    try:
        page = int(request.GET.get('page', '1'))
    except ValueError:
        page = 1
    
    try:
        d = paginator.page(page)
    except (EmptyPage, InvalidPage):
        d = paginator.page(paginator.num_pages)

    t = loader.get_template('mediabus/unmatchedmessages.html')
    c = RequestContext(request, {'msgout': d, 'mdata': msgdata})
    return HttpResponse(t.render(c))
