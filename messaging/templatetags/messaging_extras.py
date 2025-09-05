from django import template

register = template.Library()

@register.filter
def dict_get(dictionary, key):
    """Get value from dictionary using key"""
    if hasattr(dictionary, 'get'):
        return dictionary.get(key)
    return None

@register.filter
def replace(value, arg):
    """Replace substring in string. Usage: {{ value|replace:"old,new" }}"""
    if arg and ',' in arg:
        old, new = arg.split(',', 1)
        return str(value).replace(old, new)
    return value

@register.filter
def space_to_underscore(value):
    """Convert spaces to underscores"""
    return str(value).replace(' ', '_')

@register.filter
def lower(value):
    """Convert string to lowercase"""
    return value.lower() if value else ''