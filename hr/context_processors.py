def base_context(request):
    return {
        'user_groups': request.user.groups.values_list('name', flat=True) if request.user.is_authenticated else []
    }