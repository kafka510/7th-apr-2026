"""
Middleware to normalize CSRF token header names
Django's CSRF middleware expects X-CSRFToken, but some clients send X-Csrftoken
This middleware normalizes the header name before CSRF middleware processes it
"""
import logging
from django.utils.deprecation import MiddlewareMixin

logger = logging.getLogger(__name__)


class CSRFHeaderNormalizerMiddleware(MiddlewareMixin):
    """
    Normalizes CSRF token header names to X-CSRFToken before CSRF middleware processes the request.
    This helps with case-sensitivity issues where frontend sends X-Csrftoken instead of X-CSRFToken.
    Also validates token length and logs issues for debugging.
    """
    
    def process_request(self, request):
        """
        Normalize CSRF token header names before CSRF middleware processes the request.
        """
        # Django converts all headers to uppercase with HTTP_ prefix and replaces hyphens with underscores
        # So 'X-Csrftoken' becomes 'HTTP_X_CSRFTOKEN', 'X-CSRF-Token' becomes 'HTTP_X_CSRF_TOKEN', etc.
        
        # Check all possible CSRF header variations (Django normalizes them all to HTTP_X_* format)
        csrf_token = None
        found_header = None
        
        # Search through all META keys for CSRF token headers (case-insensitive)
        # Django converts headers, so we need to check the normalized form
        for key, value in request.META.items():
            key_lower = key.lower()
            # Look for any header that contains 'csrf' and 'token'
            if 'csrf' in key_lower and 'token' in key_lower:
                csrf_token = value
                found_header = key
                break
        
        # Also check the standard header name explicitly
        if not csrf_token and 'HTTP_X_CSRFTOKEN' in request.META:
            csrf_token = request.META['HTTP_X_CSRFTOKEN']
            found_header = 'HTTP_X_CSRFTOKEN'
        
        # If we found a token, validate and normalize it
        if csrf_token:
            # Strip whitespace (in case frontend adds spaces)
            csrf_token = csrf_token.strip()
            
            # Validate token length (should be 64 characters for Django CSRF tokens)
            token_length = len(csrf_token) if csrf_token else 0
            
            # If token is malformed, remove it completely so Django can use cookie fallback
            if token_length != 64:
                logger.warning(
                    f"CSRF token in header has incorrect length: {token_length} (expected 64). "
                    f"Header: {found_header}, Path: {request.path}, "
                    f"Token preview: {csrf_token[:20] if token_length > 0 else 'EMPTY'}..."
                )
                
                # Remove ALL CSRF token headers (including any case variations)
                # This allows Django's CSRF middleware to fall back to cookie validation
                headers_to_remove = []
                for key in list(request.META.keys()):
                    key_lower = key.lower()
                    if 'csrf' in key_lower and 'token' in key_lower:
                        headers_to_remove.append(key)
                
                for header in headers_to_remove:
                    del request.META[header]
                # Don't set HTTP_X_CSRFTOKEN with invalid token
                # Let Django's CSRF middleware handle it (it will check cookie as fallback)
                return None
            
            # Normalize to standard header name (only if token is valid)
            if found_header != 'HTTP_X_CSRFTOKEN':
                # Remove the old header
                if found_header in request.META:
                    del request.META[found_header]
                # Set the standard header name with cleaned token
                request.META['HTTP_X_CSRFTOKEN'] = csrf_token
        
        return None
