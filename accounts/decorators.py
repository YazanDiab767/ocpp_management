from functools import wraps

from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied

from accounts.models import URL_TO_PAGE


def admin_required(view_func):
    """Allow access only to admin users."""
    @wraps(view_func)
    @login_required
    def wrapper(request, *args, **kwargs):
        if not request.user.is_admin:
            raise PermissionDenied
        return view_func(request, *args, **kwargs)
    return wrapper


def staff_or_admin_required(view_func):
    """Allow access to any authenticated staff or admin user."""
    @wraps(view_func)
    @login_required
    def wrapper(request, *args, **kwargs):
        return view_func(request, *args, **kwargs)
    return wrapper


def page_permission_required(page_key):
    """Only allow access if the user has permission for this page.
    Admins always pass. Staff users must have the page in their permissions."""
    def decorator(view_func):
        @wraps(view_func)
        @login_required
        def wrapper(request, *args, **kwargs):
            if not request.user.has_page_access(page_key):
                raise PermissionDenied
            return view_func(request, *args, **kwargs)
        return wrapper
    return decorator


def auto_page_permission(view_func):
    """Looks up the page key from URL_TO_PAGE using the current URL name,
    then checks permission. Handy for views where you don't want to
    hardcode the page key."""
    @wraps(view_func)
    @login_required
    def wrapper(request, *args, **kwargs):
        url_name = request.resolver_match.url_name
        page_key = URL_TO_PAGE.get(url_name)
        if page_key and not request.user.has_page_access(page_key):
            raise PermissionDenied
        return view_func(request, *args, **kwargs)
    return wrapper
