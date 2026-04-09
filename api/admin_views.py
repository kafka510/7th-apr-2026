"""
API Admin Views
---------------
Web-based API configuration interface for administrators
"""

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.contrib.auth.models import User
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.apps import apps
from .models import APIUser, APIKey, TablePermission, ColumnRestriction, APIRequestLog, FailedAuthAttempt, BlockedAPIIP
from .forms import (
    SetupAPIPermissionsForm, GrantTableAccessForm,
    RestrictColumnForm, GenerateAPIKeyForm, UpdateRateLimitsForm
)
from .brute_force_protection import brute_force_protector
from django.core.cache import cache
from django.utils import timezone
import json

from main.permissions import user_has_capability


def is_admin(user):
    """Check if user is admin role or superuser"""
    if getattr(user, "is_superuser", False):
        return True
    return user_has_capability(user, 'api.manage')


@login_required
@user_passes_test(is_admin)
def api_config_dashboard(request):
    """
    Main API configuration dashboard
    """
    # Get statistics (exclude web_only users - they don't have API access)
    total_api_users = APIUser.objects.exclude(access_level='web_only').count()
    active_api_users = APIUser.objects.exclude(access_level='web_only').filter(status='active').count()
    total_api_keys = APIKey.objects.count()
    active_api_keys = APIKey.objects.filter(status='active').count()
    total_requests = APIRequestLog.objects.count()
    
    # Recent API users (exclude web_only)
    recent_api_users = APIUser.objects.exclude(access_level='web_only').order_by('-created_at')[:5]
    
    # Recent API keys
    recent_api_keys = APIKey.objects.all().order_by('-created_at')[:5]
    
    # Recent requests
    recent_requests = APIRequestLog.objects.all().order_by('-timestamp')[:10]
    
    context = {
        'total_api_users': total_api_users,
        'active_api_users': active_api_users,
        'total_api_keys': total_api_keys,
        'active_api_keys': active_api_keys,
        'total_requests': total_requests,
        'recent_api_users': recent_api_users,
        'recent_api_keys': recent_api_keys,
        'recent_requests': recent_requests,
    }
    
    return render(request, 'api/admin/dashboard.html', context)


@login_required
@user_passes_test(is_admin)
def create_api_user(request):
    """
    Redirect to user management page for creating users
    """
    messages.info(request, 'Please use the User Management page to create users with API access. This ensures proper site access control and user profile creation.')
    return redirect('main:user_management')


@login_required
@user_passes_test(is_admin)
def setup_api_permissions(request):
    """
    Setup API permissions for a user
    """
    if request.method == 'POST':
        form = SetupAPIPermissionsForm(request.POST)
        if form.is_valid():
            user = form.cleaned_data['user']
            
            # Create or update APIUser
            api_user, created = APIUser.objects.update_or_create(
                user=user,
                defaults={
                    'name': form.cleaned_data['name'],
                    'description': form.cleaned_data['description'],
                    'status': 'active',
                    'rate_limit_per_minute': form.cleaned_data['rate_limit_per_minute'],
                    'rate_limit_per_hour': form.cleaned_data['rate_limit_per_hour'],
                    'rate_limit_per_day': form.cleaned_data['rate_limit_per_day'],
                    'allowed_ips': form.cleaned_data['allowed_ips']
                }
            )
            
            # Grant table permissions
            if form.cleaned_data['grant_all_tables']:
                tables = [t[0] for t in SetupAPIPermissionsForm.ALL_TABLES]
            else:
                tables = form.cleaned_data['tables']
            
            for table_name in tables:
                TablePermission.objects.get_or_create(
                    api_user=api_user,
                    table_name=table_name,
                    defaults={
                        'can_read': True,
                        'can_filter': form.cleaned_data['can_filter'],
                        'can_aggregate': form.cleaned_data['can_aggregate'],
                        'max_records_per_request': form.cleaned_data['max_records_per_request']
                    }
                )
            
            action = 'created' if created else 'updated'
            messages.success(request, f'API permissions {action} for user "{user.username}". Access granted to {len(tables)} table(s).')
            return redirect('api:api_config_dashboard')
    else:
        form = SetupAPIPermissionsForm()
    
    context = {
        'form': form,
        'title': 'Setup API Permissions'
    }
    
    return render(request, 'api/admin/setup_permissions.html', context)


@login_required
@user_passes_test(is_admin)
def manage_api_users(request):
    """
    View and manage all API users
    Only show users with API access (api_only or both), not web_only users
    """
    # Filter to only show users with API access - exclude web_only users
    api_users = APIUser.objects.exclude(access_level='web_only').order_by('-created_at')
    
    context = {
        'api_users': api_users,
        'title': 'Manage API Users'
    }
    
    return render(request, 'api/admin/manage_users.html', context)


@login_required
@user_passes_test(is_admin)
def view_api_user(request, user_id):
    """
    View details of a specific API user
    """
    api_user = APIUser.objects.get(id=user_id)
    
    # Get API keys
    api_keys = APIKey.objects.filter(api_user=api_user).order_by('-created_at')
    
    # Get table permissions
    table_permissions = TablePermission.objects.filter(api_user=api_user).order_by('table_name')
    
    # Get column restrictions
    column_restrictions = ColumnRestriction.objects.filter(
        table_permission__api_user=api_user
    ).select_related('table_permission')
    
    # Get recent requests
    recent_requests = APIRequestLog.objects.filter(
        api_key__api_user=api_user
    ).order_by('-timestamp')[:20]
    
    context = {
        'api_user': api_user,
        'api_keys': api_keys,
        'table_permissions': table_permissions,
        'column_restrictions': column_restrictions,
        'recent_requests': recent_requests,
        'title': f'API User: {api_user.name}'
    }
    
    return render(request, 'api/admin/view_user.html', context)


@login_required
@user_passes_test(is_admin)
def generate_key_for_user(request):
    """
    Generate API key for a user (admin function)
    """
    if request.method == 'POST':
        form = GenerateAPIKeyForm(request.POST)
        if form.is_valid():
            user = form.cleaned_data['user']
            
            # Get or create APIUser
            api_user, created = APIUser.objects.get_or_create(
                user=user,
                defaults={
                    'name': f"{user.username}'s API Access",
                    'description': 'Created by administrator',
                    'status': 'active'
                }
            )
            
            # Generate API key
            api_key, plaintext_key = APIKey.create_key(
                api_user=api_user,
                name=form.cleaned_data['name'],
                expires_in_days=form.cleaned_data.get('expires_in_days')
            )
            
            messages.success(request, f'API key generated for user "{user.username}"')
            
            # Show the key in a modal or separate page
            context = {
                'api_key': plaintext_key,
                'key_object': api_key,
                'user': user,
                'title': 'API Key Generated'
            }
            
            return render(request, 'api/admin/key_generated.html', context)
    else:
        form = GenerateAPIKeyForm()
    
    context = {
        'form': form,
        'title': 'Generate API Key for User'
    }
    
    return render(request, 'api/admin/generate_key.html', context)


@login_required
@user_passes_test(is_admin)
def grant_table_access(request):
    """
    Grant additional table access to existing API user
    """
    if request.method == 'POST':
        form = GrantTableAccessForm(request.POST)
        if form.is_valid():
            api_user = form.cleaned_data['api_user']
            tables = form.cleaned_data['tables']
            
            count = 0
            for table_name in tables:
                _, created = TablePermission.objects.get_or_create(
                    api_user=api_user,
                    table_name=table_name,
                    defaults={
                        'can_read': True,
                        'can_filter': form.cleaned_data['can_filter'],
                        'can_aggregate': form.cleaned_data['can_aggregate'],
                        'max_records_per_request': form.cleaned_data['max_records_per_request']
                    }
                )
                if created:
                    count += 1
            
            messages.success(request, f'Granted access to {count} new table(s) for "{api_user.name}"')
            return redirect('api:manage_api_users')
    else:
        form = GrantTableAccessForm()
    
    context = {
        'form': form,
        'title': 'Grant Table Access'
    }
    
    return render(request, 'api/admin/grant_table_access.html', context)


@login_required
@user_passes_test(is_admin)
def restrict_columns(request):
    """
    Add column restrictions
    """
    if request.method == 'POST':
        form = RestrictColumnForm(request.POST)
        if form.is_valid():
            api_user = form.cleaned_data['api_user']
            table_name = form.cleaned_data['table']
            columns = form.cleaned_data['columns']
            restriction_type = form.cleaned_data['restriction_type']
            
            # Get table permission
            try:
                table_permission = TablePermission.objects.get(
                    api_user=api_user,
                    table_name=table_name
                )
                
                count = 0
                for column_name in columns:
                    _, created = ColumnRestriction.objects.get_or_create(
                        table_permission=table_permission,
                        column_name=column_name,
                        defaults={'restriction_type': restriction_type}
                    )
                    if created:
                        count += 1
                
                messages.success(request, f'Restricted {count} column(s) in table "{table_name}" for "{api_user.name}"')
                return redirect('api:manage_api_users')
            except TablePermission.DoesNotExist:
                messages.error(request, f'User does not have access to table "{table_name}"')
    else:
        form = RestrictColumnForm()
    
    context = {
        'form': form,
        'title': 'Restrict Columns'
    }
    
    return render(request, 'api/admin/restrict_columns.html', context)


@login_required
@user_passes_test(is_admin)
@require_http_methods(["POST"])
def revoke_api_key_admin(request, key_id):
    """
    Revoke an API key (admin function)
    """
    try:
        api_key = APIKey.objects.get(id=key_id)
        api_key.status = 'revoked'
        api_key.save()
        
        messages.success(request, f'API key "{api_key.name}" has been revoked')
    except APIKey.DoesNotExist:
        messages.error(request, 'API key not found')
    
    return redirect(request.META.get('HTTP_REFERER', 'api:api_config_dashboard'))


@login_required
@user_passes_test(is_admin)
@require_http_methods(["POST"])
def toggle_api_user_status(request, user_id):
    """
    Toggle API user status (active/suspended)
    """
    try:
        api_user = APIUser.objects.get(id=user_id)
        
        if api_user.status == 'active':
            api_user.status = 'suspended'
            messages.warning(request, f'API access suspended for "{api_user.name}"')
        else:
            api_user.status = 'active'
            messages.success(request, f'API access activated for "{api_user.name}"')
        
        api_user.save()
    except APIUser.DoesNotExist:
        messages.error(request, 'API user not found')
    
    return redirect(request.META.get('HTTP_REFERER', 'api:api_config_dashboard'))


@login_required
@user_passes_test(lambda u: u.is_superuser)  # Superuser only
@require_http_methods(["POST"])
def delete_api_user(request, api_user_id):
    """
    Delete API user and all related API keys
    Superuser only - removes APIUser record and all API keys
    Django user account remains active
    """
    if not request.user.is_superuser:
        messages.error(request, 'Only superusers can delete API users.')
        return redirect('api:manage_api_users')
    
    try:
        api_user = get_object_or_404(APIUser, id=api_user_id)
        username = api_user.user.username
        
        # Delete all API keys for this user
        keys_deleted = APIKey.objects.filter(api_user=api_user).count()
        APIKey.objects.filter(api_user=api_user).delete()
        
        # Delete the APIUser record
        api_user.delete()
        
        messages.success(request, f'API access removed for "{username}". {keys_deleted} API key(s) deleted.')
    except Exception as e:
        messages.error(request, f'Error deleting API user: {str(e)}')
    
    return redirect('api:manage_api_users')


@login_required
@user_passes_test(is_admin)
@require_http_methods(["POST"])
def update_rate_limits(request, user_id):
    """
    Update rate limits for an API user
    """
    try:
        api_user = APIUser.objects.get(id=user_id)
        
        api_user.rate_limit_per_minute = int(request.POST.get('rate_limit_per_minute', 60))
        api_user.rate_limit_per_hour = int(request.POST.get('rate_limit_per_hour', 1000))
        api_user.rate_limit_per_day = int(request.POST.get('rate_limit_per_day', 10000))
        api_user.save()
        
        messages.success(request, f'Rate limits updated for "{api_user.name}"')
    except APIUser.DoesNotExist:
        messages.error(request, 'API user not found')
    except ValueError:
        messages.error(request, 'Invalid rate limit values')
    
    return redirect(request.META.get('HTTP_REFERER', 'api:api_config_dashboard'))


@login_required
@user_passes_test(is_admin)
def get_table_columns(request):
    """
    AJAX endpoint to get columns for a table
    """
    table_name = request.GET.get('table')
    api_user_id = request.GET.get('api_user')
    
    if not table_name:
        return JsonResponse({'error': 'Table name required'}, status=400)
    
    try:
        # Get model
        model = apps.get_model('main', table_name)
        
        # Get all columns
        columns = []
        for field in model._meta.get_fields():
            if hasattr(field, 'column'):
                columns.append({
                    'name': field.name,
                    'type': field.get_internal_type(),
                    'verbose_name': getattr(field, 'verbose_name', field.name)
                })
        
        # Get existing restrictions if api_user provided
        restricted = []
        if api_user_id:
            try:
                api_user = APIUser.objects.get(id=api_user_id)
                table_permission = TablePermission.objects.get(
                    api_user=api_user,
                    table_name=table_name
                )
                restricted = list(
                    ColumnRestriction.objects.filter(
                        table_permission=table_permission
                    ).values_list('column_name', flat=True)
                )
            except (APIUser.DoesNotExist, TablePermission.DoesNotExist):
                pass
        
        return JsonResponse({
            'columns': columns,
            'restricted': restricted
        })
    except LookupError:
        return JsonResponse({'error': 'Table not found'}, status=404)


@login_required
@user_passes_test(is_admin)
def api_logs(request):
    """
    View API request logs
    """
    logs = APIRequestLog.objects.all().order_by('-timestamp')[:100]
    
    # Filter by API user if specified
    api_user_id = request.GET.get('api_user')
    if api_user_id:
        logs = logs.filter(api_key__api_user_id=api_user_id)
    
    # Filter by status code
    status_code = request.GET.get('status')
    if status_code:
        logs = logs.filter(status_code=status_code)
    
    context = {
        'logs': logs,
        'title': 'API Request Logs'
    }
    
    return render(request, 'api/admin/logs.html', context)


@login_required
@user_passes_test(is_admin)
@require_http_methods(["POST"])
def remove_column_restriction(request, restriction_id):
    """
    Remove a column restriction
    """
    try:
        restriction = ColumnRestriction.objects.get(id=restriction_id)
        column_name = restriction.column_name
        table_name = restriction.table_permission.table_name
        restriction.delete()
        
        messages.success(request, f'Removed restriction on column "{column_name}" in table "{table_name}"')
    except ColumnRestriction.DoesNotExist:
        messages.error(request, 'Restriction not found')
    
    return redirect(request.META.get('HTTP_REFERER', 'api:api_config_dashboard'))


@login_required
@user_passes_test(is_admin)
@require_http_methods(["POST"])
def revoke_table_access(request, permission_id):
    """
    Revoke table access for an API user
    """
    try:
        permission = TablePermission.objects.get(id=permission_id)
        table_name = permission.table_name
        api_user_name = permission.api_user.name
        permission.delete()
        
        messages.success(request, f'Revoked access to table "{table_name}" for "{api_user_name}"')
    except TablePermission.DoesNotExist:
        messages.error(request, 'Permission not found')
    
    return redirect(request.META.get('HTTP_REFERER', 'api:api_config_dashboard'))


@login_required
@user_passes_test(is_admin)
def blocked_ips_view(request):
    """
    View and manage blocked API IPs
    Shows failed authentication attempts and blocked IPs
    """
    # Handle unblock request
    if request.method == 'POST' and 'unblock_ip' in request.POST:
        ip_to_unblock = request.POST.get('ip_address')
        notes = request.POST.get('notes', 'Manually unblocked by admin')
        
        success, message = brute_force_protector.unblock_ip(ip_to_unblock, notes)
        
        if success:
            messages.success(request, f'IP {ip_to_unblock} has been unblocked.')
        else:
            messages.error(request, message)
        
        return redirect('api:blocked_ips')
    
    # Get blocked IPs
    blocked_ips = BlockedAPIIP.objects.filter(status='active').order_by('-blocked_at')
    
    # Get recently expired blocks (for reference)
    expired_blocks = BlockedAPIIP.objects.filter(status='expired').order_by('-blocked_at')[:10]
    
    # Get recent failed attempts (last 100)
    recent_attempts = FailedAuthAttempt.objects.all().order_by('-created_at')[:100]
    
    # Get failure statistics
    from datetime import timedelta
    last_24h = timezone.now() - timedelta(hours=24)
    failed_attempts_24h = FailedAuthAttempt.objects.filter(created_at__gte=last_24h).count()
    unique_ips_24h = FailedAuthAttempt.objects.filter(created_at__gte=last_24h).values('ip_address').distinct().count()
    
    # Group attempts by IP (top offenders)
    from django.db.models import Count
    top_offenders = FailedAuthAttempt.objects.filter(
        created_at__gte=last_24h
    ).values('ip_address').annotate(
        attempt_count=Count('id')
    ).order_by('-attempt_count')[:10]
    
    context = {
        'blocked_ips': blocked_ips,
        'expired_blocks': expired_blocks,
        'recent_attempts': recent_attempts,
        'failed_attempts_24h': failed_attempts_24h,
        'unique_ips_24h': unique_ips_24h,
        'top_offenders': top_offenders,
        'config': {
            'max_attempts': brute_force_protector.MAX_ATTEMPTS_PER_IP,
            'window_minutes': brute_force_protector.ATTEMPT_WINDOW_MINUTES,
            'block_duration': brute_force_protector.BLOCK_DURATION_MINUTES,
            'token_rate_limit': brute_force_protector.TOKEN_REQUEST_LIMIT,
        }
    }
    
    return render(request, 'api/admin/blocked_ips.html', context)

