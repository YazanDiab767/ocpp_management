def user_permissions(request):
    """Injects the set of allowed page keys into every template context.
    Templates can check: {% if 'customers' in allowed_pages %}"""
    if hasattr(request, 'user') and request.user.is_authenticated:
        return {'allowed_pages': request.user.get_allowed_pages()}
    return {'allowed_pages': set()}
