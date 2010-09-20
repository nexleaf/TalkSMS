import json

from taskmanager.models import *

class UnparseableException(Exception):
    def __init__(self, value):
        self.value = value
    def __str__(self):
        return repr(self.value)

class BaseMachine(object):
    """
    A base class for creating state machines that interact with the patient.

    Each state machine instance is associated with a patient via the TaskManager.
    The state machine supports the method handle() to process dispatched
    messages from the TaskManager.
    """
    def __init__(self, session, router, patient, args):
        """
        Creates an instance of our machine, storing the arguments we
        were given to a field.
        """
        self.router = router
        self.session = session
        self.patient = patient
        self.args = json.loads(args)
        self.state = "idle"

    def start(self):
        # allow our machine to take initiative
        pass

    def timeout(self):
        # allow our machine to react to timeouts
        # by default let's just stop running if we time out
        return None

    def handle(self, message):
        # allow the message to pass on unhandled by default
        return False

    def get_state(self):
        if self.state is None:
            return "undefined"
        return self.state

    # helper method for setting a timeout
    def set_timeout(self, timeout_date):
        self.session.timeout_date = timeout_date
        self.session.save()

    # helper method for scheduling tasks
    def schedule_task(self, taskname, date, arguments={}):
        nt = ScheduledTask(
            patient = self.patient,
            task = Task.objects.get(className=taskname),
            process = self.session.process,
            arguments = json.dumps(arguments),
            schedule_date = date
        )
        nt.save()

    # helper for logging
    def log_message(self, message, outgoing):
        nm = SessionMessage(
            session = self.session,
            message=message,
            outgoing=outgoing
            )
        nm.save()
