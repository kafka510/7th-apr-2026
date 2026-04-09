"""
Middleware to intercept static file requests and enforce authentication.
This intercepts requests BEFORE Django's automatic static file serving in development.
Must be placed AFTER AuthenticationMiddleware so request.user is available.
"""

import logging
from django.http import HttpResponseForbidden
from django.conf import settings
from main.views.static_file_views import serve_static_file, serve_media_file

logger = logging.getLogger(__name__)


class StaticFileAuthMiddleware:
    """
    Middleware to intercept static/media file requests and enforce authentication.
    
    This middleware:
    1. Runs AFTER AuthenticationMiddleware (so request.user is available)
    2. Intercepts static/media requests BEFORE they reach URL routing
    3. Uses our authenticated views to serve files with proper security checks
    
    This prevents Django's automatic static file serving from bypassing authentication.
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
        # Log middleware initialization (only once at startup)
        logger.info("StaticFileAuthMiddleware initialized - static files will require authentication")
    
    def __call__(self, request):
        # Intercept static and media file requests
        path = request.path
        
        # Check if this is a static or media file request
        if path.startswith('/static/') or path.startswith('/media/'):
            # Log interception at debug level (only in DEBUG mode)
            logger.debug(f"Static file request intercepted: {path}, user: {request.user.username if request.user.is_authenticated else 'Anonymous'}")
            
            # Extract file path
            if path.startswith('/static/'):
                file_path = path[8:]  # Remove '/static/' prefix
                # Use our authenticated static file view
                try:
                    response = serve_static_file(request, file_path)
                    return response
                except Exception as e:
                    logger.error(f"Error serving static file {file_path}: {e}", exc_info=True)
                    raise
            elif path.startswith('/media/'):
                file_path = path[7:]  # Remove '/media/' prefix
                # Use our authenticated media file view
                try:
                    response = serve_media_file(request, file_path)
                    return response
                except Exception as e:
                    logger.error(f"Error serving media file {file_path}: {e}", exc_info=True)
                    raise
        
        # For all other requests, continue normal processing
        response = self.get_response(request)
        return response
