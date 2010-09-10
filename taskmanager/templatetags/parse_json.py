import datetime

from django.template import Library
from django.template.defaultfilters import stringfilter

import json

register = Library()

@stringfilter
def parse_json(json_string):
    """
    Return an object parsed out of the JSON input.
    """
    try:
        collection = json.loads(json_string)

        # build up a table
        out = ""
        for k in collection:
            out += "<tr><td style=\"text-align: left;\"><b>%s:</b></td><td>%s</td></tr>" % (k, collection[k])
        return out
    except ValueError:
        return None

register.filter(parse_json)
