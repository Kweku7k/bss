from django import template

register = template.Library()


@register.filter
def get_item(dictionary, key):
    return dictionary.get(key, '')


@register.filter
def prettify_tag(value):
    return value.replace("_", " ").title()


@register.filter
def get_item(dictionary, key):
    """Get an item from a dictionary."""
    if dictionary:
        return dictionary.get(key)
    return None