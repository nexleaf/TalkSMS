import rapidsms
import machine, appt_machine

from django.template.loader import render_to_string

from datetime import datetime, timedelta
import parsedatetime.parsedatetime as pdt
import parsedatetime.parsedatetime_consts as pdc

from taskmanager.models import *

# to access the reschedule() method
from appt_request import AppointmentRequestMachine

class AppointmentFollowupMachine(appt_machine.BaseAppointmentMachine):
    def __init__(self, session, router, patient, args):
        super(AppointmentFollowupMachine, self).__init__(session, router, patient, args)

        # init our dispatch table 
        self.state_dispatch = {
                'awaiting_response': self.AwaitingResponseState
            }
        self.state = 'idle'

    def start(self):
        # we assume that we have a reference to the patient
        # send them a nice greeting message
        conn = rapidsms.connection.Connection(self.router.get_backend('email'), self.patient.address)
        message = rapidsms.message.EmailMessage(connection=conn)
        message.subject = "Appointment Followup"
        message.text =  render_to_string('tasks/appts/followup.html', {'patient': self.patient, 'args': self.args})
        message.send()
        self.log_message(message.text, outgoing=True)
        # set a timeout so that the message eventually ends
        self.set_timeout(datetime.now() + timedelta(hours=4))
        # and wait for a response
        self.state = 'awaiting_response'

        return True # return True because we want this to continue

    def handle(self, message):
        self.log_message(message.text, outgoing=False)
        
        try:
            # execute our current state and get our new state from it
            self.state = self.state_dispatch[self.state](message)
        except machine.UnparseableException:
            # we can't handle it if we can't even parse it
            return False

        if self.state is None:
            # we're in a terminal state; allow the task manager to destroy us
            return None

        # we handled it and moved on to a new state, indicate as much
        return True

    # ==================================================
    # === definitions for each of our states are below
    # ==================================================

    def AwaitingResponseState(self, message):
        text = message.text.strip().lower()

        # attempt to parse a date out of the message
        p = pdt.Calendar()
        result = p.parse(text)

        if (result[1] == 0):
            # assume this is a comment, thank them, and exit
            message.text = "Thank you for your response!"
            message.respond(message.text)
            self.log_message(message.text, outgoing=True)
            return None
        else:
            # the date they chose is in result[0]
            self.reschedule(message, result[0])
            return None
        
