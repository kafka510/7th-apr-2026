from django.http import HttpResponseForbidden, JsonResponse
from django.shortcuts import redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required as django_login_required
from functools import wraps
from main.models import UserProfile as main_userprofile
from main.permissions import get_allowed_roles, user_has_feature, user_has_app_access, _feature_app


def login_required(view_func):
    """
    JSON-aware version of Django's login_required decorator.
    Returns JSON error for JSON/AJAX requests instead of redirecting to login page.
    """
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        # Check if this is a JSON/AJAX request
        is_json_request = (
            request.method == 'POST' and (
                request.headers.get('Content-Type', '').startswith('application/json') or
                request.headers.get('X-Requested-With') == 'XMLHttpRequest' or
                request.content_type == 'application/json' or
                'application/json' in request.headers.get('Accept', '')
            )
        )
        
        if not request.user.is_authenticated:
            if is_json_request:
                return JsonResponse({'error': 'Authentication required'}, status=401)
            # For HTML requests, use Django's default login_required behavior
            return django_login_required(view_func)(request, *args, **kwargs)
        
        return view_func(request, *args, **kwargs)
    return _wrapped_view


def role_required(allowed_roles=[]):
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            if not request.user.is_authenticated:
                messages.error(request, 'Please log in to access this page.')
                return redirect('accounts:login')
            try:
                user_profile = main_userprofile.objects.get(user=request.user)
                user_role = user_profile.role
                print(user_profile.role,'*********',user_profile.user)
            except main_userprofile.DoesNotExist:
                messages.error(request, 'User profile not found. Please contact an administrator.')
                return redirect('accounts:login')
            if user_role in allowed_roles:
                return view_func(request, *args, **kwargs)
            messages.error(request, 'You do not have permission to view this page.')
            return redirect('main:unified_operations_dashboard')
        return _wrapped_view
    return decorator

def feature_required(feature_name):
    """
    Decorator that enforces both app access and feature permissions.
    
    This decorator:
    1. Checks if user has access to the app the feature belongs to
    2. Checks if user has the specific feature permission
    
    For JSON/AJAX requests, returns JSON errors instead of HTML redirects.
    
    Usage:
    @feature_required('yield_report')
    @login_required
    def yield_report_view(request):
        return render(request, 'main/Yield Report_v1.html')
    """
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            # Check if this is a JSON/AJAX request
            is_json_request = (
                request.headers.get('Content-Type', '').startswith('application/json') or
                request.headers.get('X-Requested-With') == 'XMLHttpRequest' or
                request.content_type == 'application/json' or
                'application/json' in request.headers.get('Accept', '')
            )
            
            if not request.user.is_authenticated:
                if is_json_request:
                    return JsonResponse({'error': 'Authentication required'}, status=401)
                messages.error(request, 'Please log in to access this page.')
                return redirect('accounts:login')
            
            try:
                user_profile = main_userprofile.objects.get(user=request.user)
                user_role = user_profile.role
            except main_userprofile.DoesNotExist:
                # Create a default profile for the user if it doesn't exist
                user_profile = main_userprofile.objects.create(
                    user=request.user,
                    role='others'  # Default role
                )
                user_role = user_profile.role
                if not is_json_request:
                    messages.info(request, f'Welcome! Your account has been set up with {user_role} permissions.')
            
            # Check app access first (user_has_feature already does this, but be explicit)
            app_key = _feature_app(feature_name)
            if app_key and not user_has_app_access(request.user, app_key):
                if is_json_request:
                    return JsonResponse({
                        'error': f'You do not have access to the {app_key.upper()} application. Please contact an administrator to grant access.'
                    }, status=403)
                messages.error(
                    request, 
                    f'You do not have access to the {app_key.upper()} application. '
                    'Please contact an administrator to grant access.'
                )
                return redirect('main:unified_operations_dashboard')
            
            # Check feature permission
            if not user_has_feature(request.user, feature_name):
                if is_json_request:
                    return JsonResponse({
                        'error': f'You do not have permission to access {feature_name}.'
                    }, status=403)
                messages.error(request, f'You do not have permission to access {feature_name}.')
                return redirect('main:unified_operations_dashboard')
            
            return view_func(request, *args, **kwargs)
        return _wrapped_view
    return decorator


def app_access_required(app_key: str):
    """
    Decorator to enforce app-level access control.
    
    This decorator checks if the user has access to a specific app (web, ticketing, api)
    before allowing access to the view.
    
    Usage:
    @app_access_required('ticketing')
    @login_required
    def ticketing_view(request):
        return render(request, 'ticketing/page.html')
    """
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            if not request.user.is_authenticated:
                messages.error(request, 'Please log in to access this page.')
                return redirect('accounts:login')
            
            if not user_has_app_access(request.user, app_key):
                app_label = app_key.upper() if app_key else 'this application'
                messages.error(
                    request,
                    f'You do not have access to the {app_label} application. '
                    'Please contact an administrator to grant access.'
                )
                return redirect('main:unified_operations_dashboard')
            
            return view_func(request, *args, **kwargs)
        return _wrapped_view
    return decorator

def get_user_role(request):
    """
    Helper function to get the current user's role.
    
    Args:
        request: Django request object
        
    Returns:
        str: User's role or None if not found
    """
    if not request.user.is_authenticated:
        return None
    
    try:
        user_profile = main_userprofile.objects.get(user=request.user)
        return user_profile.role
    except main_userprofile.DoesNotExist:
        return None


def role_required_api(allowed_roles=[]):
    """
    API version of role_required decorator that returns JSON responses
    instead of redirects. Use this for API endpoints.
    
    Usage:
    @role_required_api(allowed_roles=['admin'])
    @login_required
    def api_endpoint(request):
        return JsonResponse({'success': True})
    """
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            if not request.user.is_authenticated:
                return JsonResponse({
                    'success': False,
                    'error': 'Authentication required'
                }, status=401)
            try:
                user_profile = main_userprofile.objects.get(user=request.user)
                user_role = user_profile.role
            except main_userprofile.DoesNotExist:
                return JsonResponse({
                    'success': False,
                    'error': 'User profile not found. Please contact an administrator.'
                }, status=403)
            if user_role in allowed_roles:
                return view_func(request, *args, **kwargs)
            return JsonResponse({
                'success': False,
                'error': 'You do not have permission to perform this action.'
            }, status=403)
        return _wrapped_view
    return decorator