from django.contrib.auth import logout
from django.contrib.auth.models import AnonymousUser
from django.utils import timezone
from datetime import timedelta
from django.conf import settings
from django.shortcuts import redirect
from django.contrib import messages
from django.http import HttpResponseRedirect
from django.http import JsonResponse
import time
from django.http import HttpResponseForbidden
from functools import wraps


class SessionTimeoutMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Skip session timeout check for login/logout pages to avoid redirect loops
        skip_paths = ['/accounts/login/', '/accounts/logout/', '/admin/login/']
        
        if any(request.path.startswith(path) for path in skip_paths):
            response = self.get_response(request)
            return response
            
        # Check if user is authenticated
        if request.user.is_authenticated:
            # Get current timestamp
            current_time = time.time()
            
            # Get last activity from session
            last_activity = request.session.get('last_activity', current_time)
            
            # Check if session has expired
            if current_time - last_activity > settings.SESSION_IDLE_TIMEOUT:
                # Session expired, logout user
                logout(request)
                
                # Add a message about session expiry
                messages.warning(request, 'Your session has expired due to inactivity. Please log in again.')

                # API clients should receive JSON, while browser routes keep redirect behavior.
                is_api_request = (
                    request.path.startswith('/api/')
                    or 'application/json' in request.META.get('HTTP_ACCEPT', '')
                )
                if is_api_request:
                    return JsonResponse(
                        {
                            'success': False,
                            'error': 'Session expired due to inactivity. Please log in again.',
                            'session_expired': True,
                        },
                        status=401,
                    )

                # Redirect browser routes to login page
                return HttpResponseRedirect('/accounts/login/')
            else:
                # Update last activity
                request.session['last_activity'] = current_time
        
        response = self.get_response(request)
        return response 
    
