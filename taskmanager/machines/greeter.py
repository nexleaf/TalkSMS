import rapidsms
import machine

from django.template.loader import render_to_string

class GreeterMachine(machine.BaseMachine):
    def __init__(self, session, router, patient, args):
        super(GreeterMachine, self).__init__(session, router, patient, args)
        self.state = 'idle'

    def start(self):
        # we assume that we have a reference to the patient
        # send them a nice greeting message
        conn = rapidsms.connection.Connection(self.router.get_backend('email'), self.patient.address)
        message = rapidsms.message.EmailMessage(connection=conn)
        message.subject = "Greeter Automated Message"
        message.text = "Hello, %s %s!" % (self.patient.first_name, self.patient.last_name)
        message.send()
        self.log_message(message.text, outgoing=True)
        return None # returning None because this machine is done

    def handle(self, message):
        log_message(message.text, outgoing=False)
        
        # we're going to try to figure out what they're talking about
        message.text = "Hey, %s! Glad to hear from you!" % self.patient.first_name
        message.respond(message.text)
        self.log_message(message.text, outgoing=True)
        return None # no one should ever get here because the handler should be removed
