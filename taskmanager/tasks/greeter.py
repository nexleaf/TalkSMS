import sms, re

class Greeter(object):
    def __init__(self, user, args=None):
        self.args = args

        # set up expected responses before we create the message
        # each consists of a regular expression or match callback
        # and an optional callback that's triggered if it matches the user's input
        r_good = sms.Response('good', match_regex=r'(great|good|ok)', label='good')
        r_bad = sms.Response('bad', match_regex=r'(bad)', label='bad')
        r_unknown = sms.Response('unknown', match_regex=r'.*', label='unknown')
        # initial message, prompts the user for how they're feeling
        # the message has three possible responses: good, bad, and anything else (e.g. unparseable)
        # in practice, the framework will usually handle the unknown case by retransmitting with a generic error message
        m_initial = sms.Message(
            'Hello, how are you?',
            [r_good, r_bad, r_unknown])
        
        # message sent if the user is good
        # note the empty response list indicating that this is a terminal state
        m_good_resp = sms.Message('Glad to hear it!', [])

        # message sent if the user is not so good
        m_bad_resp = sms.Message('Sorry to hear it; hope you feel better soon.', [])
        
        # message sent if it's anything else
        m_unknown_resp = sms.Message('I couldn\'t understand your response, but I hope you\'re well in any case.', [])

        # finally, we construct the graph of messages and responses that will drive this interaction
        # the next-state list must match the responses associated with that node
        self.graph = { m_initial: [m_good_resp, m_bad_resp, m_unknown_resp],
                       m_good_resp: [],
                       m_bad_resp: [],
                       m_unknown_resp: []
                       }

        self.interaction = sms.Interaction(self.graph, m_initial, self.__class__.__name__ + '_interaction')
        
