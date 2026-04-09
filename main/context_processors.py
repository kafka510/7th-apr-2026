from .permissions import get_all_features, get_all_roles, user_has_feature
from accounts.decorators import get_user_role
from django.conf import settings
import time

def permissions_context(request):
    """
    Context processor to make permissions available in templates.
    
    This adds the following variables to all templates:
    - user_permissions: Dict of features the current user can access
    - user_role: Current user's role
    - permission_checks: Dict of boolean permission checks for each feature
    - all_features: All available features
    - all_roles: All available roles
    """
    context = {
        'user_permissions': {},
        'user_role': None,
        'permission_checks': {},
        'all_features': get_all_features(),
        'all_roles': get_all_roles(),
    }
    
    if request.user.is_authenticated:
        user_role = get_user_role(request)
        if user_role:
            context['user_role'] = user_role
            accessible_features = {}
            for feature_name, label in get_all_features().items():
                has_access = user_has_feature(request.user, feature_name)
                context['permission_checks'][feature_name] = has_access
                if has_access:
                    accessible_features[feature_name] = label
            context['user_permissions'] = accessible_features
    
    # Note: user_role is available in context, access via user_profile.role in views
    
    return context

def security_notice_context(request):
    """
    Context processor to add security notice message to all templates.
    """
    return {
        'security_notice': {
            'enabled': True,
            'message': 'Please note that due to enhanced security measures, your account or IP address may be temporarily restricted if any suspicious activity is detected. Should you encounter any inconvenience, you may contact the Central Team in India for assistance.',
            'type': 'info',  # info, warning, success, error
            'dismissible': True,
            'show_once_per_session': True,
        }
    } 
    
def app_version(request):
    """
    Makes the app version available in all templates for cache busting
    Usage in template: {{ APP_VERSION }}
    """
    return {
        'APP_VERSION': getattr(settings, 'STATIC_VERSION', '1.0.0'),
        'CACHE_BUST_TIMESTAMP': str(int(time.time())),
        'DJANGO_VITE_DEV_MODE': getattr(settings, 'DJANGO_VITE_DEV_MODE', False),
    }
