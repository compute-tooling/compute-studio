from django import template

register = template.Library()


@register.filter
def col_input_class(param):
    cols = len(param.col_fields)
    if cols == 1:
        return "col-6"
    return "col"


@register.filter
def is_first(arr, item):
    return arr.index(item) == 0
