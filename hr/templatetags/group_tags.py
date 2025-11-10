from django import template

register = template.Library()


@register.filter(name='has_group')
def has_group(user, group_name):
    return user.groups.filter(name=group_name).exists()


@register.simple_tag(takes_context=True)
def nav_is_active(context, *names):
    """
    Return True when the current request matches any provided url/view names.
    """
    request = context.get("request")
    if not request:
        return False

    match = getattr(request, "resolver_match", None)
    if not match:
        return False

    current_names = set()

    if match.url_name:
        current_names.add(match.url_name)

    if match.view_name:
        current_names.add(match.view_name)

    current_names.update(getattr(match, "namespaces", []))

    for candidate in names:
        if not candidate:
            continue

        if candidate in current_names:
            return True

        if ":" in candidate and match.view_name == candidate:
            return True

    return False
