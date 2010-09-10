from django.contrib import admin
from models import *

admin.site.register(Patient)
admin.site.register(Clinician)
admin.site.register(Task)
admin.site.register(TaskTemplate)
admin.site.register(Process)
admin.site.register(Session)
admin.site.register(SessionMessage)
admin.site.register(ScheduledTask)
