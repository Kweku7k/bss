from functools import wraps
from django.contrib import messages
from django.shortcuts import redirect

def role_required(groups_allowed):
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            user = request.user
            if user.is_authenticated and (user.groups.filter(name__in=groups_allowed).exists() or user.is_superuser):
                return view_func(request, *args, **kwargs)
            else:
                messages.error(request, "Page restricted. You do not have the required permissions.")
                return redirect(request.META.get('HTTP_REFERER', '/'))  # Redirect to previous page or home
        return wrapper
    return decorator
