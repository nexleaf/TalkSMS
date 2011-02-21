#!/usr/bin/env python

# vim: ai ts=4 sts=4 et sw=4

from django.conf.urls.defaults import *

import taskmanager.tasks.views_mediabus.views as mediabus


urlpatterns = patterns('',
                       (r'^mediabusdata/$', mediabus.datadisplay),
                       (r'^mediabusdata/unmatched/$', mediabus.unmatched)
                       )
