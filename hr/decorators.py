from functools import wraps
import logging
from django.contrib import messages
from django.http import HttpResponseForbidden
from django.shortcuts import redirect
from hr.models import UserTag

logger = logging.getLogger('activity')


def role_required(allowed_roles=[]):
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            user_groups = [g.lower() for g in request.user.groups.values_list('name', flat=True)]
            allowed = [role.lower() for role in allowed_roles]

            if set(user_groups).intersection(set(allowed)) or request.user.is_superuser:
                return view_func(request, *args, **kwargs)
            else:
                messages.error(request, 'You do not have permission to access this page.')
                return redirect(request.META.get('HTTP_REFERER', '/'))
        return wrapper
    return decorator



def tag_required(tag_name):
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            user = request.user
            user_groups = [g.lower() for g in request.user.groups.values_list('name', flat=True)]

            if user.is_superuser or 'superadmin' in user_groups:
                return view_func(request, *args, **kwargs)

            has_tag = UserTag.objects.filter(user=user, tag__name=tag_name).exists()
            if has_tag:
                return view_func(request, *args, **kwargs)

            logger.warning(f"Access denied: User '{user.username}' tried to access permission '{tag_name}'.")
            messages.error(request, "Access denied. You do not have the required permissions for this feature.")
            return redirect(request.META.get('HTTP_REFERER', '/'))
        return _wrapped_view
    return decorator
