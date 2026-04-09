"""
API-Only User Access Enforcement Middleware
--------------------------------------------
Ensures that users with access_level='api_only' cannot access web pages.
They should only be able to access:
- /api/manual/ (API documentation)
- /api/v1/* (API endpoints)
- /accounts/logout/ (logout)
- /accounts/profile/ (view profile - optional)
"""

from django.shortcuts import redirect
from django.contrib import messages
from django.urls import reverse


class APIOnlyEnforcementMiddleware:
    """Enforce that API-only users cannot access web dashboard pages"""
    
    def __init__(self, get_response):
        self.get_response = get_response
        
        # URLs that API-only users CAN access
        self.allowed_urls = [
            '/api/manual/',
            '/api/v1/',
            '/accounts/logout/',
            '/accounts/profile/',
            '/static/',
            '/media/',
        ]
        
        # URL patterns that should be blocked for API-only users
        # (web dashboard pages)
        self.blocked_url_patterns = [
            '/unified-operations-dashboard/',
            '/portfolio-map/',
            '/kpi-dashboard/',
            '/sales/',
            '/generation-report/',
            '/yield-report/',
            '/revenue-loss/',
            '/bess-performance/',
            '/time-series-dashboard/',
            '/analytics/',
            '/user-management/',
            '/site-onboarding/',
            '/data-upload/',
            '/security-alerts/',
            '/feedback/',
            '/api/dashboard/',  # User API dashboard (not for api-only)
            '/api/admin/',  # Admin pages
        ]
    
    def __call__(self, request):
        # Process the request
        response = self.process_request(request)
        if response:
            return response
        
        # Continue with normal request processing
        response = self.get_response(request)
        return response
    
    def process_request(self, request):
        """Check if API-only user is trying to access web pages"""
        
        # Skip if user is not authenticated
        if not request.user.is_authenticated:
            return None
        
        # Get the current path
        path = request.path
        
        # Check if path is in allowed URLs for API-only users
        for allowed_url in self.allowed_urls:
            if path.startswith(allowed_url):
                return None  # Allow access
        
        # Check if user has API-only access
        try:
            from api.models import APIUser
            api_user = APIUser.objects.get(user=request.user)
            
            # Only enforce for api_only users (not 'both' or 'web_only')
            if api_user.access_level == 'api_only':
                # Check if trying to access blocked web pages
                for blocked_pattern in self.blocked_url_patterns:
                    if path.startswith(blocked_pattern):
                        # Blocked! Redirect to API manual
                        messages.warning(
                            request,
                            'You have API-only access and cannot access web dashboard pages. '
                            'Please use the API endpoints documented below.'
                        )
                        return redirect('api:api_manual')
                
                # Also block access to root/home page
                if path == '/' or path == '/dashboard/' or path.startswith('/main/'):
                    messages.warning(
                        request,
                        'You have API-only access. Please use the API endpoints.'
                    )
                    return redirect('api:api_manual')
        
        except APIUser.DoesNotExist:
            # User doesn't have APIUser record, allow normal access
            pass
        except Exception as e:
            # Log error but don't block access for unexpected errors
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Error in APIOnlyEnforcementMiddleware: {e}")
        
        return None  # Allow access

