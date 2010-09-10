import rapidsms
import machine

from django.template.loader import render_to_string

from datetime import datetime, timedelta
import time
import parsedatetime.parsedatetime as pdt
import parsedatetime.parsedatetime_consts as pdc

from taskmanager.models import *

class BaseAppointmentMachine(machine.BaseMachine):
    def __init__(self, session, router, patient, args):
        super(BaseAppointmentMachine, self).__init__(session, router, patient, args)

    # ==================================================
    # === helper methods below
    # ==================================================
    
    def reschedule(self, message, appt_date):
        p = pdt.Calendar()
        
        # deactivate all the old scheduled tasks on this process
        ScheduledTask.objects.filter(process=self.session.process).update(active=False)

        # sanitize the arguments structure in case we're rescheduling
        if 'nocancel' in self.args: del self.args['nocancel']

        # create a datetime for the scheduler
        appt_datetime = datetime.fromtimestamp(time.mktime(appt_date))

        # schedule a task to remind them before that date
        reminder_date = p.parse("2 days ago", appt_date)
        reminder_datetime = datetime.fromtimestamp(time.mktime(reminder_date[0]))
        reminder_args = {
            'appt_date': appt_datetime.ctime()
            }
        reminder_args.update(self.args) # pass on any arguments from the parent
        self.schedule_task("AppointmentReminderMachine", reminder_datetime, arguments=reminder_args)

        # schedule a task to remind them before that date
        reminder_nightbefore_date = p.parse("1 day ago at 9pm", appt_date)
        reminder_nightbefore_datetime = datetime.fromtimestamp(time.mktime(reminder_nightbefore_date[0]))
        reminder_nightbefore_args = {
            'appt_date': appt_datetime.ctime(),
            'daybefore': 'true',
            'nocancel': 'true'
            }
        reminder_nightbefore_args.update(self.args) # pass on any arguments from the parent
        self.schedule_task("AppointmentReminderMachine", reminder_nightbefore_datetime, arguments=reminder_nightbefore_args)
        
        # schedule a task to remind them the morning of, too
        morning_reminder_date = p.parse("8am", appt_date)
        morning_reminder_datetime = datetime.fromtimestamp(time.mktime(morning_reminder_date[0]))
        morning_args = {
            'appt_date': appt_datetime.ctime(),
            'nocancel': 'true'
            }
        morning_args.update(self.args) # pass on any arguments from the parent
        self.schedule_task("AppointmentReminderMachine", morning_reminder_datetime, arguments=morning_args)
        
        # schedule a followup task
        followup_date = p.parse("4 hours after", appt_date)
        followup_datetime = datetime.fromtimestamp(time.mktime(followup_date[0]))
        followup_args = {
            'appt_date': appt_datetime.ctime()
            }
        followup_args.update(self.args) # pass on any arguments from the parent
        self.schedule_task("AppointmentFollowupMachine", followup_datetime, arguments=followup_args)

        message.text = render_to_string('tasks/appts/rescheduled.html', {
            'patient': self.patient,
            'args': self.args,
            'appt_date': appt_datetime,
            'reminder_date': reminder_datetime})
        message.respond(message.text)
        self.log_message(message.text, outgoing=True)
