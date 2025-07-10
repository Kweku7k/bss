from datetime import timedelta

def base_context(request):
    return {
        'user_groups': request.user.groups.values_list('name', flat=True) if request.user.is_authenticated else []
    }
    
    
def session_expiry(request):
    if request.user.is_authenticated:
        return {
            'session_remaining_seconds': request.session.get_expiry_age()
        }
    return {}