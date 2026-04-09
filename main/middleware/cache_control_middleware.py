"""
Middleware to add cache control headers for static files and API responses
"""
from django.utils.deprecation import MiddlewareMixin


class CacheControlMiddleware(MiddlewareMixin):
    """
    Adds appropriate cache control headers to responses
    - Static files: Cache with version control
    - API endpoints: No cache
    - HTML pages: No cache or short cache
    """
    
    def process_response(self, request, response):
        path = request.path
        
        # Don't cache API responses
        if path.startswith('/api/'):
            response['Cache-Control'] = 'no-cache, no-store, must-revalidate, max-age=0'
            response['Pragma'] = 'no-cache'
            response['Expires'] = '0'
        
        # Don't cache HTML pages (or cache for very short time)
        elif response.get('Content-Type', '').startswith('text/html'):
            # Short cache for HTML pages (5 minutes)
            response['Cache-Control'] = 'no-cache, no-store, must-revalidate, max-age=0'
            response['Pragma'] = 'no-cache'
            response['Expires'] = '0'
        
        # Static files can be cached but should respect version changes
        elif path.startswith('/static/'):
            # Cache static files for 1 hour (since we have version control via query params)
            response['Cache-Control'] = 'public, max-age=3600, must-revalidate'
            # Add ETag support
            if not response.has_header('ETag'):
                response['Vary'] = 'Accept-Encoding'
        
        return response

