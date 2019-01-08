import json

from django import template

from django.core.serializers.json import DjangoJSONEncoder
from django.utils.html import conditional_escape
from django.utils.safestring import mark_safe

register = template.Library()


@register.filter
def add(int1, int2):
    """
    https://groups.google.com/forum/#!topic/django-users/N5veueqXxG8
    """
    return int1 + int2


@register.filter
def dict_get(hash, key):
    """
    https://groups.google.com/forum/#!topic/django-users/N5veueqXxG8
    """
    return hash[key]


@register.filter
def is_truthy(checkbox):
    """
    Decide if checkbox should be on or not:
    - value is set and it is true --> turn on
    - place holder is True and value is not set --> turn on
    """
    def _is_truthy(val):
        if val is True:
            return True
        if val == "True":
            return True
        return False
    placeholder = checkbox.field.widget.attrs["placeholder"]
    value = checkbox.value()
    return _is_truthy(value) or (_is_truthy(placeholder) and value in (None, ""))


@register.filter
def length(list):
    return len(list)


"""
JSON filter implementation courtesy of
https://code.djangoproject.com/ticket/17419 and
https://code.djangoproject.com/attachment/ticket/17419/jsonfilter.py
"""


class SafeJSONEncoder(DjangoJSONEncoder):
    def _recursive_escape(self, o, esc=conditional_escape):
        if isinstance(o, dict):
            return type(o)((esc(k), self._recursive_escape(v))
                           for (k, v) in o.items())
        if isinstance(o, (list, tuple)):
            return type(o)(self._recursive_escape(v) for v in o)
        try:
            return type(o)(esc(o))
        except ValueError:
            return esc(o)

    def encode(self, o):
        value = self._recursive_escape(o)
        return super(SafeJSONEncoder, self).encode(value)


@register.filter('json')
def json_filter(value):
    """
    Returns the JSON representation of ``value`` in a safe manner.
    """
    return mark_safe(json.dumps(value, cls=SafeJSONEncoder))
