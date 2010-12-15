import datetime, time

import parsedatetime.parsedatetime as pdt
import parsedatetime.parsedatetime_consts as pdc

from django.template import Library
from django.template.defaultfilters import stringfilter

register = Library()

@register.filter(name='parse_date')
@stringfilter
def parse_date(date_string, format="%a %b %d %H:%M:%S %Y"):
    """
    Return a datetime corresponding to date_string, parsed according to format.

    For example, to re-display a date string in another format::

        {{ "01/01/1970"|parse_date:"%m/%d/%Y"|date:"F jS, Y" }}

    """
    try:
        return datetime.datetime.strptime(date_string, format)
    except ValueError:
        return None

@register.filter(name='relative_date')
@stringfilter
def relative_date(date_string): 
    """
    Return a relative date string corresponding to date_string, parsed using parsedatetime.

    Returned string will be "today @ hh:mm p" if it's today,
    "tomorrow @ hh:mm p" if it's tomorrow,
    or "<day of week> @hh:mm p" if it's within a week.
    Anything else is "mm/dd/yyyy" (note the lack of a time).
    """

    try:
        # attempt to parse the input with parsedatetime
        p = pdt.Calendar()
        result = p.parse(date_string)
        date = datetime.datetime.fromtimestamp(time.mktime(result[0]))
        # actually gets the time it was this morning
        rightnow = datetime.datetime.combine(datetime.datetime.now(), datetime.time.min)
        diff = date - rightnow
    except:
        # any exception here should return nothing
        return None

    if diff.days == 0: # Today
        return 'today @' + date.strftime("%-I:%M %p (%m/%d/%Y)") ## at 05:45 PM
    elif diff.days == 1: # Tomorrow
        return 'tomorrow @' + date.strftime("%-I:%M %p (%m/%d/%Y)") ## at 05:45 PM Tomorrow
    elif diff.days < 7: # one week from now
        return date.strftime("%A at %-I:%M %p (%m/%d/%Y)") ## at 05:45 PM Tuesday
    else:
        return 'on ' + date.strftime("%m/%d/%Y") ## on 10/03/1980
