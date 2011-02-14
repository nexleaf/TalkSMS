import os
import sys

filedir = os.path.dirname(__file__) # this is in the rapidsms directory
runpath = filedir

sys.path.append(os.path.join(runpath,'..'))
sys.path.append(os.path.join(runpath,'.'))
sys.path.append(os.path.join(runpath,'taskmanager'))

rapidsms_installpath = "/usr/local/lib/python2.6/dist-packages/RapidSMS-0.9.5a-py2.6.egg/rapidsms"
sys.path.append(os.path.join(rapidsms_installpath))

os.environ['DJANGO_SETTINGS_MODULE'] = 'cens.settings'
os.environ["RAPIDSMS_HOME"] = runpath

import rapidsms.djangoproject.urls

import django.core.handlers.wsgi
application = django.core.handlers.wsgi.WSGIHandler()
