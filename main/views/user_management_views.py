"""
User Management views
"""
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required as django_login_required
from accounts.decorators import login_required
from django.http import JsonResponse
from django.contrib.auth.tokens import default_token_generator
from django.utils.http import urlsafe_base64_encode
from django.utils.encoding import force_bytes
from django.core.mail import send_mail, EmailMultiAlternatives
from django.template.loader import render_to_string
import logging
logger = logging.getLogger(__name__)
from django.urls import reverse
from django.contrib import messages
from django.db import transaction
from django.db.models import Q, Count
from django.conf import settings
from django.contrib.auth.models import User

from main.permissions import APP_ACCESS_LABELS, get_roles_for_capability, user_has_capability
from accounts.decorators import feature_required, role_required

# Get roles for user management capability, fallback to admin if empty
_roles = get_roles_for_capability('user_management.manage')
USER_MANAGEMENT_MANAGER_ROLES = _roles if _roles else ['admin']
from ..models import (
    UserProfile, AssetList, ActiveUserSession, UserActivityLog, SecurityAlert,
    UserBlockingLog, BlockedUser
)
import json, csv
from datetime import timedelta
from django.utils import timezone
from django.http import HttpResponse
from .shared.decorators import superuser_required
from main.utils.connection_ip import get_connection_ip_fields_for_log


@feature_required('user_management')
@login_required
def api_user_management_data(request):
    """JSON API endpoint for user management data"""
    try:
        user_profile = UserProfile.objects.get(user=request.user)
    except UserProfile.DoesNotExist:
        pass
    
    # Only admin can see all assets, others see only their assigned assets
    is_admin = user_has_capability(request.user, 'user_management.manage')
    
    if is_admin:
        assets = AssetList.objects.all()
        countries = sorted(set(country.strip() for country in AssetList.objects.values_list('country', flat=True) if country))
        portfolios = sorted(set(portfolio.strip() for portfolio in AssetList.objects.values_list('portfolio', flat=True) if portfolio))
    else:
        try:
            user_profile = UserProfile.objects.get(user=request.user)
            accessible_sites = user_profile.get_accessible_sites()
            assets = accessible_sites
            countries = sorted(set(country.strip() for country in accessible_sites.values_list('country', flat=True) if country))
            portfolios = sorted(set(portfolio.strip() for portfolio in accessible_sites.values_list('portfolio', flat=True) if portfolio))
        except UserProfile.DoesNotExist:
            assets = AssetList.objects.none()
            countries = []
            portfolios = []
    
    # Get filter parameters
    search_query = request.GET.get('search', '').strip()
    role_filter = request.GET.get('role', '').strip()
    status_filter = request.GET.get('status', '').strip()
    
    # Ensure UserProfile exists for inactive users
    if status_filter == '' or status_filter == 'inactive' or status_filter == 'blocked':
        inactive_users_without_profile = User.objects.filter(
            is_active=False
        ).exclude(
            userprofile__isnull=False
        )
        
        for inactive_user in inactive_users_without_profile:
            try:
                UserProfile.objects.get_or_create(
                    user=inactive_user,
                    defaults={
                        'role': 'others',
                        'created_by': request.user if request.user.is_authenticated else None
                    }
                )
            except Exception:
                pass
    
    # Query UserProfiles
    users_queryset = UserProfile.objects.select_related('user').all()
    
    # Apply filters
    if search_query:
        users_queryset = users_queryset.filter(
            Q(user__username__icontains=search_query) |
            Q(user__email__icontains=search_query) |
            Q(user__first_name__icontains=search_query) |
            Q(user__last_name__icontains=search_query)
        )
    
    if role_filter:
        users_queryset = users_queryset.filter(role=role_filter)
    
    if status_filter == 'active':
        users_queryset = users_queryset.filter(user__is_active=True)
    elif status_filter == 'inactive':
        users_queryset = users_queryset.filter(user__is_active=False)
    elif status_filter == 'blocked':
        try:
            from ..models import BlockedUser
            blocked_user_ids = BlockedUser.objects.filter(status='active').values_list('user_id', flat=True)
            users_queryset = users_queryset.filter(user_id__in=blocked_user_ids)
        except:
            pass
    
    users = users_queryset.order_by('-created_at')
    
    # Get counts for badges
    total_users = UserProfile.objects.count()
    active_users = UserProfile.objects.filter(user__is_active=True).count()
    inactive_users = UserProfile.objects.filter(user__is_active=False).count()
    
    # Get blocked users count
    blocked_users_count = 0
    try:
        from ..models import BlockedUser
        blocked_users_count = BlockedUser.objects.filter(status='active').count()
    except:
        pass
    
    # Get blocked IPs count (all active blocked IPs, not limited)
    blocked_ips_count = 0
    try:
        from ..models import BlockedIP
        blocked_ips_count = BlockedIP.objects.filter(status='active').count()
    except:
        pass
    
    # Get activity statistics
    now = timezone.now()
    twenty_four_hours_ago = now - timedelta(hours=24)
    
    active_users_count = 0
    activity_data = []
    security_alerts = 0
    suspicious_activities = []
    
    # Only get activity data if models are available
    if ActiveUserSession and UserActivityLog and SecurityAlert:
        thirty_minutes_ago = now - timedelta(minutes=30)
        active_users_count = ActiveUserSession.objects.filter(
            is_active=True,
            last_activity__gte=thirty_minutes_ago
        ).count()
        
        import pytz
        user_timezone_str = request.GET.get('timezone')
        if not user_timezone_str:
            user_timezone = pytz.timezone('Asia/Kolkata')
        else:
            try:
                user_timezone = pytz.timezone(user_timezone_str)
            except:
                user_timezone = pytz.timezone('Asia/Kolkata')
        
        now_local = timezone.now().astimezone(user_timezone)
        twenty_four_hours_ago_local = now_local - timedelta(hours=24)
        
        for i in range(24):
            hour_start_local = twenty_four_hours_ago_local + timedelta(hours=i)
            hour_end_local = hour_start_local + timedelta(hours=1)
            
            hour_start_utc = hour_start_local.astimezone(pytz.UTC)
            hour_end_utc = hour_end_local.astimezone(pytz.UTC)
            
            hour_activity = UserActivityLog.objects.filter(
                timestamp__gte=hour_start_utc,
                timestamp__lt=hour_end_utc
            ).count()
            
            activity_data.append({
                'hour': hour_start_local.strftime('%H:00'),
                'hour_full': hour_start_local.strftime('%Y-%m-%d %H:00'),
                'timestamp': hour_start_local.isoformat(),
                'count': hour_activity,
                'timezone': str(user_timezone)
            })
        
        security_alerts = SecurityAlert.objects.filter(
            created_at__gte=twenty_four_hours_ago,
            status='open'
        ).count()
        
        # Get suspicious activities
        suspicious_activities_queryset = UserActivityLog.objects.filter(
            is_suspicious=True,
            timestamp__gte=twenty_four_hours_ago
        ).select_related('user').order_by('-timestamp')[:10]
        
        suspicious_activities = [
            {
                'id': activity.id,
                'user': {
                    'id': activity.user.id if activity.user else None,
                    'username': activity.user.username if activity.user else 'Unknown',
                } if activity.user else None,
                'ip_address': activity.ip_address,
                'action': activity.action,
                'resource': activity.resource,
                'timestamp': activity.timestamp.isoformat(),
                'is_suspicious': activity.is_suspicious,
                'risk_level': getattr(activity, 'risk_level', 'medium'),
            }
            for activity in suspicious_activities_queryset
        ]
    else:
        import pytz
        user_timezone = pytz.timezone('Asia/Kolkata')
        now_local = timezone.now().astimezone(user_timezone)
        twenty_four_hours_ago_local = now_local - timedelta(hours=24)
        
        for i in range(24):
            hour_start_local = twenty_four_hours_ago_local + timedelta(hours=i)
            activity_data.append({
                'hour': hour_start_local.strftime('%H:00'),
                'hour_full': hour_start_local.strftime('%Y-%m-%d %H:00'),
                'timestamp': hour_start_local.isoformat(),
                'count': 0,
                'timezone': str(user_timezone)
            })
    
    # Serialize users with login statistics
    from accounts.models import LoginAttempt
    
    users_data = []
    for profile in users:
        username = profile.user.username
        
        # Calculate login statistics from LoginAttempt model
        # All-time successful logins
        successful_logins_all_time = LoginAttempt.objects.filter(
            username=username,
            successful=True
        ).count()
        
        # Successful logins in last 30 days
        thirty_days_ago = timezone.now() - timedelta(days=30)
        successful_logins_30d = LoginAttempt.objects.filter(
            username=username,
            successful=True,
            attempt_time__gte=thirty_days_ago
        ).count()
        
        # All-time failed attempts
        failed_attempts_all_time = LoginAttempt.objects.filter(
            username=username,
            successful=False
        ).count()
        
        # Recent failed attempts (last 24 hours)
        twenty_four_hours_ago = timezone.now() - timedelta(hours=24)
        failed_attempts_recent = LoginAttempt.objects.filter(
            username=username,
            successful=False,
            attempt_time__gte=twenty_four_hours_ago
        ).count()
        
        # Calculate usage score
        # Formula: (successful_logins_30d * 5) + (successful_logins_all_time * 0.5) - (failed_attempts_all_time * 2)
        usage_score = int(
            (successful_logins_30d * 5) + 
            (successful_logins_all_time * 0.5) - 
            (failed_attempts_all_time * 2)
        )
        usage_score = max(0, usage_score)  # Don't allow negative scores
        
        users_data.append({
            'id': profile.id,
            'user': {
                'id': profile.user.id,
                'username': profile.user.username,
                'email': profile.user.email,
                'first_name': profile.user.first_name,
                'last_name': profile.user.last_name,
                'is_active': profile.user.is_active,
                'date_joined': profile.user.date_joined.isoformat(),
                'last_login': profile.user.last_login.isoformat() if profile.user.last_login else None,
            },
            'role': profile.role,
            'accessible_countries': profile.accessible_countries or '',
            'accessible_portfolios': profile.accessible_portfolios or '',
            'accessible_sites': profile.accessible_sites or '',
            'app_access': profile.app_access or '',
            'ticketing_access': getattr(profile, 'ticketing_access', False),
            'created_by': profile.created_by_id,
            'created_at': profile.created_at.isoformat(),
            # Add login statistics
            'usage_score': usage_score,
            'successful_logins_all_time': successful_logins_all_time,
            'successful_logins_30d': successful_logins_30d,
            'failed_attempts_all_time': failed_attempts_all_time,
            'failed_attempts_recent': failed_attempts_recent,
        })
    
    # Sort users by usage score in descending order
    users_data.sort(key=lambda x: x['usage_score'], reverse=True)
    
    # Serialize assets
    assets_data = [
        {
            'asset_code': asset.asset_code,
            'asset_name': asset.asset_name,
            'country': asset.country,
            'portfolio': asset.portfolio,
            'asset_number': asset.asset_number,
        }
        for asset in assets
    ]
    
    # Get waffle flags for superusers
    flags_data = None
    flag_search_query = ''
    if request.user.is_superuser:
        from waffle.models import Flag
        flags_queryset = Flag.objects.all().order_by('name')
        flag_search_query = request.GET.get('flag_search', '').strip()
        if flag_search_query:
            flags_queryset = flags_queryset.filter(name__icontains=flag_search_query)
        
        flags_data = []
        for flag in flags_queryset:
            flag_data = {
                'id': flag.id,
                'name': flag.name,
                'everyone': flag.everyone,
                'percent': flag.percent,
                'testing': flag.testing,
                'superusers': flag.superusers,
                'staff': flag.staff,
                'authenticated': flag.authenticated,
                'rollout': flag.rollout,
                'note': flag.note or '',
                'created': flag.created.isoformat(),
                'modified': flag.modified.isoformat(),
            }
            # Include users if the flag has user assignments
            if hasattr(flag, 'users') and flag.users.exists():
                flag_data['users'] = [
                    {
                        'id': user.id,
                        'username': user.username,
                        'email': user.email,
                    }
                    for user in flag.users.all()
                ]
            else:
                flag_data['users'] = []
            flags_data.append(flag_data)
    
    # Build response
    stats = {
        'active_users_count': active_users_count,
        'security_alerts_count': security_alerts,
        'total_users': total_users,
        'suspicious_activities_count': len(suspicious_activities),
        'active_users': active_users,
        'inactive_users': inactive_users,
        'blocked_users_count': blocked_users_count,
        'blocked_ips_count': blocked_ips_count,
    }
    
    response_data = {
        'users': users_data,
        'assets': assets_data,
        'countries': countries,
        'portfolios': portfolios,
        'stats': stats,
        'activity_data': activity_data,
        'suspicious_activities': suspicious_activities,
        'is_superuser': request.user.is_superuser,  # Explicitly include superuser status
    }
    
    if flags_data is not None:
        response_data['flags'] = flags_data
        response_data['flag_search_query'] = flag_search_query
    
    return JsonResponse(response_data)


def api_create_user(request):
    """
    JSON-only API endpoint for creating users.
    POST /api/user-management/create/
    Always returns JSON - never HTML
    
    This endpoint is designed specifically for React/frontend AJAX requests.
    All responses are JSON, including errors.
    """
    # Force JSON content type in response
    response_kwargs = {'content_type': 'application/json'}
    
    # Check authentication first and return JSON if not authenticated
    if not request.user.is_authenticated:
        return JsonResponse({'error': 'Authentication required'}, status=401, **response_kwargs)
    
    # Check feature access - use the same logic as the decorator but return JSON
    try:
        from main.permissions import user_has_feature, user_has_app_access, _feature_app
        from main.models import UserProfile as main_userprofile
        
        # Check app access
        app_key = _feature_app('user_management')
        if app_key and not user_has_app_access(request.user, app_key):
            return JsonResponse({
                'error': f'You do not have access to the {app_key.upper()} application. Please contact an administrator.'
            }, status=403, **response_kwargs)
        
        # Check feature permission
        if not user_has_feature(request.user, 'user_management'):
            return JsonResponse({
                'error': 'You do not have permission to access user management feature.'
            }, status=403, **response_kwargs)
    except Exception as e:
        # If permission checks fail, log but don't block
        import logging
        logging.getLogger(__name__).warning(f"Feature check failed: {e}")
    
    # Check capability for creating users
    if not user_has_capability(request.user, 'user_management.manage'):
        return JsonResponse({
            'error': 'Permission denied. Only admin users can create users.'
        }, status=403, **response_kwargs)
    
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405, **response_kwargs)
    
    # Always return JSON - no HTML responses
    try:
        # Parse JSON data - handle both JSON and form-data
        try:
            content_type = request.headers.get('Content-Type', '') or request.content_type or ''
            if content_type.startswith('application/json'):
                # Standard JSON request
                data = json.loads(request.body) if request.body else {}
            elif content_type.startswith('multipart/form-data') or content_type.startswith('application/x-www-form-urlencoded'):
                # Form-data request - convert to JSON format for processing
                data = {
                    'username': request.POST.get('username', '').strip(),
                    'email': request.POST.get('email', '').strip(),
                    'password': request.POST.get('password', '').strip(),
                    'role': request.POST.get('role', '').strip(),
                    'access_control': request.POST.getlist('access_control'),
                    'countries': request.POST.getlist('countries'),
                    'portfolios': request.POST.getlist('portfolios'),
                    'sites': request.POST.getlist('sites'),
                }
            else:
                # Try to parse as JSON anyway
                data = json.loads(request.body) if request.body else {}
        except json.JSONDecodeError as e:
            return JsonResponse({'error': f'Invalid JSON data: {str(e)}'}, status=400, **response_kwargs)
        
        username = data.get('username', '').strip()
        email = data.get('email', '').strip()
        password = data.get('password', '').strip()
        role = data.get('role', '').strip()
        access_control = data.get('access_control', [])
        if isinstance(access_control, str):
            access_control = [access_control]
        country_names = data.get('countries', [])
        portfolio_names = data.get('portfolios', [])
        site_ids = data.get('sites', [])
        
        # Convert to lists if strings
        if isinstance(country_names, str):
            country_names = [country_names] if country_names else []
        if isinstance(portfolio_names, str):
            portfolio_names = [portfolio_names] if portfolio_names else []
        if isinstance(site_ids, str):
            site_ids = [site_ids] if site_ids else []
        
        # Multi-select dropdown access control
        selected_apps = []
        if 'web_access' in access_control or 'web' in access_control:
            selected_apps.append('web')
        if 'ticketing_access' in access_control or 'ticketing' in access_control:
            selected_apps.append('ticketing')
        if 'api_access' in access_control or 'api' in access_control:
            selected_apps.append('api')
        web_access = 'web' in selected_apps
        api_access = 'api' in selected_apps

        # Validation
        if not username or not email or not password or not role:
            return JsonResponse({
                'error': 'All fields are required (username, email, password, role).'
            }, status=400, **response_kwargs)
        
        if User.objects.filter(username=username).exists():
            return JsonResponse({
                'error': 'Username already exists.'
            }, status=400, **response_kwargs)
        
        if User.objects.filter(email=email).exists():
            return JsonResponse({
                'error': 'Email already exists.'
            }, status=400, **response_kwargs)

        # Create user and profile
        user = None
        try:
            with transaction.atomic():
                user = User.objects.create_user(username=username, email=email, password=password)
                
                profile = UserProfile.objects.create(
                    user=user,
                    role=role,
                    created_by=request.user
                )
                profile.set_app_access(selected_apps)
                
                # Apply hierarchical access control logic
                if site_ids and site_ids != ['']:
                    profile.accessible_sites = ','.join(site_ids)
                    profile.accessible_countries = ''
                    profile.accessible_portfolios = ''
                elif portfolio_names and portfolio_names != ['']:
                    profile.accessible_portfolios = ','.join(portfolio_names)
                    profile.accessible_sites = ''
                    profile.accessible_countries = ''
                elif country_names and country_names != ['']:
                    profile.accessible_countries = ','.join(country_names)
                    profile.accessible_sites = ''
                    profile.accessible_portfolios = ''
                else:
                    profile.accessible_sites = ''
                    profile.accessible_countries = ''
                    profile.accessible_portfolios = ''
                
                profile.save()
                
                # Create or update APIUser if API access is granted
                from api.models import APIUser
                if api_access:
                    if web_access and api_access:
                        access_level = 'both'
                    elif api_access:
                        access_level = 'api_only'
                    else:
                        access_level = 'web_only'
                    
                    APIUser.objects.update_or_create(
                        user=user,
                        defaults={
                            'name': f"{user.first_name} {user.last_name}".strip() or user.username,
                            'description': f"User created via user management",
                            'access_level': access_level,
                            'status': 'active'
                        }
                    )
                else:
                    APIUser.objects.filter(user=user).delete()
                
                # Build access summary (moved before logging)
                access_parts = [APP_ACCESS_LABELS.get(key, key.title()) for key in selected_apps]
                access_summary = ', '.join(access_parts) if access_parts else 'No access'
                
                # Log user creation (moved after access_summary is built)
                try:
                    if UserActivityLog:
                        UserActivityLog.objects.create(
                            user=request.user,
                            action='create',
                            resource=f'User Management - Create User',
                            **get_connection_ip_fields_for_log(request),
                            user_agent=request.META.get('HTTP_USER_AGENT', 'Unknown'),
                            method=request.method,
                            status_code=200,
                            response_time=0.0,
                            request_data={
                                'details': f'Created user: {username} ({email}) with role: {role}, access: {access_summary}',
                                'username': username,
                                'email': email,
                                'role': role,
                                'access_summary': access_summary
                            }
                        )
                        logger.info(f"Successfully logged user creation: {username} by {request.user.username}")
                except Exception as log_error:
                    logger.error(f"Failed to log user creation: {log_error}", exc_info=True)
                    print(f"ERROR: Failed to log user creation: {log_error}")
                
                return JsonResponse({
                    'success': True,
                    'message': f'User {username} created successfully with {access_summary} access!',
                    'user': {
                        'id': user.id,
                        'username': user.username,
                        'email': user.email,
                        'role': role,
                        'app_access': selected_apps,
                    }
                }, status=201, **response_kwargs)
                
        except Exception as e:
            # Cleanup if user was created but profile creation failed
            if user and user.pk:
                try:
                    user.delete()
                except:
                    pass
            raise e
            
    except Exception as exc:
        import traceback
        error_msg = str(exc)
        if settings.DEBUG:
            error_msg += f"\nTraceback: {traceback.format_exc()}"
        return JsonResponse({
            'error': f'Error creating user: {error_msg}'
        }, status=500, content_type='application/json')


@feature_required('user_management')
@login_required
def user_management_view(request):
    # IMPORTANT: Handle POST requests - React may send form-data, but we want JSON responses
    # The decorators above (login_required and feature_required) are now JSON-aware
    # and will return JSON errors for JSON requests instead of HTML redirects.
    if request.method == 'POST':
        # Check if this is a JSON/AJAX request - multiple ways to detect
        content_type = request.headers.get('Content-Type', '') or request.content_type or ''
        accept = request.headers.get('Accept', '')
        x_requested_with = request.headers.get('X-Requested-With', '')
        
        # Check if it's JSON request
        is_json_content = content_type.startswith('application/json')
        
        # Check if it's an AJAX/XHR request (React fetch/axios typically sets this, or we can check Accept header)
        is_ajax_request = (
            x_requested_with == 'XMLHttpRequest' or
            'application/json' in accept or
            accept.startswith('application/json') or
            # If it's form-data but Accept header suggests JSON preference, treat as AJAX
            (content_type.startswith('multipart/form-data') and 'application/json' in accept)
        )
        
        # For POST requests from React, we want JSON responses even if sent as form-data
        # Check if this looks like a React/frontend request (not a traditional form submission)
        is_likely_react_request = (
            is_json_content or 
            is_ajax_request or
            # If it's form-data POST to /user-management/, assume it's React and convert to JSON handling
            (content_type.startswith('multipart/form-data') and request.path == '/user-management/')
        )
        
        if is_likely_react_request:
            # Delegate to the API endpoint that always returns JSON
            # Convert form-data to JSON format if needed
            return api_create_user(request)
    
    # Check if React version is enabled via waffle flag
    from waffle import flag_is_active
    use_react = flag_is_active(request, 'react_user_management')
    
    if use_react:
        return render(request, 'main/user_management_react.html')
    
    try:
        user_profile = UserProfile.objects.get(user=request.user)
    except UserProfile.DoesNotExist:
        print("DEBUG: No user profile found")
    
    # Only admin can see all assets, others see only their assigned assets
    is_admin = user_has_capability(request.user, 'user_management.manage')
    
    if is_admin:
        assets = AssetList.objects.all()
        countries = sorted(set(country.strip() for country in AssetList.objects.values_list('country', flat=True) if country))
        portfolios = sorted(set(portfolio.strip() for portfolio in AssetList.objects.values_list('portfolio', flat=True) if portfolio))
    else:
        try:
            user_profile = UserProfile.objects.get(user=request.user)
            accessible_sites = user_profile.get_accessible_sites()
            assets = accessible_sites
            countries = sorted(set(country.strip() for country in accessible_sites.values_list('country', flat=True) if country))
            portfolios = sorted(set(portfolio.strip() for portfolio in accessible_sites.values_list('portfolio', flat=True) if portfolio))
        except UserProfile.DoesNotExist:
            assets = AssetList.objects.none()
            countries = []
            portfolios = []
    
    # Get filter parameters
    search_query = request.GET.get('search', '').strip()
    role_filter = request.GET.get('role', '').strip()
    status_filter = request.GET.get('status', '').strip()  # New status filter
    
    # Filter users based on search and role
    # IMPORTANT: Include ALL users (both active and inactive) when status_filter is empty
    
    # First, ensure UserProfile exists for all inactive users (so they show in the list)
    # This is necessary because some inactive users might not have UserProfile records
    if status_filter == '' or status_filter == 'inactive' or status_filter == 'blocked':
        # Get inactive users without UserProfile records
        inactive_users_without_profile = User.objects.filter(
            is_active=False
        ).exclude(
            userprofile__isnull=False
        )
        
        # Create UserProfile for inactive users without profiles
        for inactive_user in inactive_users_without_profile:
            try:
                UserProfile.objects.get_or_create(
                    user=inactive_user,
                    defaults={
                        'role': 'others',
                        'created_by': request.user if request.user.is_authenticated else None
                    }
                )
            except Exception:
                pass  # Skip if creation fails
    
    # Now query UserProfiles (after ensuring inactive users have profiles)
    users_queryset = UserProfile.objects.select_related('user').all()
    
    # Search filter
    if search_query:
        users_queryset = users_queryset.filter(
            Q(user__username__icontains=search_query) |
            Q(user__email__icontains=search_query) |
            Q(user__first_name__icontains=search_query) |
            Q(user__last_name__icontains=search_query)
        )
    
    # Role filter
    if role_filter:
        users_queryset = users_queryset.filter(role=role_filter)
    
    # Status filter (active, inactive/deleted, blocked)
    # If status_filter is empty (default), show ALL users (both active and inactive)
    if status_filter == 'active':
        users_queryset = users_queryset.filter(user__is_active=True)
    elif status_filter == 'inactive':
        users_queryset = users_queryset.filter(user__is_active=False)
    elif status_filter == 'blocked':
        # Get blocked users from BlockedUser model if available
        try:
            from ..models import BlockedUser
            blocked_user_ids = BlockedUser.objects.filter(status='active').values_list('user_id', flat=True)
            users_queryset = users_queryset.filter(user_id__in=blocked_user_ids)
        except:
            pass  # Model not available yet
    # If status_filter is empty, no filter is applied - shows ALL users (active and inactive)
    
    users = users_queryset.order_by('-created_at')
    
    # Get counts for badges
    total_users = UserProfile.objects.count()
    active_users = UserProfile.objects.filter(user__is_active=True).count()
    inactive_users = UserProfile.objects.filter(user__is_active=False).count()
    
    # Get blocked users count
    blocked_users_count = 0
    try:
        from ..models import BlockedUser
        blocked_users_count = BlockedUser.objects.filter(status='active').count()
    except:
        pass
    
    # Get blocked IPs count (all active blocked IPs, not limited)
    blocked_ips_count = 0
    try:
        from ..models import BlockedIP
        blocked_ips_count = BlockedIP.objects.filter(status='active').count()
    except:
        pass
    
    # Get activity statistics
    now = timezone.now()
    twenty_four_hours_ago = now - timedelta(hours=24)
    
    # Initialize default values
    active_users_count = 0
    activity_data = []
    security_alerts = 0
    suspicious_activities = []
    user_activity_summary = []
    
    # Only get activity data if models are available (migrated)
    if ActiveUserSession and UserActivityLog and SecurityAlert:
        # Active users (sessions active in last 30 minutes)
        thirty_minutes_ago = now - timedelta(minutes=30)
        active_users_count = ActiveUserSession.objects.filter(
            is_active=True,
            last_activity__gte=thirty_minutes_ago
        ).count()
        
        # Activity data for last 24 hours (hourly breakdown)
        # Get user's timezone from request header or use India timezone as default
        import pytz
        
        # Try to get timezone from request or default to India
        user_timezone_str = request.GET.get('timezone')
        if not user_timezone_str:
            # Default to India timezone since you mentioned Indian time
            user_timezone = pytz.timezone('Asia/Kolkata')
        else:
            try:
                user_timezone = pytz.timezone(user_timezone_str)
            except:
                user_timezone = pytz.timezone('Asia/Kolkata')
        
        # Calculate 24 hours ago in user's timezone
        now_local = timezone.now().astimezone(user_timezone)
        twenty_four_hours_ago_local = now_local - timedelta(hours=24)
        
        for i in range(24):
            # Calculate hour in user's local timezone
            hour_start_local = twenty_four_hours_ago_local + timedelta(hours=i)
            hour_end_local = hour_start_local + timedelta(hours=1)
            
            # Convert back to UTC for database query
            hour_start_utc = hour_start_local.astimezone(pytz.UTC)
            hour_end_utc = hour_end_local.astimezone(pytz.UTC)
            
            hour_activity = UserActivityLog.objects.filter(
                timestamp__gte=hour_start_utc,
                timestamp__lt=hour_end_utc
            ).count()
            
            activity_data.append({
                'hour': hour_start_local.strftime('%H:00'),
                'hour_full': hour_start_local.strftime('%Y-%m-%d %H:00'),
                'timestamp': hour_start_local.isoformat(),
                'count': hour_activity,
                'timezone': str(user_timezone)
            })
        
        # Security alerts summary
        security_alerts = SecurityAlert.objects.filter(
            created_at__gte=twenty_four_hours_ago,
            status='open'
        ).count()
        
        # Recent suspicious activities
        suspicious_activities = UserActivityLog.objects.filter(
            is_suspicious=True,
            timestamp__gte=twenty_four_hours_ago
        ).order_by('-timestamp')[:10]
        
        # User activity summary
        user_activity_summary = UserActivityLog.objects.filter(
            timestamp__gte=twenty_four_hours_ago
        ).values('action').annotate(count=Count('id')).order_by('-count')
    else:
        # Default empty activity data for 24 hours
        import pytz
        user_timezone = pytz.timezone('Asia/Kolkata')  # Default to India timezone
        
        now_local = timezone.now().astimezone(user_timezone)
        twenty_four_hours_ago_local = now_local - timedelta(hours=24)
        
        for i in range(24):
            hour_start_local = twenty_four_hours_ago_local + timedelta(hours=i)
            activity_data.append({
                'hour': hour_start_local.strftime('%H:00'),
                'hour_full': hour_start_local.strftime('%Y-%m-%d %H:00'),
                'timestamp': hour_start_local.isoformat(),
                'count': 0,
                'timezone': str(user_timezone)
            })
    
    error = None
    is_ajax = False  # Initialize the variable

    if request.method == 'POST':
        # Check if this is an AJAX/JSON request
        is_ajax = (
            request.headers.get('Content-Type', '').startswith('application/json') or
            request.headers.get('X-Requested-With') == 'XMLHttpRequest' or
            request.content_type == 'application/json' or
            'application/json' in request.headers.get('Accept', '')
        )
        
        # Parse data from JSON or form data
        if is_ajax:
            try:
                data = json.loads(request.body)
                username = data.get('username', '').strip()
                email = data.get('email', '').strip()
                password = data.get('password', '').strip()
                role = data.get('role', '').strip()
                access_control = data.get('access_control', [])
                if isinstance(access_control, str):
                    access_control = [access_control]
                country_names = data.get('countries', [])
                portfolio_names = data.get('portfolios', [])
                site_ids = data.get('sites', [])
            except json.JSONDecodeError:
                return JsonResponse({'error': 'Invalid JSON data'}, status=400)
        else:
            username = request.POST.get('username')
            email = request.POST.get('email')
            password = request.POST.get('password')
            role = request.POST.get('role')
            access_control = request.POST.getlist('access_control')
            country_names = request.POST.getlist('countries')
            portfolio_names = request.POST.getlist('portfolios')
            site_ids = request.POST.getlist('sites')
        
        # New: Multi-select dropdown access control
        selected_apps = []
        if 'web_access' in access_control or 'web' in access_control:
            selected_apps.append('web')
        if 'ticketing_access' in access_control or 'ticketing' in access_control:
            selected_apps.append('ticketing')
        if 'api_access' in access_control or 'api' in access_control:
            selected_apps.append('api')
        web_access = 'web' in selected_apps
        api_access = 'api' in selected_apps

        if not username or not email or not password or not role:
            error = "All fields are required."
            if is_ajax:
                return JsonResponse({'error': error}, status=400)
        elif User.objects.filter(username=username).exists():
            error = "Username already exists."
            if is_ajax:
                return JsonResponse({'error': error}, status=400)
        elif User.objects.filter(email=email).exists():
            error = "Email already exists."
            if is_ajax:
                return JsonResponse({'error': error}, status=400)
        else:
            try:
                # Create user and profile in a transaction
                with transaction.atomic():
                    user = User.objects.create_user(username=username, email=email, password=password)
                    
                    profile = UserProfile.objects.create(
                        user=user,
                        role=role,
                        created_by=request.user
                    )
                    profile.set_app_access(selected_apps)
                    
                    # Apply hierarchical access control logic using TextField approach
                    if site_ids and site_ids != ['']:
                        # If specific sites are selected, assign only those sites
                        profile.accessible_sites = ','.join(site_ids)
                        profile.accessible_countries = ''  # Clear country assignments
                        profile.accessible_portfolios = ''  # Clear portfolio assignments
                    elif portfolio_names and portfolio_names != ['']:
                        # If portfolios are selected, assign those portfolios
                        profile.accessible_portfolios = ','.join(portfolio_names)
                        profile.accessible_sites = ''  # Clear site assignments
                        profile.accessible_countries = ''  # Clear country assignments
                    elif country_names and country_names != ['']:
                        # If countries are selected, assign those countries
                        profile.accessible_countries = ','.join(country_names)
                        profile.accessible_sites = ''  # Clear site assignments
                        profile.accessible_portfolios = ''  # Clear portfolio assignments
                    else:
                        # No access assigned
                        profile.accessible_sites = ''
                        profile.accessible_countries = ''
                        profile.accessible_portfolios = ''
                    
                    profile.save()
                    
                    # Create or update APIUser ONLY if user has API access
                    from api.models import APIUser
                    if api_access:
                        # Determine access_level based on web and api access
                        if web_access and api_access:
                            access_level = 'both'
                        elif api_access:
                            access_level = 'api_only'
                        else:
                            access_level = 'web_only'
                        
                        APIUser.objects.update_or_create(
                            user=user,
                            defaults={
                                'name': f"{user.first_name} {user.last_name}".strip() or user.username,
                                'description': f"User created via user management",
                                'access_level': access_level,
                                'status': 'active'
                            }
                        )
                    else:
                        # Remove APIUser record if it exists (cleanup)
                        APIUser.objects.filter(user=user).delete()
                    
                    # Build access summary message
                    access_parts = [APP_ACCESS_LABELS.get(key, key.title()) for key in selected_apps]
                    access_summary = ', '.join(access_parts) if access_parts else 'No access'
                    
                    # Log user creation
                    try:
                        if UserActivityLog:
                            UserActivityLog.objects.create(
                                user=request.user,
                                action='create',
                                resource=f'User Management - Create User',
                                **get_connection_ip_fields_for_log(request),
                                user_agent=request.META.get('HTTP_USER_AGENT', 'Unknown'),
                                method=request.method,
                                status_code=200,
                                response_time=0.0,
                                request_data={
                                    'details': f'Created user: {username} ({email}) with role: {role}, access: {access_summary}',
                                    'username': username,
                                    'email': email,
                                    'role': role,
                                    'access_summary': access_summary
                                }
                            )
                            logger.info(f"Successfully logged user creation: {username} by {request.user.username}")
                    except Exception as log_error:
                        logger.error(f"Failed to log user creation: {log_error}", exc_info=True)
                        print(f"ERROR: Failed to log user creation: {log_error}")
                    
                    if is_ajax:
                        # Return JSON response for AJAX requests
                        return JsonResponse({
                            'success': True,
                            'message': f'User {username} created successfully with {access_summary} access!',
                            'user': {
                                'id': user.id,
                                'username': user.username,
                                'email': user.email,
                                'role': role,
                                'app_access': selected_apps,
                            }
                        })
                    else:
                        # Traditional form submission - redirect
                        messages.success(request, f'User {username} created successfully with {access_summary} access!')
                        return redirect('main:user_management')
            except Exception as e:
                error = f"Error creating user: {str(e)}"
                if user and user.pk:
                    user.delete()  # Cleanup if profile creation failed
                if is_ajax:
                    import traceback
                    error_details = error
                    if settings.DEBUG:
                        error_details += f"\nTraceback: {traceback.format_exc()}"
                    return JsonResponse({'error': error_details}, status=500)

    # Import APIUser for access level choices
    from api.models import APIUser
    
    # Get waffle flags for superusers
    flags = None
    flag_search_query = ''
    if request.user.is_superuser:
        from waffle.models import Flag
        flags = Flag.objects.all().order_by('name')
        flag_search_query = request.GET.get('flag_search', '').strip()
        if flag_search_query:
            flags = flags.filter(name__icontains=flag_search_query)
    
    # If this was an AJAX POST request that failed validation, return JSON error instead of rendering HTML
    if request.method == 'POST' and is_ajax and error:
        return JsonResponse({'error': error}, status=400)
    
    return render(request, 'main/user_management.html', {
        'users': users,
        'assets': assets,
        'countries': countries,
        'portfolios': portfolios,
        'error': error,
        'search_query': search_query,
        'role_filter': role_filter,
        'status_filter': status_filter,
        'active_users_count': active_users_count,
        'activity_data': activity_data,
        'security_alerts_count': security_alerts,
        'suspicious_activities': suspicious_activities,
        'user_activity_summary': user_activity_summary,
        'role_choices': UserProfile.ROLE_CHOICES,
        'access_level_choices': APIUser.ACCESS_LEVEL_CHOICES,
        'total_users': total_users,
        'flags': flags,
        'flag_search_query': flag_search_query,
        'active_users': active_users,
        'inactive_users': inactive_users,
        'blocked_users_count': blocked_users_count,
        'blocked_ips_count': blocked_ips_count,
    })



@login_required
@role_required(allowed_roles=USER_MANAGEMENT_MANAGER_ROLES)  # ADMIN ONLY ACCESS
def user_activity_api(request):
    """API endpoint for user activity chart data - ADMIN ONLY"""
    # Check if models are available
    if not UserActivityLog:
        return JsonResponse({
            'success': False,
            'error': 'Activity logging not available. Please run migrations.'
        }, status=503)
        
    try:
        now = timezone.now()
        twenty_four_hours_ago = now - timedelta(hours=24)
        
        # Get activity data for last 24 hours (hourly breakdown)
        # Use India timezone for display
        import pytz
        user_timezone = pytz.timezone('Asia/Kolkata')  # India timezone
        
        # Calculate 24 hours ago in India timezone
        now_local = timezone.now().astimezone(user_timezone)
        twenty_four_hours_ago_local = now_local - timedelta(hours=24)
        
        activity_data = []
        for i in range(24):
            # Calculate hour in India timezone
            hour_start_local = twenty_four_hours_ago_local + timedelta(hours=i)
            hour_end_local = hour_start_local + timedelta(hours=1)
            
            # Convert back to UTC for database query
            hour_start_utc = hour_start_local.astimezone(pytz.UTC)
            hour_end_utc = hour_end_local.astimezone(pytz.UTC)
            
            hour_activity = UserActivityLog.objects.filter(
                timestamp__gte=hour_start_utc,
                timestamp__lt=hour_end_utc
            ).count()
            
            activity_data.append({
                'hour': hour_start_local.strftime('%H:00'),
                'hour_full': hour_start_local.strftime('%Y-%m-%d %H:00'),
                'timestamp': hour_start_local.isoformat(),
                'count': hour_activity,
                'timezone': 'Asia/Kolkata'
            })
        
        return JsonResponse({
            'success': True,
            'data': activity_data
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@login_required
@role_required(allowed_roles=USER_MANAGEMENT_MANAGER_ROLES)  # ADMIN ONLY ACCESS
def download_user_activity(request):
    """Download user activity data with filters - ADMIN ONLY"""
    # Check if models are available
    if not UserActivityLog:
        # Return a simple HTML page with error message instead of JSON
        html_content = '''
        <!DOCTYPE html>
        <html>
        <head><title>Download Error</title></head>
        <body>
            <h3>Activity logging not available</h3>
            <p>Please run migrations first.</p>
            <script>
                setTimeout(() => window.close(), 3000);
            </script>
        </body>
        </html>
        '''
        return HttpResponse(html_content, content_type='text/html')
    
    try:
        # Get filter parameters
        start_date = request.GET.get('start_date')
        end_date = request.GET.get('end_date')
        user_filter = request.GET.get('user')
        action_filter = request.GET.get('action')
        ip_filter = request.GET.get('ip')
        include_suspicious = request.GET.get('include_suspicious', 'false') == 'true'
        
        # Build queryset - start with all activity logs
        queryset = UserActivityLog.objects.select_related('user').all()
        
        # Apply date filters - default to current date if no dates specified
        import pytz
        user_timezone = pytz.timezone('Asia/Kolkata')  # India timezone
        
        if start_date:
            try:
                start_dt = timezone.datetime.strptime(start_date, '%Y-%m-%d')
                start_dt = timezone.make_aware(start_dt, user_timezone)
                queryset = queryset.filter(timestamp__gte=start_dt)
            except ValueError:
                pass
        else:
            # Default to current date if no start date specified
            today = timezone.now().astimezone(user_timezone).replace(hour=0, minute=0, second=0, microsecond=0)
            queryset = queryset.filter(timestamp__gte=today)
        
        if end_date:
            try:
                end_dt = timezone.datetime.strptime(end_date, '%Y-%m-%d')
                end_dt = timezone.make_aware(end_dt, user_timezone) + timedelta(days=1)  # Include full day
                queryset = queryset.filter(timestamp__lt=end_dt)
            except ValueError:
                pass
        else:
            # Default to end of current date if no end date specified
            if not start_date:  # Only apply if no custom start date
                tomorrow = timezone.now().astimezone(user_timezone).replace(hour=23, minute=59, second=59, microsecond=999999)
                queryset = queryset.filter(timestamp__lte=tomorrow)
        
        if user_filter:
            queryset = queryset.filter(user__username__icontains=user_filter)
        
        if action_filter:
            queryset = queryset.filter(action=action_filter)
        
        if ip_filter:
            queryset = queryset.filter(
                Q(ip_address__icontains=ip_filter)
                | Q(client_ip__icontains=ip_filter)
                | Q(peer_ip__icontains=ip_filter)
                | Q(forwarded_for__icontains=ip_filter)
            )
        
        if include_suspicious:
            queryset = queryset.filter(is_suspicious=True)
        
        # Order by timestamp
        queryset = queryset.order_by('-timestamp')
        
        # Use the same approach as site onboarding (WORKING METHOD)
        filename = f'user_activity_{timezone.now().strftime("%Y%m%d_%H%M%S")}.csv'
        response = HttpResponse(content_type='text/csv; charset=utf-8')
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        
        # Add UTF-8 BOM for better Excel compatibility
        response.write('\ufeff')
        
        writer = csv.writer(response)
        
        # Write header - ALL available columns from UserActivityLog model
        headers = [
            'ID',
            'Timestamp (IST)',
            'Timestamp (UTC)',
            'Username',
            'User ID',
            'User Email',
            'Session Key',
            'IP Address',
            'Peer IP (REMOTE_ADDR)',
            'X-Forwarded-For (raw)',
            'Client IP (resolved)',
            'User Agent',
            'Action',
            'Action Display',
            'Resource (URL Path)',
            'HTTP Method',
            'Status Code',
            'Response Time (seconds)',
            'Response Size (bytes)',
            'Country',
            'City', 
            'Region',
            'Is Suspicious',
            'Risk Level',
            'Risk Level Display',
            'Security Flags',
            'Request Data (JSON)',
            'Request GET Parameters',
            'Request POST Parameters',
            'Content Type',
            'Content Length'
        ]
        writer.writerow(headers)
        
        # Convert to India timezone for timestamp display
        import pytz
        ist_timezone = pytz.timezone('Asia/Kolkata')
        
        # Write data - ALL available columns
        for log in queryset:
            # Convert timestamp to IST for display
            timestamp_ist = log.timestamp.astimezone(ist_timezone)
            
            # Extract request data details
            request_data = log.request_data or {}
            get_params = request_data.get('get_params', {})
            post_params = request_data.get('post_params', {})
            content_type = request_data.get('content_type', '')
            content_length = request_data.get('content_length', 0)
            
            row = [
                log.id,
                timestamp_ist.strftime('%Y-%m-%d %H:%M:%S'),
                log.timestamp.strftime('%Y-%m-%d %H:%M:%S'),
                log.user.username if log.user else 'Anonymous',
                log.user.id if log.user else '',
                log.user.email if log.user else '',
                log.session_key,
                log.ip_address,
                log.peer_ip,
                log.forwarded_for,
                log.client_ip,
                log.user_agent,
                log.action,
                log.get_action_display(),
                log.resource,
                log.method,
                log.status_code,
                round(log.response_time, 3),
                log.response_size,
                log.country,
                log.city,
                log.region,
                'Yes' if log.is_suspicious else 'No',
                log.risk_level,
                log.get_risk_level_display(),
                ', '.join(log.security_flags) if log.security_flags else '',
                json.dumps(log.request_data) if log.request_data else '',
                json.dumps(get_params) if get_params else '',
                json.dumps(post_params) if post_params else '',
                content_type,
                content_length
            ]
            writer.writerow(row)
        
        # Add headers to ensure download starts automatically
        response['Cache-Control'] = 'no-cache, no-store, must-revalidate'
        response['Pragma'] = 'no-cache'
        response['Expires'] = '0'
        
        return response
        
    except Exception as e:
        # Return HTML error page instead of JSON
        html_content = f'''
        <!DOCTYPE html>
        <html>
        <head><title>Download Error</title></head>
        <body>
            <h3>Download Error</h3>
            <p>Error: {str(e)}</p>
            <script>
                setTimeout(() => window.close(), 3000);
            </script>
        </body>
        </html>
        '''
        return HttpResponse(html_content, content_type='text/html')


@login_required
@role_required(allowed_roles=USER_MANAGEMENT_MANAGER_ROLES)  # ADMIN ONLY ACCESS
def download_user_activity_auto(request):
    """Auto-download page that starts download immediately"""
    # Check if models are available
    if not UserActivityLog:
        return HttpResponse('''
        <!DOCTYPE html>
        <html>
        <head><title>Download Error</title></head>
        <body>
            <h3>Activity logging not available</h3>
            <p>Please run migrations first.</p>
            <script>setTimeout(() => window.close(), 3000);</script>
        </body>
        </html>
        ''', content_type='text/html')
    
    try:
        # Get filter parameters
        start_date = request.GET.get('start_date')
        end_date = request.GET.get('end_date')
        user_filter = request.GET.get('user')
        action_filter = request.GET.get('action')
        ip_filter = request.GET.get('ip')
        include_suspicious = request.GET.get('include_suspicious', 'false') == 'true'
        
        # Build download URL for the actual CSV download
        params = []
        if start_date: params.append(f'start_date={start_date}')
        if end_date: params.append(f'end_date={end_date}')
        if user_filter: params.append(f'user={user_filter}')
        if action_filter: params.append(f'action={action_filter}')
        if ip_filter: params.append(f'ip={ip_filter}')
        if include_suspicious: params.append('include_suspicious=true')
        
        query_string = '&'.join(params)
        download_url = f"/download-user-activity/?{query_string}"
        
        # Return HTML page that automatically triggers download
        html_content = f'''
        <!DOCTYPE html>
        <html>
        <head>
            <title>Downloading User Activity Data...</title>
            <meta http-equiv="refresh" content="0; url={download_url}">
        </head>
        <body>
            <div style="text-align: center; padding: 50px; font-family: Arial, sans-serif;">
                <h3>🔄 Preparing Download...</h3>
                <p>Your download should start automatically.</p>
                <p><a href="{download_url}">Click here if download doesn't start</a></p>
                <script>
                    // Multiple methods to trigger download
                    setTimeout(() => {{
                        window.location.href = '{download_url}';
                    }}, 500);
                    
                    // Close window after download starts
                    setTimeout(() => {{
                        window.close();
                    }}, 3000);
                </script>
            </div>
        </body>
        </html>
        '''
        
        return HttpResponse(html_content, content_type='text/html')
        
    except Exception as e:
        return HttpResponse(f'''
        <!DOCTYPE html>
        <html>
        <head><title>Download Error</title></head>
        <body>
            <h3>Download Error</h3>
            <p>Error: {str(e)}</p>
            <script>setTimeout(() => window.close(), 3000);</script>
        </body>
        </html>
        ''', content_type='text/html')

@role_required(allowed_roles=USER_MANAGEMENT_MANAGER_ROLES)
@login_required
def send_password_reset_email(request, user):
    token = default_token_generator.make_token(user)
    uid = urlsafe_base64_encode(force_bytes(user.pk))
    reset_url = request.build_absolute_uri(
        reverse('accounts:password_reset_confirm', kwargs={'uidb64': uid, 'token': token})
    )
    
    # Get logo URL
    logo_url = request.build_absolute_uri('/static/PEAK_LOGO.jpg')
    
    # Prepare email context
    context = {
        'user': user,
        'uid': uid,
        'token': token,
        'protocol': request.scheme,
        'domain': request.get_host(),
        'logo_url': logo_url,
        'reset_url': reset_url,
    }
    
    subject = "Set Your Password - Peak Energy"
    
    # Render HTML email template
    html_message = render_to_string('accounts/password_reset_email.html', context)
    
    # Plain text version
    text_message = f"""Hello {user.username},

Your account has been created for Peak Energy. Please set your password to complete your account setup and access the system.

Your username: {user.username}

Please set your password using the following link:
{reset_url}

This link will expire after use or in 24 hours for security reasons.

After setting your password, you can log in at: www.peakpulse-dev.xyz

If you did not expect this email, please contact your system administrator.

Welcome to Peak Energy!

Best regards,
Peak Energy Team"""
    
    logger = logging.getLogger(__name__)
    
    try:
        # Create email message with HTML and plain text alternatives
        msg = EmailMultiAlternatives(
            subject=subject,
            body=text_message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[user.email]
        )
        msg.attach_alternative(html_message, "text/html")
        
        # Send email
        msg.send()
        logger.info(f"Password reset email sent successfully to {user.email}")
        
    except Exception as e:
        import traceback
        error_msg = f"Failed to send password reset email to {user.email}: {str(e)}"
        logger.error(error_msg)
        logger.error(f"Error type: {type(e).__name__}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        raise  # Re-raise so the calling function can handle it
    
@login_required
@role_required(allowed_roles=USER_MANAGEMENT_MANAGER_ROLES)
def send_password_reset(request, user_id):
    if request.method == 'POST':
        user = get_object_or_404(User, pk=user_id)
        logger = logging.getLogger(__name__)
        logger.info(f"Password reset requested for user ID {user_id} ({user.username}, {user.email})")
        
        try:
            send_password_reset_email(request, user)
            messages.success(request, f"Password setup link sent to {user.email}.")
            logger.info(f"Password reset email successfully sent to {user.email}")
        except Exception as e:
            import traceback
            logger.error(f"Error sending password reset email: {str(e)}")
            logger.error(f"Traceback: {traceback.format_exc()}")
            messages.error(request, f"Failed to send password setup email: {str(e)}. Please check email configuration.")
    
    return redirect('main:user_management')


@feature_required('user_management')
@login_required
def edit_user_access(request, user_id):
    """
    Edit user access permissions (countries, portfolios, and sites)
    Only admin users can access this view
    """
    if not user_has_capability(request.user, 'user_management.manage'):
        messages.error(request, 'Only admin users can edit user access.')
        return redirect('main:user_management')
    
    try:
        user_profile = UserProfile.objects.select_related('user').get(user_id=user_id)
    except UserProfile.DoesNotExist:
        messages.error(request, 'User not found.')
        return redirect('main:user_management')
    
    # Get all available assets, countries, and portfolios for admin
    assets = AssetList.objects.all()
    countries = sorted(set(country.strip() for country in AssetList.objects.values_list('country', flat=True) if country))
    portfolios = sorted(set(portfolio.strip() for portfolio in AssetList.objects.values_list('portfolio', flat=True) if portfolio))
    
    if request.method == 'POST':
        role = request.POST.get('role')  # New: User role
        
        # New: Multi-select dropdown access control
        access_control = request.POST.getlist('access_control')
        selected_apps = []
        if 'web_access' in access_control:
            selected_apps.append('web')
        if 'ticketing_access' in access_control:
            selected_apps.append('ticketing')
        if 'api_access' in access_control:
            selected_apps.append('api')
        web_access = 'web' in selected_apps
        api_access = 'api' in selected_apps
        
        country_names = request.POST.getlist('countries')
        portfolio_names = request.POST.getlist('portfolios')
        site_ids = request.POST.getlist('sites')
        
        try:
            with transaction.atomic():
                # Update user role if provided
                if role:
                    user_profile.role = role
                
                # Update application access selections
                user_profile.set_app_access(selected_apps)
                
                # Apply hierarchical access control logic using TextField approach
                if site_ids and site_ids != ['']:
                    # If specific sites are selected, assign only those sites
                    user_profile.accessible_sites = ','.join(site_ids)
                    user_profile.accessible_countries = ''  # Clear country assignments
                    user_profile.accessible_portfolios = ''  # Clear portfolio assignments
                elif portfolio_names and portfolio_names != ['']:
                    # If portfolios are selected, assign those portfolios
                    user_profile.accessible_portfolios = ','.join(portfolio_names)
                    user_profile.accessible_sites = ''  # Clear site assignments
                    user_profile.accessible_countries = ''  # Clear country assignments
                elif country_names and country_names != ['']:
                    # If countries are selected, assign those countries
                    user_profile.accessible_countries = ','.join(country_names)
                    user_profile.accessible_sites = ''  # Clear site assignments
                    user_profile.accessible_portfolios = ''  # Clear portfolio assignments
                else:
                    # No access assigned - clear everything
                    user_profile.accessible_sites = ''
                    user_profile.accessible_countries = ''
                    user_profile.accessible_portfolios = ''
                
                user_profile.save()
                if not user_profile.user.is_superuser and user_profile.user.is_staff:
                    user_profile.user.is_staff = False
                    user_profile.user.save(update_fields=['is_staff'])
                
                # Create or update APIUser ONLY if user has API access
                from api.models import APIUser
                if api_access:
                    # Determine access_level based on web and api access
                    if web_access and api_access:
                        access_level = 'both'
                    elif api_access:
                        access_level = 'api_only'
                    else:
                        access_level = 'web_only'
                    
                    APIUser.objects.update_or_create(
                        user=user_profile.user,
                        defaults={
                            'name': f"{user_profile.user.first_name} {user_profile.user.last_name}".strip() or user_profile.user.username,
                            'description': f"User managed via user management",
                            'access_level': access_level,
                            'status': 'active'
                        }
                    )
                else:
                    # Remove APIUser record and all related API keys if API access removed
                    api_user = APIUser.objects.filter(user=user_profile.user).first()
                    if api_user:
                        # Delete all API keys for this user
                        from api.models import APIKey
                        APIKey.objects.filter(api_user=api_user).delete()
                        # Delete the APIUser record
                        api_user.delete()
                
                # Build access summary message
                access_parts = [APP_ACCESS_LABELS.get(key, key.title()) for key in selected_apps]
                access_summary = ', '.join(access_parts) if access_parts else 'No access'
                
                # Log user update
                try:
                    if UserActivityLog:
                        changes = []
                        if role and role != user_profile.role:
                            changes.append(f'role: {user_profile.role} -> {role}')
                        if access_summary:
                            changes.append(f'access: {access_summary}')
                        if country_names:
                            changes.append(f'countries: {", ".join(country_names)}')
                        if portfolio_names:
                            changes.append(f'portfolios: {", ".join(portfolio_names)}')
                        if site_ids:
                            changes.append(f'sites: {len(site_ids)} sites')
                        
                        change_details = '; '.join(changes) if changes else 'Access updated'
                        
                        UserActivityLog.objects.create(
                            user=request.user,
                            action='update',
                            resource=f'User Management - Update User Access',
                            **get_connection_ip_fields_for_log(request),
                            user_agent=request.META.get('HTTP_USER_AGENT', 'Unknown'),
                            method=request.method,
                            status_code=200,
                            response_time=0.0,
                            request_data={
                                'details': f'Updated user: {user_profile.user.username} - {change_details}',
                                'target_user': user_profile.user.username,
                                'target_user_id': user_profile.user.id,
                                'changes': change_details
                            }
                        )
                        logger.info(f"Successfully logged user update: {user_profile.user.username} by {request.user.username}")
                except Exception as log_error:
                    logger.error(f"Failed to log user update: {log_error}", exc_info=True)
                    print(f"ERROR: Failed to log user update: {log_error}")
                
                messages.success(request, f'Access updated successfully for {user_profile.user.username}! Access: {access_summary}')
                return redirect('main:user_management')
        except Exception as e:
            messages.error(request, f'Error updating user access: {str(e)}')
    
    # Get current access settings
    has_web_access = user_profile.has_app_access('web')
    has_ticketing_access = user_profile.has_app_access('ticketing')
    has_api_access = user_profile.has_app_access('api')
    return render(request, 'main/edit_user_access.html', {
        'user_profile': user_profile,
        'assets': assets,
        'countries': countries,
        'portfolios': portfolios,
        'has_web_access': has_web_access,
        'has_api_access': has_api_access,
        'has_ticketing_access': has_ticketing_access,
        'role_choices': UserProfile.ROLE_CHOICES,
    })

@login_required
@superuser_required  # Superuser only - more restrictive than role_required
def delete_user_permanent(request):
    """Permanently delete a user - Superuser only"""
    # Additional superuser check for extra security (defense in depth)
    if not request.user.is_superuser:
        return JsonResponse({'error': 'Permission denied. Only superusers can delete users.'}, status=403)
    
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            username = data.get('username', '').strip()
            
            if not username:
                return JsonResponse({'error': 'Username is required'}, status=400)
            
            # Prevent self-deletion
            if username == request.user.username:
                return JsonResponse({'error': 'You cannot delete your own account'}, status=400)
            
            # Check if user exists
            try:
                user = User.objects.get(username=username)
            except User.DoesNotExist:
                return JsonResponse({'error': 'User not found'}, status=404)
            
            # Store user info before deletion for logging
            deleted_username = user.username
            deleted_email = user.email
            deleted_user_id = user.id
            
            # Log user deletion BEFORE deleting (so we can reference the user)
            try:
                if UserActivityLog:
                    UserActivityLog.objects.create(
                        user=request.user,
                        action='delete',
                        resource=f'User Management - Delete User',
                        **get_connection_ip_fields_for_log(request),
                        user_agent=request.META.get('HTTP_USER_AGENT', 'Unknown'),
                        method=request.method,
                        status_code=200,
                        response_time=0.0,
                        request_data={
                            'details': f'Deleted user: {deleted_username} ({deleted_email}) - ID: {deleted_user_id}',
                            'deleted_username': deleted_username,
                            'deleted_email': deleted_email,
                            'deleted_user_id': deleted_user_id
                        }
                    )
                    logger.info(f"Successfully logged user deletion: {deleted_username} by {request.user.username}")
            except Exception as log_error:
                logger.error(f"Failed to log user deletion: {log_error}", exc_info=True)
                print(f"ERROR: Failed to log user deletion: {log_error}")
            
            # Delete user (this will cascade to related objects)
            user.delete()
            
            return JsonResponse({
                'success': True,
                'message': f'User {deleted_username} deleted permanently'
            })
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)
    
    return JsonResponse({'error': 'Method not allowed'}, status=405)


@login_required
@role_required(allowed_roles=USER_MANAGEMENT_MANAGER_ROLES)
def deactivate_user(request):
    """Deactivate a user - Admin only"""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            username = data.get('username', '').strip()
            
            if not username:
                return JsonResponse({'error': 'Username is required'}, status=400)
            
            # Prevent self-deactivation
            if username == request.user.username:
                return JsonResponse({'error': 'You cannot deactivate your own account'}, status=400)
            
            # Check if user exists
            try:
                user = User.objects.get(username=username)
            except User.DoesNotExist:
                return JsonResponse({'error': 'User not found'}, status=404)
            
            # Check if user is already inactive
            if not user.is_active:
                return JsonResponse({'error': 'User is already deactivated'}, status=400)
            
            # Deactivate user
            user.is_active = False
            user.save()
            
            # Log the action (with error handling)
            try:
                if UserActivityLog:
                    UserActivityLog.objects.create(
                        user=request.user,
                        action='update',
                        resource=f'User Management - Deactivate {username}',
                        **get_connection_ip_fields_for_log(request),
                        user_agent=request.META.get('HTTP_USER_AGENT', 'Unknown'),
                        method=request.method,
                        status_code=200,
                        response_time=0.0,
                        request_data={
                            'details': f'Deactivated user: {username}',
                            'target_username': username,
                            'target_user_id': user.id
                        }
                    )
                    logger.info(f"Successfully logged user deactivation: {username} by {request.user.username}")
            except Exception as log_error:
                logger.error(f"Failed to log user deactivation: {log_error}", exc_info=True)
                print(f"ERROR: Failed to log user deactivation: {log_error}")
            
            return JsonResponse({
                'success': True,
                'message': f'User {username} has been deactivated'
            })
        except json.JSONDecodeError as json_error:
            return JsonResponse({'error': f'Invalid JSON: {str(json_error)}'}, status=400)
        except Exception as e:
            import traceback
            error_details = f"Error: {str(e)}\nTraceback: {traceback.format_exc()}"
            print(f"Deactivate user error: {error_details}")
            return JsonResponse({'error': f'Internal server error: {str(e)}'}, status=500)
    
    return JsonResponse({'error': 'Method not allowed'}, status=405)


@login_required
@superuser_required
def reactivate_user(request):
    """Reactivate a user - Superuser only"""
    if request.method == 'POST':
        try:
            # Additional superuser check for extra security
            if not request.user.is_superuser:
                return JsonResponse({'error': 'Only superusers can reactivate users'}, status=403)
            
            data = json.loads(request.body)
            username = data.get('username', '').strip()
            
            if not username:
                return JsonResponse({'error': 'Username is required'}, status=400)
            
            # Check if user exists
            try:
                user = User.objects.get(username=username)
            except User.DoesNotExist:
                return JsonResponse({'error': 'User not found'}, status=404)
            
            # Check if user is already active
            user_was_already_active = user.is_active
            
            # Reactivate user (if not already active)
            if not user.is_active:
                user.is_active = True
                user.save()
            
            # Clear failed login attempts from database
            from accounts.models import LoginAttempt
            LoginAttempt.clear_attempts(username)
            
            # Also clear/update BlockedUser records if they exist
            # This ensures BlockedUser records are cleaned up even if user is already active
            try:
                from ..models import BlockedUser
                # Update ALL blocked user records (both active and inactive) to ensure they're cleared
                blocked_users = BlockedUser.objects.filter(user=user)
                if blocked_users.exists():
                    # Set status to 'inactive' to mark as cleared (or could delete if preferred)
                    blocked_users.update(status='inactive')
            except Exception as unblock_error:
                # Don't fail the main operation if unblocking fails
                print(f"Warning: Failed to unblock user from BlockedUser model: {unblock_error}")
            
            # Return success message based on whether user was already active
            if user_was_already_active:
                return JsonResponse({
                    'success': True,
                    'message': f'User {username} is already active. BlockedUser records have been cleared.'
                })
            
            # Log the action (with error handling)
            try:
                if UserActivityLog:
                    UserActivityLog.objects.create(
                        user=request.user,
                        action='update',
                        resource=f'User Management - Reactivate {username}',
                        **get_connection_ip_fields_for_log(request),
                        user_agent=request.META.get('HTTP_USER_AGENT', 'Unknown'),
                        method=request.method,
                        status_code=200,
                        response_time=0.0,
                        request_data={
                            'details': f'Reactivated user: {username}',
                            'target_username': username,
                            'target_user_id': user.id
                        }
                    )
                    logger.info(f"Successfully logged user reactivation: {username} by {request.user.username}")
            except Exception as log_error:
                logger.error(f"Failed to log user reactivation: {log_error}", exc_info=True)
                print(f"ERROR: Failed to log user reactivation: {log_error}")
            
            return JsonResponse({
                'success': True,
                'message': f'User {username} has been reactivated'
            })
        except json.JSONDecodeError as json_error:
            return JsonResponse({'error': f'Invalid JSON: {str(json_error)}'}, status=400)
        except Exception as e:
            import traceback
            error_details = f"Error: {str(e)}\nTraceback: {traceback.format_exc()}"
            print(f"Reactivate user error: {error_details}")
            return JsonResponse({'error': f'Internal server error: {str(e)}'}, status=500)
    
    return JsonResponse({'error': 'Method not allowed'}, status=405)


@login_required
@role_required(allowed_roles=USER_MANAGEMENT_MANAGER_ROLES)
def test_security_endpoint(request):
    """Test endpoint to verify URLs are working"""
    return JsonResponse({'message': 'Security endpoints are working!', 'status': 'ok'})


# ============================================================================
# WAFFLE FLAG MANAGEMENT (Superuser Only)
# ============================================================================

@login_required
@superuser_required
def create_flag(request):
    """Create a new waffle flag"""
    from waffle.models import Flag
    from django.contrib import messages
    
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)
    
    try:
        # Parse JSON body
        try:
            data = json.loads(request.body)
        except json.JSONDecodeError as e:
            return JsonResponse({'error': f'Invalid JSON: {str(e)}'}, status=400)
        
        # Extract fields from request data
        name = data.get('name', '').strip()
        everyone = data.get('everyone', None)
        percent = data.get('percent', None)
        superusers = data.get('superusers', False)
        staff = data.get('staff', False)
        authenticated = data.get('authenticated', False)
        testing = data.get('testing', False)
        rollout = data.get('rollout', False)
        note = data.get('note', '').strip()
        
        # Validate required fields
        if not name:
            return JsonResponse({'error': 'Flag name is required'}, status=400)
        
        # Check if flag already exists
        if Flag.objects.filter(name=name).exists():
            return JsonResponse({'error': f'Flag "{name}" already exists'}, status=400)
        
        # Get user IDs if provided
        user_ids = data.get('users', [])
        if not isinstance(user_ids, list):
            user_ids = []
        
        # Create the flag
        flag = Flag.objects.create(
            name=name,
            everyone=everyone if everyone is not None else None,
            percent=percent if percent is not None else None,
            superusers=superusers,
            staff=staff,
            authenticated=authenticated,
            testing=testing,
            rollout=rollout,
            note=note or ''
        )
        
        # Assign users to the flag if provided
        if user_ids:
            users = User.objects.filter(id__in=user_ids)
            flag.users.set(users)
        
        # Log the activity
        try:
            UserActivityLog.objects.create(
                user=request.user,
                action='create',
                resource=f'Flag Management - Create Flag',
                method=request.method,
                status_code=200,
                response_time=0.0,
                request_data={'details': f'Created flag: {name}'},
                **get_connection_ip_fields_for_log(request),
                user_agent=request.META.get('HTTP_USER_AGENT', 'Unknown')
            )
        except Exception:
            pass  # Don't fail if logging fails
        
        return JsonResponse({
            'success': True,
            'message': f'Flag "{name}" created successfully',
            'flag': {
                'id': flag.id,
                'name': flag.name,
                'everyone': flag.everyone,
                'percent': flag.percent,
                'superusers': flag.superusers,
                'staff': flag.staff,
                'authenticated': flag.authenticated,
                'testing': flag.testing,
                'rollout': flag.rollout,
                'note': flag.note,
                'users': [
                    {
                        'id': user.id,
                        'username': user.username,
                        'email': user.email,
                    }
                    for user in flag.users.all()
                ] if hasattr(flag, 'users') else [],
            }
        })
    except Exception as e:
        import traceback
        error_msg = str(e)
        error_traceback = traceback.format_exc()
        # Log the error for debugging
        logging.getLogger(__name__).error(f"Error creating flag: {error_msg}\n{error_traceback}")
        # Return JSON error (not HTML)
        return JsonResponse({
            'error': f'Error creating flag: {error_msg}',
            'detail': error_traceback if settings.DEBUG else None
        }, status=500)


@login_required
@superuser_required
def update_flag(request, flag_id):
    """Update an existing waffle flag"""
    from waffle.models import Flag
    
    if request.method == 'POST':
        try:
            flag = get_object_or_404(Flag, id=flag_id)
            data = json.loads(request.body)
            
            name = data.get('name', '').strip()
            everyone = data.get('everyone', None)
            percent = data.get('percent', None)
            superusers = data.get('superusers', False)
            staff = data.get('staff', False)
            authenticated = data.get('authenticated', False)
            testing = data.get('testing', False)
            rollout = data.get('rollout', False)
            note = data.get('note', '').strip()
            
            if not name:
                return JsonResponse({'error': 'Flag name is required'}, status=400)
            
            # Check if name is being changed and if new name already exists
            if name != flag.name and Flag.objects.filter(name=name).exists():
                return JsonResponse({'error': f'Flag "{name}" already exists'}, status=400)
            
            # Get user IDs if provided
            user_ids = data.get('users', None)
            
            # Update the flag
            flag.name = name
            flag.everyone = everyone if everyone is not None else None
            flag.percent = percent if percent is not None else None
            flag.superusers = superusers
            flag.staff = staff
            flag.authenticated = authenticated
            flag.testing = testing
            flag.rollout = rollout
            flag.note = note or ''
            flag.save()
            
            # Update user assignments if provided
            if user_ids is not None:
                if isinstance(user_ids, list) and len(user_ids) > 0:
                    users = User.objects.filter(id__in=user_ids)
                    flag.users.set(users)
                else:
                    # Clear all user assignments
                    flag.users.clear()
            
            # Log the activity
            try:
                UserActivityLog.objects.create(
                    user=request.user,
                    action='update',
                    resource=f'Flag Management - Update Flag',
                    method=request.method,
                    status_code=200,
                    response_time=0.0,
                    request_data={'details': f'Updated flag: {name}'},
                    **get_connection_ip_fields_for_log(request),
                    user_agent=request.META.get('HTTP_USER_AGENT', 'Unknown')
                )
            except Exception:
                pass  # Don't fail if logging fails
            
            return JsonResponse({
                'success': True,
                'message': f'Flag "{name}" updated successfully',
                'flag': {
                    'id': flag.id,
                    'name': flag.name,
                    'everyone': flag.everyone,
                    'percent': flag.percent,
                    'superusers': flag.superusers,
                    'staff': flag.staff,
                    'authenticated': flag.authenticated,
                    'testing': flag.testing,
                    'rollout': flag.rollout,
                    'note': flag.note,
                    'users': [
                        {
                            'id': user.id,
                            'username': user.username,
                            'email': user.email,
                        }
                        for user in flag.users.all()
                    ] if hasattr(flag, 'users') else [],
                }
            })
        except json.JSONDecodeError as e:
            return JsonResponse({'error': f'Invalid JSON: {str(e)}'}, status=400)
        except Exception as e:
            import traceback
            error_msg = str(e)
            error_traceback = traceback.format_exc()
            # Log the error for debugging
            logging.getLogger(__name__).error(f"Error updating flag: {error_msg}\n{error_traceback}")
            # Return JSON error (not HTML)
            return JsonResponse({
                'error': f'Error updating flag: {error_msg}',
                'detail': error_traceback if settings.DEBUG else None
            }, status=500)
    
    return JsonResponse({'error': 'Method not allowed'}, status=405)


@login_required
@superuser_required
def export_flags_csv(request):
    """Export all waffle flags to CSV file"""
    from waffle.models import Flag
    import csv
    from django.http import HttpResponse
    from django.utils import timezone
    
    try:
        flags = Flag.objects.all().order_by('name')
        
        # Create CSV response
        response = HttpResponse(content_type='text/csv; charset=utf-8')
        response['Content-Disposition'] = f'attachment; filename="waffle_flags_export_{timezone.now().strftime("%Y%m%d_%H%M%S")}.csv"'
        
        # Write BOM for Excel compatibility
        response.write('\ufeff')
        
        writer = csv.writer(response)
        
        # Write header
        writer.writerow([
            'name', 'everyone', 'percent', 'superusers', 'staff', 
            'authenticated', 'rollout', 'note'
        ])
        
        # Write flag data
        for flag in flags:
            writer.writerow([
                flag.name,
                'True' if flag.everyone is True else 'False' if flag.everyone is False else '',
                flag.percent if flag.percent is not None else '',
                'True' if flag.superusers else 'False',
                'True' if flag.staff else 'False',
                'True' if flag.authenticated else 'False',
                'True' if flag.rollout else 'False',
                getattr(flag, 'note', '') or '',
            ])
        
        # Log the activity
        try:
            UserActivityLog.objects.create(
                user=request.user,
                action='download',
                resource='Flag Management - Export CSV',
                method=request.method,
                status_code=200,
                response_time=0.0,
                request_data={'details': f'Exported {flags.count()} flags to CSV'},
                **get_connection_ip_fields_for_log(request),
                user_agent=request.META.get('HTTP_USER_AGENT', 'Unknown')
            )
        except Exception:
            pass  # Don't fail if logging fails
        
        return response
        
    except Exception as e:
        return JsonResponse({'error': f'Error exporting flags: {str(e)}'}, status=500)


@login_required
@superuser_required
def import_flags_csv(request):
    """Import waffle flags from CSV file"""
    from waffle.models import Flag
    import csv
    import io
    
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)
    
    try:
        if 'file' not in request.FILES:
            return JsonResponse({'error': 'No file uploaded'}, status=400)
        
        csv_file = request.FILES['file']
        
        # Read CSV file
        decoded_file = csv_file.read().decode('utf-8-sig')  # Handle BOM
        io_string = io.StringIO(decoded_file)
        reader = csv.DictReader(io_string)
        
        created_count = 0
        updated_count = 0
        skipped_count = 0
        errors = []
        
        update_existing = request.POST.get('update_existing', 'false').lower() == 'true'
        
        for row_num, row in enumerate(reader, start=2):  # Start at 2 (header is row 1)
            try:
                name = row.get('name', '').strip()
                if not name:
                    errors.append(f'Row {row_num}: Missing flag name')
                    skipped_count += 1
                    continue
                
                # Parse boolean values
                def parse_bool(value):
                    if not value or value.strip() == '':
                        return None
                    val = value.strip().lower()
                    if val in ('true', '1', 'yes', 'on'):
                        return True
                    elif val in ('false', '0', 'no', 'off'):
                        return False
                    return None
                
                everyone = parse_bool(row.get('everyone', ''))
                percent_str = row.get('percent', '').strip()
                percent = int(percent_str) if percent_str and percent_str.isdigit() else None
                superusers = parse_bool(row.get('superusers', '')) or False
                staff = parse_bool(row.get('staff', '')) or False
                authenticated = parse_bool(row.get('authenticated', '')) or False
                rollout = parse_bool(row.get('rollout', '')) or False
                note = row.get('note', '').strip()
                
                # Check if flag exists
                existing_flag = Flag.objects.filter(name=name).first()
                
                if existing_flag:
                    if update_existing:
                        existing_flag.everyone = everyone
                        existing_flag.percent = percent
                        existing_flag.superusers = superusers
                        existing_flag.staff = staff
                        existing_flag.authenticated = authenticated
                        existing_flag.rollout = rollout
                        if hasattr(existing_flag, 'note'):
                            existing_flag.note = note or ''
                        existing_flag.save()
                        updated_count += 1
                    else:
                        skipped_count += 1
                else:
                    Flag.objects.create(
                        name=name,
                        everyone=everyone,
                        percent=percent,
                        superusers=superusers,
                        staff=staff,
                        authenticated=authenticated,
                        rollout=rollout,
                        note=note or ''
                    )
                    created_count += 1
                    
            except Exception as e:
                errors.append(f'Row {row_num}: {str(e)}')
                skipped_count += 1
        
        # Log the activity
        try:
            UserActivityLog.objects.create(
                user=request.user,
                action='upload',
                resource='Flag Management - Import CSV',
                method=request.method,
                status_code=200,
                response_time=0.0,
                request_data={
                    'details': f'Imported flags: {created_count} created, {updated_count} updated, {skipped_count} skipped'
                },
                **get_connection_ip_fields_for_log(request),
                user_agent=request.META.get('HTTP_USER_AGENT', 'Unknown')
            )
        except Exception:
            pass  # Don't fail if logging fails
        
        message = f'Import completed: {created_count} created, {updated_count} updated, {skipped_count} skipped'
        if errors:
            message += f'. {len(errors)} errors occurred.'
        
        return JsonResponse({
            'success': True,
            'message': message,
            'created': created_count,
            'updated': updated_count,
            'skipped': skipped_count,
            'errors': errors[:10]  # Limit errors to first 10
        })
        
    except Exception as e:
        return JsonResponse({'error': f'Error importing flags: {str(e)}'}, status=500)


@login_required
@superuser_required
def delete_flag(request, flag_id):
    """Delete a waffle flag"""
    from waffle.models import Flag
    
    if request.method == 'POST':
        try:
            flag = get_object_or_404(Flag, id=flag_id)
            flag_name = flag.name
            
            # Log the activity before deletion
            try:
                UserActivityLog.objects.create(
                    user=request.user,
                    action='delete',
                    resource=f'Flag Management - Delete Flag',
                    method=request.method,
                    status_code=200,
                    response_time=0.0,
                    request_data={'details': f'Deleted flag: {flag_name}'},
                    **get_connection_ip_fields_for_log(request),
                    user_agent=request.META.get('HTTP_USER_AGENT', 'Unknown')
                )
            except Exception:
                pass  # Don't fail if logging fails
            
            flag.delete()
            
            return JsonResponse({
                'success': True,
                'message': f'Flag "{flag_name}" deleted successfully'
            })
        except Exception as e:
            return JsonResponse({'error': f'Error deleting flag: {str(e)}'}, status=500)


@superuser_required
@login_required
@superuser_required
def user_management_logs(request):
    """
    View all user management activity logs and blocking logs - Superuser only
    Shows logs for user creation, update, deletion, activation, deactivation, and blocking
    """
    # Determine which tab is active (default to activity logs)
    active_tab = request.GET.get('tab', 'activity')
    
    # Check if UserActivityLog model is available
    activity_logs_available = UserActivityLog is not None
    blocking_logs_available = UserBlockingLog is not None
    
    context = {
        'active_tab': active_tab,
        'activity_logs_available': activity_logs_available,
        'blocking_logs_available': blocking_logs_available,
    }
    
    # Process Activity Logs
    if activity_logs_available:
        # Filter for user management related activities
        user_management_resources = [
            'User Management - Create User',
            'User Management - Update User Access',
            'User Management - Delete User',
            'User Management - Deactivate',
            'User Management - Reactivate',
        ]
        
        # Get filter parameters for activity logs
        action_filter = request.GET.get('action', '')
        search_query = request.GET.get('search', '').strip()
        date_from = request.GET.get('date_from', '').strip()
        date_to = request.GET.get('date_to', '').strip()
        
        # Base queryset - filter for user management activities
        queryset = UserActivityLog.objects.filter(
            resource__in=user_management_resources
        ).select_related('user').order_by('-timestamp')
        
        # Apply filters
        if action_filter:
            queryset = queryset.filter(action=action_filter)
        
        if search_query:
            queryset = queryset.filter(
                Q(user__username__icontains=search_query) |
                Q(details__icontains=search_query) |
                Q(resource__icontains=search_query)
            )
        
        if date_from:
            try:
                from datetime import datetime
                date_from_dt = datetime.strptime(date_from, '%Y-%m-%d')
                queryset = queryset.filter(timestamp__gte=date_from_dt)
            except ValueError:
                pass
        
        if date_to:
            try:
                from datetime import datetime
                date_to_dt = datetime.strptime(date_to, '%Y-%m-%d')
                # Add one day to include the entire end date
                from datetime import timedelta
                date_to_dt = date_to_dt + timedelta(days=1)
                queryset = queryset.filter(timestamp__lt=date_to_dt)
            except ValueError:
                pass
        
        # Get statistics (before pagination)
        total_count = queryset.count()
        action_counts = queryset.values('action').annotate(
            count=Count('id')
        ).order_by('-count')
        
        # Pagination - show last 50 logs by default
        from django.core.paginator import Paginator
        paginator = Paginator(queryset, 50)  # Show 50 logs per page
        page_number = request.GET.get('page', 1)
        
        # If no filters are applied and it's the first page, show the most recent 50 logs
        # (queryset is already ordered by -timestamp, so first page = most recent)
        page_obj = paginator.get_page(page_number)
        
        context.update({
            'activity_logs': page_obj,
            'activity_total_count': total_count,
            'action_counts': action_counts,
            'action_filter': action_filter,
            'search_query': search_query,
            'date_from': date_from,
            'date_to': date_to,
            'actions': ['create', 'update', 'delete'],
        })
    else:
        context.update({
            'activity_logs': [],
            'activity_total_count': 0,
            'action_counts': [],
            'action_filter': '',
            'search_query': '',
            'date_from': '',
            'date_to': '',
            'actions': ['create', 'update', 'delete'],
        })
    
    # Process Blocking Logs (Superuser only)
    if blocking_logs_available and request.user.is_superuser:
        # Get filter parameters for blocking logs
        block_type_filter = request.GET.get('block_type', '').strip()
        block_reason_filter = request.GET.get('block_reason', '').strip()
        status_filter = request.GET.get('status', '').strip()
        blocking_search_query = request.GET.get('blocking_search', '').strip()
        blocking_date_from = request.GET.get('blocking_date_from', '').strip()
        blocking_date_to = request.GET.get('blocking_date_to', '').strip()
        export_csv = request.GET.get('export', '').strip() == 'csv'
        
        # Base queryset
        blocking_queryset = UserBlockingLog.objects.select_related(
            'user', 'blocked_by', 'unblocked_by'
        ).order_by('-blocked_at')
        
        # Apply filters
        if block_type_filter:
            blocking_queryset = blocking_queryset.filter(block_type=block_type_filter)
        
        if block_reason_filter:
            blocking_queryset = blocking_queryset.filter(block_reason=block_reason_filter)
        
        if status_filter:
            blocking_queryset = blocking_queryset.filter(status=status_filter)
        
        if blocking_search_query:
            blocking_queryset = blocking_queryset.filter(
                Q(user__username__icontains=blocking_search_query) |
                Q(reason_details__icontains=blocking_search_query) |
                Q(ip_address__icontains=blocking_search_query) |
                Q(user_agent__icontains=blocking_search_query)
            )
        
        if blocking_date_from:
            try:
                from datetime import datetime
                date_from_dt = datetime.strptime(blocking_date_from, '%Y-%m-%d')
                blocking_queryset = blocking_queryset.filter(blocked_at__gte=date_from_dt)
            except ValueError:
                pass
        
        if blocking_date_to:
            try:
                from datetime import datetime
                date_to_dt = datetime.strptime(blocking_date_to, '%Y-%m-%d')
                # Add one day to include the entire end date
                from datetime import timedelta
                date_to_dt = date_to_dt + timedelta(days=1)
                blocking_queryset = blocking_queryset.filter(blocked_at__lt=date_to_dt)
            except ValueError:
                pass
        
        # CSV Export
        if export_csv and active_tab == 'blocking':
            response = HttpResponse(content_type='text/csv')
            filename = f'user_blocking_logs_{timezone.now().strftime("%Y%m%d_%H%M%S")}.csv'
            response['Content-Disposition'] = f'attachment; filename="{filename}"'
            
            writer = csv.writer(response)
            
            # Write header
            writer.writerow([
                'ID', 'Username', 'Block Type', 'Block Reason', 'Reason Details',
                'Status', 'Blocked At', 'Unblocked At', 'IP Address', 'User Agent',
                'Country', 'City', 'Failed Attempts', 'Suspicious Activities',
                'Blocked By', 'Unblocked By', 'Unblock Reason', 'Expires At'
            ])
            
            # Write data
            for log in blocking_queryset:
                writer.writerow([
                    log.id,
                    log.user.username if log.user else 'N/A',
                    log.get_block_type_display(),
                    log.get_block_reason_display(),
                    log.reason_details,
                    log.get_status_display(),
                    log.blocked_at.strftime('%Y-%m-%d %H:%M:%S') if log.blocked_at else '',
                    log.unblocked_at.strftime('%Y-%m-%d %H:%M:%S') if log.unblocked_at else '',
                    log.ip_address,
                    log.user_agent,
                    log.country,
                    log.city,
                    log.failed_attempts,
                    log.suspicious_activities,
                    log.blocked_by.username if log.blocked_by else '',
                    log.unblocked_by.username if log.unblocked_by else '',
                    log.unblock_reason,
                    log.expires_at.strftime('%Y-%m-%d %H:%M:%S') if log.expires_at else '',
                ])
            
            return response
        
        # Get statistics (before pagination)
        blocking_total_count = blocking_queryset.count()
        
        # Pagination - show last 50 logs by default
        from django.core.paginator import Paginator
        blocking_paginator = Paginator(blocking_queryset, 50)
        blocking_page_number = request.GET.get('blocking_page', 1)
        blocking_page_obj = blocking_paginator.get_page(blocking_page_number)
        
        # Get filter statistics
        block_type_counts = blocking_queryset.values('block_type').annotate(
            count=Count('id')
        ).order_by('-count')
        
        block_reason_counts = blocking_queryset.values('block_reason').annotate(
            count=Count('id')
        ).order_by('-count')
        
        status_counts = blocking_queryset.values('status').annotate(
            count=Count('id')
        ).order_by('-count')
        
        context.update({
            'blocking_logs': blocking_page_obj,
            'blocking_total_count': blocking_total_count,
            'block_type_filter': block_type_filter,
            'block_reason_filter': block_reason_filter,
            'status_filter': status_filter,
            'blocking_search_query': blocking_search_query,
            'blocking_date_from': blocking_date_from,
            'blocking_date_to': blocking_date_to,
            'block_type_counts': block_type_counts,
            'block_reason_counts': block_reason_counts,
            'status_counts': status_counts,
            'block_types': UserBlockingLog.BLOCK_TYPE_CHOICES,
            'block_reasons': UserBlockingLog.BLOCK_REASON_CHOICES,
            'statuses': UserBlockingLog.STATUS_CHOICES,
        })
    else:
        context.update({
            'blocking_logs': [],
            'blocking_total_count': 0,
            'block_type_filter': '',
            'block_reason_filter': '',
            'status_filter': '',
            'blocking_search_query': '',
            'blocking_date_from': '',
            'blocking_date_to': '',
            'block_type_counts': [],
            'block_reason_counts': [],
            'status_counts': [],
            'block_types': [],
            'block_reasons': [],
            'statuses': [],
        })
    
    return render(request, 'main/user_management_logs.html', context)


@login_required
@superuser_required
def user_blocking_logs_view(request):
    """
    View user blocking logs with date filter and CSV export - Superuser only
    Shows all UserBlockingLog entries with filtering and export capabilities
    """
    try:
        # Check if UserBlockingLog model is available
        if not UserBlockingLog:
            messages.error(request, 'Blocking logs not available. Please run migrations.')
            return render(request, 'main/user_blocking_logs.html', {
                'logs': [],
                'total_count': 0,
            })
        
        # Get filter parameters
        block_type_filter = request.GET.get('block_type', '').strip()
        block_reason_filter = request.GET.get('block_reason', '').strip()
        status_filter = request.GET.get('status', '').strip()
        search_query = request.GET.get('search', '').strip()
        date_from = request.GET.get('date_from', '').strip()
        date_to = request.GET.get('date_to', '').strip()
        export_csv = request.GET.get('export', '').strip() == 'csv'
        
        # Base queryset
        queryset = UserBlockingLog.objects.select_related(
            'user', 'blocked_by', 'unblocked_by'
        ).order_by('-blocked_at')
        
        # Apply filters
        if block_type_filter:
            queryset = queryset.filter(block_type=block_type_filter)
        
        if block_reason_filter:
            queryset = queryset.filter(block_reason=block_reason_filter)
        
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        
        if search_query:
            queryset = queryset.filter(
                Q(user__username__icontains=search_query) |
                Q(reason_details__icontains=search_query) |
                Q(ip_address__icontains=search_query) |
                Q(user_agent__icontains=search_query)
            )
        
        if date_from:
            try:
                from datetime import datetime
                date_from_dt = datetime.strptime(date_from, '%Y-%m-%d')
                queryset = queryset.filter(blocked_at__gte=date_from_dt)
            except ValueError:
                pass
        
        if date_to:
            try:
                from datetime import datetime
                date_to_dt = datetime.strptime(date_to, '%Y-%m-%d')
                # Add one day to include the entire end date
                date_to_dt = date_to_dt + timedelta(days=1)
                queryset = queryset.filter(blocked_at__lt=date_to_dt)
            except ValueError:
                pass
        
        # Get statistics (before pagination)
        total_count = queryset.count()
        
        # CSV Export
        if export_csv:
            response = HttpResponse(content_type='text/csv')
            filename = f'user_blocking_logs_{timezone.now().strftime("%Y%m%d_%H%M%S")}.csv'
            response['Content-Disposition'] = f'attachment; filename="{filename}"'
            
            writer = csv.writer(response)
            
            # Write header
            writer.writerow([
                'ID', 'Username', 'Block Type', 'Block Reason', 'Reason Details',
                'Status', 'Blocked At', 'Unblocked At', 'IP Address', 'User Agent',
                'Country', 'City', 'Failed Attempts', 'Suspicious Activities',
                'Blocked By', 'Unblocked By', 'Unblock Reason', 'Expires At'
            ])
            
            # Write data
            for log in queryset:
                writer.writerow([
                    log.id,
                    log.user.username if log.user else 'N/A',
                    log.get_block_type_display(),
                    log.get_block_reason_display(),
                    log.reason_details,
                    log.get_status_display(),
                    log.blocked_at.strftime('%Y-%m-%d %H:%M:%S') if log.blocked_at else '',
                    log.unblocked_at.strftime('%Y-%m-%d %H:%M:%S') if log.unblocked_at else '',
                    log.ip_address,
                    log.user_agent,
                    log.country,
                    log.city,
                    log.failed_attempts,
                    log.suspicious_activities,
                    log.blocked_by.username if log.blocked_by else '',
                    log.unblocked_by.username if log.unblocked_by else '',
                    log.unblock_reason,
                    log.expires_at.strftime('%Y-%m-%d %H:%M:%S') if log.expires_at else '',
                ])
            
            return response
        
        # Pagination - show last 50 logs by default
        from django.core.paginator import Paginator
        paginator = Paginator(queryset, 50)
        page_number = request.GET.get('page', 1)
        page_obj = paginator.get_page(page_number)
        
        # Get filter statistics
        block_type_counts = queryset.values('block_type').annotate(
            count=Count('id')
        ).order_by('-count')
        
        block_reason_counts = queryset.values('block_reason').annotate(
            count=Count('id')
        ).order_by('-count')
        
        status_counts = queryset.values('status').annotate(
            count=Count('id')
        ).order_by('-count')
        
        context = {
            'logs': page_obj,
            'total_count': total_count,
            'block_type_filter': block_type_filter,
            'block_reason_filter': block_reason_filter,
            'status_filter': status_filter,
            'search_query': search_query,
            'date_from': date_from,
            'date_to': date_to,
            'block_type_counts': block_type_counts,
            'block_reason_counts': block_reason_counts,
            'status_counts': status_counts,
            'block_types': UserBlockingLog.BLOCK_TYPE_CHOICES,
            'block_reasons': UserBlockingLog.BLOCK_REASON_CHOICES,
            'statuses': UserBlockingLog.STATUS_CHOICES,
        }
        
        return render(request, 'main/user_blocking_logs.html', context)
        
    except Exception as e:
        logger.error(f"Error loading user blocking logs: {str(e)}")
        messages.error(request, f'Error loading blocking logs: {str(e)}')
        return render(request, 'main/user_blocking_logs.html', {
            'logs': [],
            'total_count': 0,
            'error': str(e),
        })


@login_required
@superuser_required
def assign_flags_to_user(request):
    """Assign multiple flags to a user"""
    from waffle.models import Flag
    
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            user_id = data.get('user_id')
            flag_ids = data.get('flag_ids', [])
            
            if not user_id:
                return JsonResponse({'error': 'User ID is required'}, status=400)
            
            if not isinstance(flag_ids, list):
                return JsonResponse({'error': 'Flag IDs must be a list'}, status=400)
            
            # Get the user
            user = get_object_or_404(User, id=user_id)
            
            # Get all flags
            all_flags = Flag.objects.all()
            
            # Assign selected flags to the user
            if flag_ids:
                selected_flags = Flag.objects.filter(id__in=flag_ids)
                for flag in selected_flags:
                    flag.users.add(user)
            
            # Remove user from flags that are not in the selected list
            for flag in all_flags:
                if flag.id not in flag_ids:
                    flag.users.remove(user)
            
            # Log the activity
            try:
                UserActivityLog.objects.create(
                    user=request.user,
                    action='update',
                    resource='Flag Management - Assign Flags to User',
                    method=request.method,
                    status_code=200,
                    response_time=0.0,
                    request_data={
                        'details': f'Assigned {len(flag_ids)} flag(s) to user: {user.username}'
                    },
                    **get_connection_ip_fields_for_log(request),
                    user_agent=request.META.get('HTTP_USER_AGENT', 'Unknown')
                )
            except Exception:
                pass  # Don't fail if logging fails
            
            return JsonResponse({
                'success': True,
                'message': f'Successfully assigned {len(flag_ids)} flag(s) to {user.username}'
            })
        except json.JSONDecodeError:
            return JsonResponse({'error': 'Invalid JSON'}, status=400)
        except Exception as e:
            return JsonResponse({'error': f'Error assigning flags: {str(e)}'}, status=500)
    
    return JsonResponse({'error': 'Method not allowed'}, status=405)

