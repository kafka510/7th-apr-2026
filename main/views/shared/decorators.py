"""
Shared decorators for views
"""
from functools import wraps
from django.http import JsonResponse
import logging

def superuser_required(view_func):
    """Decorator to ensure only superusers can access a view"""
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if not request.user.is_superuser:
            logger = logging.getLogger(__name__)
            logger.warning(f"Unauthorized superuser operation attempt by user {request.user.username} (ID: {request.user.id}) on {view_func.__name__}")
            return JsonResponse({'error': 'Only superusers can perform this operation'}, status=403)
        return view_func(request, *args, **kwargs)
    return _wrapped_view
