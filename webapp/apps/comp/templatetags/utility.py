import base64
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


@register.filter
def pprint_json(data):
    if isinstance(data, dict):
        try:
            return json.dumps(data, indent=4)
        except Exception:
            pass
        return data


@register.filter
def pic_encode(data):
    return base64.b64encode(data).decode("utf-8")
