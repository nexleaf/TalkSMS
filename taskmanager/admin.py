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

admin.site.register(Service)
admin.site.register(AlertType)
admin.site.register(Alert)

# admin site visibily for serialzed tasks, as they're some issue here
from tasks.models import *
admin.site.register(SerializedTasks)

# admin visibility for scheduled message reminders
from rapidsms.contrib.scheduler.models import *
admin.site.register(EventSchedule)

