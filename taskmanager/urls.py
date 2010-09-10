#!/usr/bin/env python
# vim: ai ts=4 sts=4 et sw=4

from django.conf.urls.defaults import *
import taskmanager.views as views
import taskmanager.subviews.login as login
import taskmanager.subviews.dashboard as dashboard
import taskmanager.subviews.details as details

import taskmanager.subviews.contexts.patients as contexts_patients
import taskmanager.subviews.contexts.tasks as contexts_tasks

urlpatterns = patterns('',
    (r'^taskmanager/$', dashboard.default), # redirects to their last-viewed context (or 'patients' if none)
    (r'^taskmanager/login$', login.prompt_login),
    (r'^taskmanager/logout$', login.perform_logout),

    # patients context
    (r'^taskmanager/patients/?$', contexts_patients.default),
    (r'^taskmanager/patients/(?P<patientid>\d+)/processes/?$', contexts_patients.processes),
    (r'^taskmanager/patients/(?P<patientid>\d+)/tasks/?$', contexts_patients.tasks),
    (r'^taskmanager/patients/(?P<patientid>\d+)/history/?$', contexts_patients.history),
    (r'^taskmanager/patients/(?P<patientid>\d+)/calendar/?$', contexts_patients.calendar),

    # patients context: POST targets and an AJAX thing
    (r'^taskmanager/patients/add/?$', contexts_patients.add_patient),
    (r'^taskmanager/tasks/add/?$', contexts_patients.add_scheduled_task),
    (r'^taskmanager/processes/add/?$', contexts_patients.add_scheduled_process),
    (r'^taskmanager/tasktemplates/(?P<tasktemplateid>\d+)/fields/?$', contexts_patients.get_tasktemplate_fields),

    # tasks context
    (r'^taskmanager/tasks/?$', contexts_tasks.default),
    (r'^taskmanager/tasks/(?P<taskid>\d+)/templates/?$', contexts_tasks.templates),
    (r'^taskmanager/tasks/(?P<taskid>\d+)/messages/?$', contexts_tasks.messages),

    # tasks context: POST targets
   (r'^taskmanager/tasks/templates/update/?$', contexts_tasks.update_template),
   (r'^taskmanager/tasks/messages/update/?$', contexts_tasks.update_message),

    # details views
    (r'^taskmanager/processes/(?P<processid>\d+)/details/?$', details.process_details),
    (r'^taskmanager/tasks/(?P<taskid>\d+)/details/?$', details.scheduledtask_details),
    (r'^taskmanager/sessions/(?P<sessionid>\d+)/details/?$', details.session_details),
    (r'^taskmanager/patients/(?P<patientid>\d+)/details/?$', details.patient_details),

    # detail view commands
    (r'^taskmanager/processes/(?P<processid>\d+)/command/?$', details.process_command),
    (r'^taskmanager/tasks/(?P<taskid>\d+)/command/?$', details.scheduledtask_command),
    (r'^taskmanager/sessions/(?P<sessionid>\d+)/command/?$', details.session_command),

    # legacy scheduler views                   
    (r'^taskmanager/scheduler/?$', views.scheduler),
    (r'^taskmanager/scheduler/add/?$', views.add_scheduled_task),
    (r'^taskmanager/scheduler/check_service$', views.check_scheduler),

    # AJAX proxy
    (r'^proxy/(?P<url>.+)$', views.proxy)
)
