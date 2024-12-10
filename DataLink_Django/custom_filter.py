from django import templates

register = templates.Library()

@register.filter
def split(value, delimiter=','):
    return value.split(delimiter)
