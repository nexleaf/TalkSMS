import rapidsms
import machine, appt_machine

from django.template.loader import render_to_string

from datetime import datetime, timedelta
import time
import parsedatetime.parsedatetime as pdt
import parsedatetime.parsedatetime_consts as pdc

from taskmanager.models import *

class AppointmentRequestMachine(appt_machine.BaseAppointmentMachine):
    MAX_ATTEMPTS = 3
    RESEND_IN_HOURS = 24
    
    def __init__(self, session, router, patient, args):
        super(AppointmentRequestMachine, self).__init__(session, router, patient, args)

        # init our dispatch table 
        self.state_dispatch = {
                'awaiting_response': self.AwaitingResponseState
            }
        self.state = 'idle'

    # just sends out the default message
    def send_request_msg(self):
        # we assume that we have a reference to the patient
        # send them a nice greeting message
        conn = rapidsms.connection.Connection(self.router.get_backend('email'), self.patient.address)
        message = rapidsms.message.EmailMessage(connection=conn)
        message.subject = "Appointment Schedule Request"
        message.text = render_to_string('tasks/appts/request.html', {'patient': self.patient, 'args': self.args})
        message.send()
        self.log_message(message.text, outgoing=True)

    def start(self):
        self.attempts = 1
        self.send_request_msg()
        # set a timeout to repeat this action later
        self.set_timeout(datetime.now() + timedelta(hours=AppointmentRequestMachine.RESEND_IN_HOURS))
        # and wait for a response
        self.state = 'awaiting_response'

        return True # we handled it, thus return True

    def timeout(self):
        # check the number of attempts and see if we've gone over the maximum
        # if not, resend...if we have, terminate
        if self.attempts < AppointmentRequestMachine.MAX_ATTEMPTS:
            self.attempts += 1
            self.send_request_msg()
            self.set_timeout(datetime.now() + timedelta(hours=AppointmentRequestMachine.RESEND_IN_HOURS)) # also reset the timeout
            # if we return true, it clears the timeout; we return false because we're still handling it
            return False
        else:
            # return None to indicate that the machine is done and should be removed
            # FIXME: we may also want to raise a warning to the admin here
            return None

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
        # parse the message and determine the transition
        stripped_msg = message.text.strip().lower()
        if stripped_msg == "no" or stripped_msg == "cancel" :
            # we shouldn't bother them anymore
            return None

        # attempt to parse a date out of the message
        p = pdt.Calendar()
        result = p.parse(message.text)

        if (result[1] == 0):
            # we send them a "sorry" message...alternatively, we could throw an Unparseable
            # and let some other state machine take a crack at it
            message.text = "Sorry, I couldn't understand your input; please try again."
            message.respond(message.text)
            self.log_message(message.text, outgoing=True)
            # reset the timeout
            self.set_timeout(datetime.now() + timedelta(hours=AppointmentRequestMachine.RESEND_IN_HOURS))
            return 'awaiting_response'
        else:
            # the date they chose is in result[0]
            self.reschedule(message, result[0])
            return None
        
