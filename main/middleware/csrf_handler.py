"""
Custom CSRF failure handler for API endpoints
Returns JSON responses instead of HTML for API requests
"""
from django.http import JsonResponse
from django.http import HttpResponseForbidden
from django.views.csrf import csrf_failure as default_csrf_failure

# Try to import CSRF reason constants, fallback if not available
# Different Django versions have different constant names
REASON_NO_CSRF_COOKIE = None
REASON_BAD_TOKEN = None
REASON_MALFORMED_REFERER = None
REASON_INSECURE_REFERER = None
REASON_INCORRECT_LENGTH = None

# Try importing constants that might exist
try:
    from django.middleware.csrf import REASON_NO_CSRF_COOKIE
except ImportError:
    pass

try:
    from django.middleware.csrf import REASON_BAD_TOKEN
except ImportError:
    pass

try:
    from django.middleware.csrf import REASON_MALFORMED_REFERER
except ImportError:
    pass

try:
    from django.middleware.csrf import REASON_INSECURE_REFERER
except ImportError:
    pass

try:
    from django.middleware.csrf import REASON_INCORRECT_LENGTH
except ImportError:
    pass


def csrf_failure_view(request, reason=""):
    """
    Custom CSRF failure handler that returns JSON for API endpoints
    and falls back to default behavior for regular page requests
    """
    try:
        # Check if this is an API request
        path = getattr(request, 'path', '')
        content_type = getattr(request, 'content_type', '')
        accept_header = request.META.get('HTTP_ACCEPT', '')
        
        is_api_request = (
            path.startswith('/api/') or
            content_type == 'application/json' or
            'application/json' in accept_header
        )
        
        if is_api_request:
            # Map Django CSRF failure reasons to user-friendly messages
            reason_str = str(reason) if reason else ''
            reason_lower = reason_str.lower()
            
            # Check for specific error messages using string matching (more reliable across Django versions)
            if 'incorrect length' in reason_lower:
                error_message = (
                    'CSRF token has incorrect length. The token must be exactly 64 characters. '
                    'Since cookies are HttpOnly, you cannot read the token from cookies. '
                    'You MUST call GET /api/csrf/ or GET /api/csrf-token/ to get a fresh token, '
                    'then send it in the X-CSRFToken header (uppercase). '
                    'Example: const response = await fetch("/api/csrf/", {credentials: "include"}); '
                    'const {csrfToken} = await response.json(); '
                    'Then use csrfToken in X-CSRFToken header.'
                )
            elif 'no csrf cookie' in reason_lower or (REASON_NO_CSRF_COOKIE and reason == REASON_NO_CSRF_COOKIE):
                error_message = 'CSRF cookie not set. Please ensure cookies are enabled and you have visited a page that sets the CSRF cookie. Try calling GET /api/csrf-token/ first.'
            elif 'bad token' in reason_lower or 'missing or incorrect' in reason_lower or (REASON_BAD_TOKEN and reason == REASON_BAD_TOKEN):
                error_message = 'CSRF token missing or incorrect. The token may be empty, truncated, or malformed. Please ensure you are reading the full token from the csrftoken cookie and sending it in the X-CSRFToken header.'
            elif 'malformed referer' in reason_lower or (REASON_MALFORMED_REFERER and reason == REASON_MALFORMED_REFERER):
                error_message = 'Referer header is malformed.'
            elif 'insecure referer' in reason_lower or (REASON_INSECURE_REFERER and reason == REASON_INSECURE_REFERER):
                error_message = 'Referer header is insecure. Please ensure you are using HTTPS in production.'
            else:
                error_message = f'CSRF verification failed: {reason_str}. Please refresh the page and try again.'
            
            return JsonResponse({
                'success': False,
                'error': error_message,
                'csrf_error': True,
                'reason': reason_str,
                'help': 'Ensure you are sending the CSRF token in the X-CSRFToken header. Get a fresh token by calling GET /api/csrf-token/'
            }, status=403)
        
        # For non-API requests, use Django's default CSRF failure view
        return default_csrf_failure(request, reason)
    except Exception as e:
        # If there's an error in the handler itself, return a simple JSON error
        # This prevents the handler from causing a 500 error
        return JsonResponse({
            'success': False,
            'error': 'CSRF verification failed',
            'csrf_error': True,
            'handler_error': str(e) if hasattr(e, '__str__') else 'Unknown error'
        }, status=403)
