"""
CORS decorator for API endpoints
Adds Cross-Origin Resource Sharing headers to allow iframe access
"""

from functools import wraps
from django.http import JsonResponse


def cors_allow_same_site(view_func):
    """
    Decorator to add CORS headers for same-site origins
    Allows API requests from iframes on the same domain
    
    Usage:
        @login_required
        @cors_allow_same_site
        def my_api_view(request):
            return JsonResponse({'data': 'value'})
    """
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        # Handle preflight OPTIONS request
        if request.method == 'OPTIONS':
            response = JsonResponse({}, status=200)
        else:
            response = view_func(request, *args, **kwargs)
        
        # Get the origin from request
        origin = request.META.get('HTTP_ORIGIN', '')
        
        # Allowed origins (your domains)
        allowed_origins = [
            'https://peakpulse-dev.xyz',
            'https://www.peakpulse-dev.xyz',
            'http://localhost:8000',
            'http://127.0.0.1:8000',
        ]
        
        # Add CORS headers if origin is allowed or for same-domain requests
        if origin in allowed_origins:
            response['Access-Control-Allow-Origin'] = origin
            response['Access-Control-Allow-Methods'] = 'GET, POST, OPTIONS'
            response['Access-Control-Allow-Headers'] = 'Content-Type, Authorization, X-CSRFToken'
            response['Access-Control-Allow-Credentials'] = 'true'
        elif not origin:
            # For same-domain requests (no origin header)
            # This handles iframe requests from same domain
            response['Access-Control-Allow-Origin'] = '*'
            response['Access-Control-Allow-Methods'] = 'GET, POST, OPTIONS'
            response['Access-Control-Allow-Headers'] = 'Content-Type, Authorization, X-CSRFToken'
            response['Access-Control-Allow-Credentials'] = 'true'
        
        return response
    
    return wrapper


def cors_allow_all(view_func):
    """
    Decorator to add CORS headers allowing all origins
    Use with caution - less secure than cors_allow_same_site
    
    Usage:
        @login_required
        @cors_allow_all
        def my_public_api_view(request):
            return JsonResponse({'data': 'value'})
    """
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        # Handle preflight OPTIONS request
        if request.method == 'OPTIONS':
            response = JsonResponse({}, status=200)
        else:
            response = view_func(request, *args, **kwargs)
        
        # Add CORS headers for all origins
        response['Access-Control-Allow-Origin'] = '*'
        response['Access-Control-Allow-Methods'] = 'GET, POST, OPTIONS'
        response['Access-Control-Allow-Headers'] = 'Content-Type, Authorization, X-CSRFToken'
        response['Access-Control-Allow-Credentials'] = 'true'
        
        return response
    
    return wrapper

