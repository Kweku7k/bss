from functools import wraps
from django.contrib import messages
from django.shortcuts import redirect

def role_required(perm_name):
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            if request.user.has_perm(perm_name) or request.user.is_superuser:
                return view_func(request, *args, **kwargs)
            else:
                messages.error(request, 'You do not have permission to access this page.')
                return redirect(request.META.get('HTTP_REFERER', '/'))
        return wrapper
    return decorator
