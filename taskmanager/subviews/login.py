import sys

from django.shortcuts import render_to_response
from django.http import HttpResponseRedirect, HttpResponseNotFound, HttpResponse
from django.core.urlresolvers import reverse
from django.template import RequestContext
from taskmanager.models import *

from django.contrib.auth import authenticate, login, logout

def prompt_login(request):
    context = {}
    
    if request.method == "POST":
        username = request.POST['username']
        password = request.POST['password']
        user = authenticate(username=username, password=password)
        if user is not None:
            if user.is_active:
                login(request, user)

                # check if the user has a profile
                try:
                    user.get_profile()
                except:
                    clinician = Clinician(user=user)
                    clinician.save()
                
                # Redirect to a success page.
                if 'next' in request.POST:
                    return HttpResponseRedirect(request.POST['next'])
                else:
                    return HttpResponseRedirect('/taskmanager/')
            else:
                # Return a 'disabled account' error message
                context['error'] = 'this account has been disabled'
        else:
            # Return an 'invalid login' error message.
            context['error'] = 'your username or password is incorrect'
    else:
        # check if we should pass next into the form
        if 'next' in request.GET:
            context['next'] = request.GET['next']
            
    return render_to_response('login.html', context)

def perform_logout(request):
    logout(request)
    # Redirect to a success page.
    return HttpResponseRedirect('/taskmanager/login')
