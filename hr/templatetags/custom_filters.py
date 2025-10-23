from django import template

register = template.Library()


@register.filter
def get_item(dictionary, key):
    return dictionary.get(key, '')


@register.filter
def prettify_tag(value):
    return value.replace("_", " ").title()
