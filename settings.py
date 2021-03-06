#!/usr/bin/env python
# vim: ai ts=4 sts=4 et sw=4


# -------------------------------------------------------------------- #
#                          MAIN CONFIGURATION                          #
# -------------------------------------------------------------------- #

# django
TIME_ZONE = None
DBTEMPLATES_USE_REVERSION = True
AUTH_PROFILE_MODULE = "taskmanager.Clinician"
LOGIN_URL = "/taskmanager/login"


# you should configure your database here before doing any real work.
# see: http://docs.djangoproject.com/en/dev/ref/settings/#databases
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": "rapidsms.db"
    }
}


# the rapidsms backend configuration is designed to resemble django's
# database configuration, as a nested dict of (name, configuration).
#
# the ENGINE option specifies the module of the backend; the most common
# backend types (for a GSM modem or an SMPP server) are bundled with
# rapidsms, but you may choose to write your own.
#
# all other options are passed to the Backend when it is instantiated,
# to configure it. see the documentation in those modules for a list of
# the valid options for each.
INSTALLED_BACKENDS = {
    #"att": {
    #    "ENGINE": "rapidsms.backends.gsm",
    #    "PORT": "/dev/ttyUSB0"
    #},
    #"verizon": {
    #    "ENGINE": "rapidsms.backends.gsm,
    #    "PORT": "/dev/ttyUSB1"
    #},
    "message_tester": {
        "ENGINE": "rapidsms.backends.bucket"
    },
    "email": {
        "ENGINE": "rapidsms.backends.email",
        "smtp_host": "smtp.gmail.com",
        "smtp_port": 587,
        "imap_host": "imap.gmail.com",
        "imap_port": 993,
        "username": "<username>@gmail.com",
        "password": "<password>",
        "use_tls": "True",
        "poll_interval": "3" 
    }, 
    # "phone": {
    #     "ENGINE": "rapidsms.backends.gsm",
    #     "port": "/dev/ttyUSB0",
    #     "baudrate": 115200,
    #     "use_sim": "True",
    # }
}


# to help you get started quickly, many django/rapidsms apps are enabled
# by default. you may wish to remove some and/or add your own.
INSTALLED_APPS = [
    # the essentials.
    "django_nose",
    "djtables",
    "rapidsms",

    # common dependencies (which don't clutter up the ui).
    "rapidsms.contrib.handlers",
    "rapidsms.contrib.ajax",

    # enable the django admin using a little shim app (which includes
    # the required urlpatterns), and a bunch of undocumented apps that
    # the AdminSite seems to explode without.
    "django.contrib.sites",
    "django.contrib.auth",
    "django.contrib.admin",
    "django.contrib.sessions",
    "django.contrib.contenttypes",
    "rapidsms.contrib.djangoadmin",

    # the rapidsms contrib apps.
    "rapidsms.contrib.default",
    "rapidsms.contrib.export",
    "rapidsms.contrib.httptester",
    "rapidsms.contrib.locations",
    "rapidsms.contrib.messagelog",
    "rapidsms.contrib.messaging",
    "rapidsms.contrib.registration",
    "rapidsms.contrib.scheduler",
#    "rapidsms.contrib.search",
    "rapidsms.contrib.echo",

    # for django-reversion
    # http://wiki.github.com/etianen/django-reversion/getting-started
    "reversion",
    "dbtemplates",
    # for South
    # http://south.aeracode.org/docs/index.html
    "south",
    # our apps
    "taskmanager",
    "taskmanager.tasks"
]


# this rapidsms-specific setting defines which views are linked by the
# tabbed navigation. when adding an app to INSTALLED_APPS, you may wish
# to add it here, also, to expose it in the rapidsms ui.

RAPIDSMS_TABS = [
    
#     ("rapidsms.views.dashboard",                            "Dashboard"),
#     ("rapidsms.contrib.messagelog.views.message_log",       "Message Log"),
#     ("rapidsms.contrib.registration.views.registration",    "Registration"),
#     ("rapidsms.contrib.messaging.views.messaging",          "Messaging"),
#     ("rapidsms.contrib.locations.views.locations",          "Map"),
#     ("rapidsms.contrib.scheduler.views.index",              "Event Scheduler"),
#     ("rapidsms.contrib.httptester.views.generate_identity", "Message Tester"),

]


# -------------------------------------------------------------------- #
#                         BORING CONFIGURATION                         #
# -------------------------------------------------------------------- #


# debug mode is turned on as default, since rapidsms is under heavy
# development at the moment, and full stack traces are very useful
# when reporting bugs. don't forget to turn this off in production.
DEBUG = TEMPLATE_DEBUG = True


# after login (which is handled by django.contrib.auth), redirect to the
# dashboard rather than 'accounts/profile' (the default).
LOGIN_REDIRECT_URL = "/"


# use django-nose to run tests. rapidsms contains lots of packages and
# modules which django does not find automatically, and importing them
# all manually is tiresome and error-prone.
TEST_RUNNER = "django_nose.NoseTestSuiteRunner"


# for some reason this setting is blank in django's global_settings.py,
# but it is needed for static assets to be linkable.
MEDIA_URL = "/static/"


# this is required for the django.contrib.sites tests to run, but also
# not included in global_settings.py, and is almost always ``1``.
# see: http://docs.djangoproject.com/en/dev/ref/contrib/sites/
SITE_ID = 1


# the default log settings are very noisy.
LOG_LEVEL   = "DEBUG"
LOG_FILE    = "/<repo root>/taskmanager.log"
LOG_FORMAT  = "[%(name)s]: %(message)s"
LOG_SIZE    = 0  # just one log 
LOG_BACKUPS = 256 # number of logs to keep


# these weird dependencies should be handled by their respective apps,
# but they're not, so here they are. most of them are for django admin.
TEMPLATE_CONTEXT_PROCESSORS = [
    "django.core.context_processors.auth",
    "django.core.context_processors.debug",
    "django.core.context_processors.i18n",
    "django.core.context_processors.media",
    "django.core.context_processors.request"
]


TEMPLATE_LOADERS = (
    'django.template.loaders.filesystem.load_template_source',
    'django.template.loaders.app_directories.load_template_source',
    'dbtemplates.loader.load_template_source',
)
DBTEMPLATES_CACHE_BACKEND = 'dbtemplates.cache.DjangoCacheBackend'

# -------------------------------------------------------------------- #
#                           HERE BE DRAGONS!                           #
#        these settings are pure hackery, and will go away soon        #
# -------------------------------------------------------------------- #


# these apps should not be started by rapidsms in your tests, however,
# the models and bootstrap will still be available through django.
TEST_EXCLUDED_APPS = [
    "django.contrib.sessions",
    "django.contrib.contenttypes",
    "django.contrib.auth",
    "rapidsms",
    "rapidsms.contrib.ajax",
    "rapidsms.contrib.httptester",
]


# the default ROOT_URLCONF module, bundled with rapidsms, detects and
# maps the urls.py module of each app into a single project urlconf.
# this is handy, but too magical for the taste of some. (remove it?)
ROOT_URLCONF = "rapidsms.djangoproject.urls"


# since we might hit the database from any thread during testing, the
# in-memory sqlite database isn't sufficient. it spawns a separate
# virtual database for each thread, and syncdb is only called for the
# first. this leads to confusing "no such table" errors. so i'm
# defaulting to a temporary file instead.
import os
import tempfile
import sys

if 'test' in sys.argv:
    for db_name in DATABASES:
        DATABASES[db_name]['TEST_NAME'] = os.path.join(
            tempfile.gettempdir(),
            "%s.rapidsms.test.sqlite3" % db_name)


###############################
# TalkSMS Settings
###############################

# Tell's the scheduler to observer the set QUIET HOURS
# TODO: add the actual hours here as settings!
USE_QUIET_HOURS=True

# Determines whether a response is sent when no message matches anything
ALLMATCH_FAIL=True
ALLMATCH_FAIL_RESPONSE="I did not understand your message"


