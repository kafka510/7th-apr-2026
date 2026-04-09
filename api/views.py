"""
API Views
---------
Complete API endpoints for:
- Authentication & token management
- Schema discovery
- Dynamic data access
- API key management
"""

from django.http import JsonResponse
from django.shortcuts import render, redirect
from django.views.decorators.http import require_http_methods
from django.db import connection
from django.apps import apps
from django.utils import timezone
from .authentication import (
    require_api_auth, require_table_permission,
    get_client_ip, get_user_agent, extract_api_credentials
)
from .models import APIUser, APIKey, ActiveToken, TablePermission, ColumnRestriction
from main.models import AssetList
from main.permissions import user_has_capability
from .brute_force_protection import brute_force_protector
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.contrib import messages
import json
import logging
from datetime import timedelta

logger = logging.getLogger(__name__)


# =============================================================================
# API Manual - For API-only users
# =============================================================================

@login_required
def api_manual(request):
    """
    API Documentation page for users with API access
    Shows comprehensive API documentation
    RESTRICTED: Only users with API access (api_only or both) can view
    """
    try:
        # Check if user has API access
        from .models import APIUser, APIKey
        try:
            api_user = APIUser.objects.get(user=request.user)
            if not api_user.has_api_access():
                messages.error(request, 'You do not have API access. Please contact an administrator to request API access.')
                return redirect('main:unified_dashboard')
        except APIUser.DoesNotExist:
            messages.error(request, 'You do not have API access. Please contact an administrator to request API access.')
            return redirect('main:unified_dashboard')
        
        # Check if React version is enabled via waffle flag
        from waffle import flag_is_active
        use_react = flag_is_active(request, 'react_api_manual')
        
        # Get user's API keys
        api_keys = APIKey.objects.filter(api_user=api_user).order_by('-created_at')
        
        # Get user's accessible sites for display
        accessible_sites = api_user.get_user_accessible_sites()
        accessible_countries = api_user.get_user_accessible_countries()
        accessible_portfolios = api_user.get_user_accessible_portfolios()
        
        if use_react:
            # Render React version - pass data as JSON
            import json
            context = {
                'api_user': json.dumps({
                    'id': api_user.id,
                    'name': api_user.name,
                    'access_level': api_user.access_level,
                    'access_level_display': api_user.get_access_level_display(),
                    'status': api_user.status,
                    'rate_limit_per_minute': api_user.rate_limit_per_minute,
                    'rate_limit_per_hour': api_user.rate_limit_per_hour,
                    'rate_limit_per_day': api_user.rate_limit_per_day,
                }),
                'api_keys': json.dumps([{
                    'id': str(key.id),
                    'name': key.name,
                    'key_prefix': key.key_prefix,
                    'status': key.status,
                    'created_at': key.created_at.isoformat() if key.created_at else None,
                    'expires_at': key.expires_at.isoformat() if key.expires_at else None,
                } for key in api_keys]),
                'accessible_sites_count': accessible_sites.count() if accessible_sites else 0,
                'accessible_countries': json.dumps(list(accessible_countries) if accessible_countries else []),
                'accessible_portfolios': json.dumps(list(accessible_portfolios) if accessible_portfolios else []),
                'base_url': f"{request.scheme}://{request.get_host()}",
            }
            return render(request, 'api/api_manual_react.html', context)
        
        # Legacy template
        context = {
            'api_user': api_user,
            'api_keys': api_keys,
            'accessible_sites': accessible_sites,
            'accessible_countries': list(accessible_countries) if accessible_countries else [],
            'accessible_portfolios': list(accessible_portfolios) if accessible_portfolios else [],
        }
        
        return render(request, 'api/api_manual.html', context)
        
    except Exception as e:
        messages.error(request, f'Error loading API manual: {str(e)}')
        return redirect('accounts:login')


# =============================================================================
# Public Endpoints - No Authentication Required
# =============================================================================

@require_http_methods(["POST"])
def request_token(request):
    """
    Generate an active token from API key
    WITH BRUTE FORCE PROTECTION
    
    POST /api/v1/auth/token
    Body: {
        "api_key": "your-api-key",
        "lifetime_minutes": 60 (optional, default 60),
        "max_uses": 100 (optional, default 100)
    }
    
    Returns: {
        "token": "active-token-string",
        "expires_at": "2025-01-01T12:00:00Z",
        "lifetime_minutes": 60,
        "max_uses": 100
    }
    """
    client_ip = get_client_ip(request)
    user_agent = get_user_agent(request)
    
    try:
        # === STEP 1: Check if IP is blocked ===
        allowed, block_reason, retry_after = brute_force_protector.check_ip_allowed(client_ip)
        if not allowed:
            response = JsonResponse({
                'error': 'Access denied',
                'message': f'Your IP address has been temporarily blocked: {block_reason}',
                'code': 'IP_BLOCKED',
                'retry_after_seconds': retry_after
            }, status=403)
            
            if retry_after:
                response['Retry-After'] = str(retry_after)
            
            return response
        
        # === STEP 2: Check token request rate limit ===
        rate_allowed, retry_after = brute_force_protector.check_token_request_rate_limit(client_ip)
        if not rate_allowed:
            return JsonResponse({
                'error': 'Rate limit exceeded',
                'message': f'Too many token requests. Maximum {brute_force_protector.TOKEN_REQUEST_LIMIT} requests per minute.',
                'code': 'RATE_LIMIT_EXCEEDED',
                'retry_after_seconds': retry_after
            }, status=429)
        
        # === STEP 3: Parse request body ===
        try:
            data = json.loads(request.body.decode('utf-8'))
        except json.JSONDecodeError:
            return JsonResponse({
                'error': 'Invalid JSON',
                'message': 'Request body must be valid JSON.',
                'code': 'INVALID_JSON'
            }, status=400)
        
        api_key_string = data.get('api_key')
        
        if not api_key_string:
            return JsonResponse({
                'error': 'API key required',
                'message': 'Please provide your API key in the request body.',
                'code': 'API_KEY_REQUIRED'
            }, status=400)
        
        # === STEP 4: Apply progressive delay (exponential backoff) ===
        brute_force_protector.apply_progressive_delay(client_ip)
        
        # === STEP 5: Verify API key ===
        api_key = APIKey.verify_key(api_key_string)
        
        if not api_key:
            # 🚨 FAILED AUTHENTICATION - Record it!
            should_block, attempt_count, info = brute_force_protector.record_failed_attempt(
                ip_address=client_ip,
                attempted_key=api_key_string,
                failure_reason='invalid_key',
                user_agent=user_agent,
                endpoint='/api/v1/auth/token'
            )
            
            if should_block:
                # IP is now blocked
                return JsonResponse({
                    'error': 'Access denied',
                    'message': f'Your IP address has been blocked due to {attempt_count} failed authentication attempts. Please contact support.',
                    'code': 'IP_BLOCKED',
                    'retry_after_seconds': info
                }, status=403)
            else:
                # Not blocked yet, but warn
                return JsonResponse({
                    'error': 'Invalid API key',
                    'message': 'The provided API key is invalid or expired.',
                    'code': 'INVALID_API_KEY',
                    'warning': f'Failed attempts: {attempt_count}. You have {info} attempts remaining before your IP is blocked.'
                }, status=401)
        
        # === STEP 6: Check suspicious patterns ===
        is_suspicious, suspicion_reason = brute_force_protector.is_ip_suspicious(client_ip)
        if is_suspicious:
            # Auto-block suspicious IPs
            brute_force_protector.record_failed_attempt(
                ip_address=client_ip,
                attempted_key=api_key_string,
                failure_reason='suspicious_pattern',
                user_agent=user_agent
            )
        
        # === STEP 7: Validate parameters ===
        lifetime_minutes = int(data.get('lifetime_minutes', 60))
        max_uses = int(data.get('max_uses', 100))
        
        if lifetime_minutes < 1 or lifetime_minutes > 1440:  # Max 24 hours
            return JsonResponse({
                'error': 'Invalid lifetime',
                'message': 'Lifetime must be between 1 and 1440 minutes (24 hours).',
                'code': 'INVALID_LIFETIME'
            }, status=400)
        
        if max_uses < 1 or max_uses > 10000:
            return JsonResponse({
                'error': 'Invalid max_uses',
                'message': 'Max uses must be between 1 and 10000.',
                'code': 'INVALID_MAX_USES'
            }, status=400)
        
        # === STEP 8: Create active token ===
        active_token = ActiveToken.create_token(
            api_key=api_key,
            ip_address=client_ip,
            user_agent=user_agent,
            lifetime_minutes=lifetime_minutes,
            max_uses=max_uses
        )
        
        return JsonResponse({
            'success': True,
            'token': active_token.token,
            'expires_at': active_token.expires_at.isoformat(),
            'lifetime_minutes': lifetime_minutes,
            'max_uses': max_uses,
            'created_at': active_token.created_at.isoformat()
        })
        
    except Exception as e:
        return JsonResponse({
            'error': 'Internal error',
            'message': str(e),
            'code': 'INTERNAL_ERROR'
        }, status=500)


# =============================================================================
# Schema Discovery Endpoints - Require Authentication
# =============================================================================

@require_http_methods(["GET"])
@require_api_auth(use_active_token=False)
def list_tables(request):
    """
    Get list of available tables
    
    GET /api/v1/schema/tables
    
    Returns: {
        "tables": [
            {
                "name": "asset_list",
                "permissions": {
                    "can_read": true,
                    "can_filter": true,
                    "can_aggregate": true,
                    "max_records_per_request": 1000
                }
            },
            ...
        ]
    }
    """
    try:
        api_user = request.api_user
        
        # Get all table permissions for this user
        permissions = TablePermission.objects.filter(
            api_user=api_user
        ).select_related('api_user')
        
        tables = []
        for perm in permissions:
            tables.append({
                'name': perm.table_name,
                'permissions': {
                    'can_read': perm.can_read,
                    'can_filter': perm.can_filter,
                    'can_aggregate': perm.can_aggregate,
                    'max_records_per_request': perm.max_records_per_request
                }
            })
        
        return JsonResponse({
            'success': True,
            'tables': tables,
            'total_count': len(tables)
        })
        
    except Exception as e:
        return JsonResponse({
            'error': 'Failed to retrieve tables',
            'message': str(e),
            'code': 'TABLES_RETRIEVAL_ERROR'
        }, status=500)


@require_http_methods(["GET"])
@require_api_auth(use_active_token=False)
def get_table_schema(request, table_name):
    """
    Get schema information for a specific table
    
    GET /api/v1/schema/tables/<table_name>
    
    Returns: {
        "table_name": "asset_list",
        "columns": [
            {
                "name": "asset_code",
                "type": "CharField",
                "max_length": 255,
                "nullable": false,
                "primary_key": true,
                "is_restricted": false
            },
            ...
        ],
        "permissions": {...}
    }
    """
    try:
        api_user = request.api_user
        
        # Check if user has access to this table
        try:
            permission = TablePermission.objects.get(
                api_user=api_user,
                table_name=table_name
            )
        except TablePermission.DoesNotExist:
            return JsonResponse({
                'error': 'Table not found',
                'message': f'You do not have access to table: {table_name}',
                'code': 'TABLE_NOT_FOUND'
            }, status=404)
        
        # Get restricted columns
        restrictions = ColumnRestriction.objects.filter(
            table_permission=permission
        ).values_list('column_name', 'restriction_type') if permission else []
        restricted_columns = {col: rtype for col, rtype in restrictions}
        
        # Get model
        try:
            model = apps.get_model('main', table_name)
        except LookupError:
            return JsonResponse({
                'error': 'Table not found',
                'message': f'Table {table_name} does not exist in the database.',
                'code': 'TABLE_NOT_FOUND'
            }, status=404)
        
        # Get column information
        columns = []
        for field in model._meta.get_fields():
            if hasattr(field, 'column'):
                column_name = field.column if hasattr(field, 'column') else field.name
                
                column_info = {
                    'name': field.name,
                    'type': field.get_internal_type(),
                    'nullable': field.null if hasattr(field, 'null') else False,
                    'primary_key': field.primary_key if hasattr(field, 'primary_key') else False,
                    'is_restricted': field.name in restricted_columns
                }
                
                # Add type-specific info
                if hasattr(field, 'max_length') and field.max_length:
                    column_info['max_length'] = field.max_length
                
                if hasattr(field, 'choices') and field.choices:
                    column_info['choices'] = [choice[0] for choice in field.choices]
                
                if hasattr(field, 'help_text') and field.help_text:
                    column_info['description'] = field.help_text
                
                columns.append(column_info)
        
        return JsonResponse({
            'success': True,
            'table_name': table_name,
            'columns': columns,
            'total_columns': len(columns),
            'permissions': {
                'can_read': permission.can_read,
                'can_filter': permission.can_filter,
                'can_aggregate': permission.can_aggregate,
                'max_records_per_request': permission.max_records_per_request
            }
        })
        
    except Exception as e:
        return JsonResponse({
            'error': 'Failed to retrieve schema',
            'message': str(e),
            'code': 'SCHEMA_RETRIEVAL_ERROR'
        }, status=500)


# =============================================================================
# Data Access Endpoints - Require Authentication & Active Token
# =============================================================================

@require_http_methods(["GET"])
@require_api_auth(use_active_token=True)
def get_table_data(request, table_name):
    """
    Get data from a table with filtering and pagination
    
    GET /api/v1/data/<table_name>?filter=<json>&page=1&page_size=100
    
    Query Parameters:
    - filter: JSON object with filter conditions
    - page: Page number (default: 1)
    - page_size: Records per page (default: 100, max: table permission limit)
    - fields: Comma-separated list of fields to return (default: all allowed fields)
    - order_by: Field name to order by (prefix with - for descending)
    
    Returns: {
        "data": [...],
        "pagination": {
            "page": 1,
            "page_size": 100,
            "total_records": 1500,
            "total_pages": 15,
            "has_next": true,
            "has_previous": false
        }
    }
    """
    try:
        api_user = request.api_user
        
        # Get user's accessible sites using the same utility as main app
        from main.views.shared.utilities import get_user_accessible_sites
        
        # Create a mock request object for the utility function
        class MockRequest:
            def __init__(self, user):
                self.user = user
        
        mock_request = MockRequest(api_user.user)
        accessible_sites = get_user_accessible_sites(mock_request)
        
        # Check if user is admin (for filtering logic)
        is_admin = user_has_capability(api_user.user, 'data_api.view_all')
        
        # Check if user has access to this table
        # For admins with country-level access, bypass TablePermission check
        try:
            permission = TablePermission.objects.get(
                api_user=api_user,
                table_name=table_name
            )
            has_table_access = True
        except TablePermission.DoesNotExist:
            # If no explicit permission but user is admin or has accessible sites, grant read access
            if is_admin or (accessible_sites.exists()):
                has_table_access = True
                # Create a default permission object for the response
                permission = None
            else:
                has_table_access = False
        
        if not has_table_access:
            return JsonResponse({
                'error': 'Table not found',
                'message': f'You do not have access to table: {table_name}',
                'code': 'TABLE_NOT_FOUND'
            }, status=404)
        
        # Get model
        try:
            model = apps.get_model('main', table_name)
        except LookupError:
            return JsonResponse({
                'error': 'Table not found',
                'message': f'Table {table_name} does not exist in the database.',
                'code': 'TABLE_NOT_FOUND'
            }, status=404)
        
        # Get restricted columns
        restrictions = ColumnRestriction.objects.filter(
            table_permission=permission
        ).values_list('column_name', 'restriction_type') if permission else []
        restricted_columns = {col: rtype for col, rtype in restrictions}
        
        # Start with all objects
        queryset = model.objects.all()
        
        # Apply hierarchical access control based on user's accessible sites
        # Skip filtering for admin users (they get all data)
        if not is_admin:
            try:
                from main.views.shared.utilities import filter_data_by_user_sites
                if accessible_sites.exists():
                    # Filter data based on accessible sites
                    # Create a mock request object for the function
                    class MockRequest:
                        def __init__(self, user):
                            self.user = user
                    
                    mock_request = MockRequest(api_user.user)
                    # Determine the appropriate field name for filtering
                    asset_field_name = None
                    if hasattr(model, 'asset_code'):
                        asset_field_name = 'asset_code'
                    elif hasattr(model, 'assetno'):
                        asset_field_name = 'assetno'
                    elif hasattr(model, 'asset_no'):
                        asset_field_name = 'asset_no'
                    elif hasattr(model, 'asset_number'):
                        asset_field_name = 'asset_number'
                    
                    if asset_field_name:
                        queryset = filter_data_by_user_sites(queryset, asset_field_name, mock_request)
            except ImportError:
                # Fallback: if the access control function doesn't exist, 
                # we'll implement a basic filtering here
                if not is_admin:
                    accessible_sites = api_user.get_user_accessible_sites()
                    if accessible_sites.exists():
                        # Get accessible site codes
                        accessible_site_codes = list(accessible_sites.values_list('asset_code', flat=True))
                        accessible_asset_numbers = list(accessible_sites.values_list('asset_number', flat=True))
                        
                        # Apply filtering based on common field patterns
                        if hasattr(model, 'asset_code'):
                            queryset = queryset.filter(asset_code__in=accessible_site_codes)
                        elif hasattr(model, 'assetno'):
                            queryset = queryset.filter(assetno__in=accessible_site_codes)
                        elif hasattr(model, 'asset_no'):
                            queryset = queryset.filter(asset_no__in=accessible_site_codes)
                        elif hasattr(model, 'asset_number'):
                            queryset = queryset.filter(asset_number__in=accessible_asset_numbers)
        
        # Apply advanced filters if allowed and provided
        filter_param = request.GET.get('filter')
        if filter_param:
            if not permission.can_filter:
                return JsonResponse({
                    'error': 'Filtering not allowed',
                    'message': 'You do not have permission to filter this table.',
                    'code': 'FILTER_NOT_ALLOWED'
                }, status=403)
            
            try:
                from .filtering import apply_filters_to_queryset
                queryset = apply_filters_to_queryset(queryset, model, filter_param)
            except Exception as e:
                return JsonResponse({
                    'error': 'Filter error',
                    'message': str(e),
                    'code': 'FILTER_ERROR'
                }, status=400)
        
        # Apply ordering
        order_by = request.GET.get('order_by')
        if order_by:
            try:
                queryset = queryset.order_by(order_by)
            except Exception as e:
                return JsonResponse({
                    'error': 'Invalid order_by',
                    'message': str(e),
                    'code': 'INVALID_ORDER'
                }, status=400)
        
        # Get pagination parameters
        page = int(request.GET.get('page', 1))
        page_size = int(request.GET.get('page_size', 100))
        
        # Enforce max records per request
        if page_size > permission.max_records_per_request:
            page_size = permission.max_records_per_request
        
        # Paginate
        paginator = Paginator(queryset, page_size)
        
        if page > paginator.num_pages:
            page = paginator.num_pages if paginator.num_pages > 0 else 1
        
        page_obj = paginator.get_page(page)
        
        # Get requested fields
        fields_param = request.GET.get('fields')
        if fields_param:
            requested_fields = [f.strip() for f in fields_param.split(',')]
        else:
            requested_fields = [f.name for f in model._meta.get_fields() if hasattr(f, 'column')]
        
        # Build response data
        data = []
        for obj in page_obj:
            row = {}
            for field_name in requested_fields:
                # Skip restricted columns
                if field_name in restricted_columns:
                    if restricted_columns[field_name] == 'hidden':
                        continue
                    elif restricted_columns[field_name] == 'masked':
                        row[field_name] = None
                        continue
                
                try:
                    value = getattr(obj, field_name)
                    # Convert to JSON-serializable format
                    if hasattr(value, 'isoformat'):
                        value = value.isoformat()
                    row[field_name] = value
                except AttributeError:
                    pass
            
            data.append(row)
        
        # Attach records count for logging
        response = JsonResponse({
            'success': True,
            'data': data,
            'pagination': {
                'page': page,
                'page_size': page_size,
                'total_records': paginator.count,
                'total_pages': paginator.num_pages,
                'has_next': page_obj.has_next(),
                'has_previous': page_obj.has_previous()
            }
        })
        
        response.records_returned = len(data)
        return response
        
    except Exception as e:
        return JsonResponse({
            'error': 'Data retrieval error',
            'message': str(e),
            'code': 'DATA_RETRIEVAL_ERROR'
        }, status=500)


@require_http_methods(["GET"])
@require_api_auth(use_active_token=True)
def get_table_aggregate(request, table_name):
    """
    Get aggregate data from a table
    
    GET /api/v1/data/<table_name>/aggregate?operation=count&field=id&filter=<json>
    
    Query Parameters:
    - operation: count, sum, avg, min, max
    - field: Field to aggregate (not needed for count)
    - filter: JSON object with filter conditions
    
    Returns: {
        "result": 1500,
        "operation": "count",
        "field": "id"
    }
    """
    try:
        api_user = request.api_user
        
        # Get user's accessible sites using the same utility as main app
        from main.views.shared.utilities import get_user_accessible_sites
        
        # Create a mock request object for the utility function
        class MockRequest:
            def __init__(self, user):
                self.user = user
        
        mock_request = MockRequest(api_user.user)
        accessible_sites = get_user_accessible_sites(mock_request)
        
        # Check if user is admin (for filtering logic)
        is_admin = user_has_capability(api_user.user, 'data_api.view_all')
        
        # Check if user has access to this table
        # For admins with country-level access, bypass TablePermission check
        try:
            permission = TablePermission.objects.get(
                api_user=api_user,
                table_name=table_name
            )
            has_table_access = True
        except TablePermission.DoesNotExist:
            # If no explicit permission but user is admin or has accessible sites, grant read access
            if is_admin or (accessible_sites.exists()):
                has_table_access = True
                # Create a default permission object for the response
                permission = None
            else:
                has_table_access = False
        
        if not has_table_access:
            return JsonResponse({
                'error': 'Table not found',
                'message': f'You do not have access to table: {table_name}',
                'code': 'TABLE_NOT_FOUND'
            }, status=404)
        
        # Get model
        try:
            model = apps.get_model('main', table_name)
        except LookupError:
            return JsonResponse({
                'error': 'Table not found',
                'message': f'Table {table_name} does not exist.',
                'code': 'TABLE_NOT_FOUND'
            }, status=404)
        
        # Get operation and field
        operation = request.GET.get('operation', 'count').lower()
        field = request.GET.get('field')
        
        if operation not in ['count', 'sum', 'avg', 'min', 'max']:
            return JsonResponse({
                'error': 'Invalid operation',
                'message': 'Operation must be one of: count, sum, avg, min, max',
                'code': 'INVALID_OPERATION'
            }, status=400)
        
        # Start with all objects
        queryset = model.objects.all()
        
        # Apply hierarchical access control based on user's accessible sites
        # Skip filtering for admin users (they get all data)
        if not is_admin:
            try:
                from main.views.shared.utilities import filter_data_by_user_sites
                if accessible_sites.exists():
                    # Filter data based on accessible sites
                    # Create a mock request object for the function
                    class MockRequest:
                        def __init__(self, user):
                            self.user = user
                    
                    mock_request = MockRequest(api_user.user)
                    # Determine the appropriate field name for filtering
                    asset_field_name = None
                    if hasattr(model, 'asset_code'):
                        asset_field_name = 'asset_code'
                    elif hasattr(model, 'assetno'):
                        asset_field_name = 'assetno'
                    elif hasattr(model, 'asset_no'):
                        asset_field_name = 'asset_no'
                    elif hasattr(model, 'asset_number'):
                        asset_field_name = 'asset_number'
                    
                    if asset_field_name:
                        queryset = filter_data_by_user_sites(queryset, asset_field_name, mock_request)
            except ImportError:
                # Fallback: if the access control function doesn't exist, 
                # we'll implement a basic filtering here
                if not is_admin:
                    accessible_sites = api_user.get_user_accessible_sites()
                    if accessible_sites.exists():
                        # Get accessible site codes
                        accessible_site_codes = list(accessible_sites.values_list('asset_code', flat=True))
                        accessible_asset_numbers = list(accessible_sites.values_list('asset_number', flat=True))
                        
                        # Apply filtering based on common field patterns
                        if hasattr(model, 'asset_code'):
                            queryset = queryset.filter(asset_code__in=accessible_site_codes)
                        elif hasattr(model, 'assetno'):
                            queryset = queryset.filter(assetno__in=accessible_site_codes)
                        elif hasattr(model, 'asset_no'):
                            queryset = queryset.filter(asset_no__in=accessible_site_codes)
                        elif hasattr(model, 'asset_number'):
                            queryset = queryset.filter(asset_number__in=accessible_asset_numbers)
        
        # Apply advanced filters
        filter_param = request.GET.get('filter')
        if filter_param:
            try:
                from .filtering import apply_filters_to_queryset
                queryset = apply_filters_to_queryset(queryset, model, filter_param)
            except Exception as e:
                return JsonResponse({
                    'error': 'Filter error',
                    'message': str(e),
                    'code': 'FILTER_ERROR'
                }, status=400)
        
        # Perform aggregation
        from django.db.models import Count, Sum, Avg, Min, Max
        
        if operation == 'count':
            result = queryset.count()
        else:
            if not field:
                return JsonResponse({
                    'error': 'Field required',
                    'message': f'Field parameter is required for {operation} operation.',
                    'code': 'FIELD_REQUIRED'
                }, status=400)
            
            agg_func = {
                'sum': Sum,
                'avg': Avg,
                'min': Min,
                'max': Max
            }[operation]
            
            result = queryset.aggregate(result=agg_func(field))['result']
        
        return JsonResponse({
            'success': True,
            'result': result,
            'operation': operation,
            'field': field if field else None
        })
        
    except Exception as e:
        return JsonResponse({
            'error': 'Aggregation error',
            'message': str(e),
            'code': 'AGGREGATION_ERROR'
        }, status=500)


# =============================================================================
# API Key Management Endpoints - Require Django Authentication
# =============================================================================

@login_required
@require_http_methods(["GET"])
def api_dashboard(request):
    """
    API management dashboard
    Shows user's API keys and usage statistics
    RESTRICTED: Only users with API access (api_only or both) can view
    """
    from django.shortcuts import render
    
    # Check if user has API access
    try:
        api_user = APIUser.objects.get(user=request.user)
        if not api_user.has_api_access():
            messages.error(request, 'You do not have API access. Please contact an administrator.')
            return redirect('main:unified_dashboard')
    except APIUser.DoesNotExist:
        messages.error(request, 'You do not have API access. Please contact an administrator.')
        return redirect('main:unified_dashboard')
    
    # Check if React version is enabled via waffle flag
    from waffle import flag_is_active
    use_react = flag_is_active(request, 'react_api_dashboard')
    
    # Get API keys
    api_keys = APIKey.objects.filter(api_user=api_user).order_by('-created_at')
    
    # Get table permissions
    table_permissions = TablePermission.objects.filter(api_user=api_user).order_by('table_name')
    
    # Check if user is admin (can generate keys for others)
    is_admin_user = request.user.is_superuser or user_has_capability(request.user, 'api.manage')
    
    if use_react:
        # Render React version - pass data as JSON
        import json
        context = {
            'api_user': json.dumps({
                'id': api_user.id,
                'name': api_user.name,
                'access_level': api_user.access_level,
                'status': api_user.status,
                'rate_limit_per_minute': api_user.rate_limit_per_minute,
                'rate_limit_per_hour': api_user.rate_limit_per_hour,
                'rate_limit_per_day': api_user.rate_limit_per_day,
                'total_requests': api_user.total_requests,
                'last_request_at': api_user.last_request_at.isoformat() if api_user.last_request_at else None,
            }),
            'api_keys': json.dumps([{
                'id': str(key.id),
                'name': key.name,
                'key_prefix': key.key_prefix,
                'status': key.status,
                'created_at': key.created_at.isoformat() if key.created_at else None,
                'expires_at': key.expires_at.isoformat() if key.expires_at else None,
                'last_used_at': key.last_used_at.isoformat() if key.last_used_at else None,
                'total_requests': key.total_requests,
            } for key in api_keys]),
            'table_permissions': json.dumps([{
                'id': perm.id,
                'table_name': perm.table_name,
                'can_read': perm.can_read,
                'can_filter': perm.can_filter,
                'can_aggregate': perm.can_aggregate,
                'max_records_per_request': perm.max_records_per_request,
            } for perm in table_permissions]),
            'is_admin_user': json.dumps(is_admin_user),
        }
        return render(request, 'api/dashboard_react.html', context)
    
    # Legacy template
    context = {
        'api_user': api_user,
        'api_keys': api_keys,
        'table_permissions': table_permissions,
        'is_admin_user': is_admin_user
    }
    
    return render(request, 'api/dashboard.html', context)


@login_required
@require_http_methods(["POST"])
def generate_api_key(request):
    """
    Generate a new API key for the authenticated user
    ALLOWED: Only for admin users (superuser or admin role)
    Regular users must use /api/admin/generate-key/ via admin interface
    """
    # Check if user is admin
    is_admin_user = request.user.is_superuser or user_has_capability(request.user, 'api.manage')
    
    if not is_admin_user:
        return JsonResponse({
            'error': 'Access denied',
            'message': 'Only administrators can generate API keys. Please contact an administrator to request API access.',
            'code': 'SELF_KEY_GENERATION_DISABLED'
        }, status=403)
    
    try:
        # Get or create APIUser for the admin
        try:
            api_user = APIUser.objects.get(user=request.user)
        except APIUser.DoesNotExist:
            # Create APIUser for admin if it doesn't exist
            api_user = APIUser.objects.create(
                user=request.user,
                name=request.user.get_full_name() or request.user.username,
                description='Auto-created for admin user',
                access_level='both',
                status='active'
            )
        
        # Parse request data
        name = request.POST.get('name', 'Admin Generated Key')
        description = request.POST.get('description', '')
        expires_at = request.POST.get('expires_at')
        
        # Create API key
        api_key = APIKey.objects.create(
            api_user=api_user,
            name=name,
            description=description,
            expires_at=expires_at if expires_at else None
        )
        
        return JsonResponse({
            'success': True,
            'message': 'API key generated successfully',
            'key': api_key.key,  # Return the actual key
            'key_id': str(api_key.id),
            'expires_at': api_key.expires_at.isoformat() if api_key.expires_at else None
        })
        
    except Exception as e:
        return JsonResponse({
            'error': 'Key generation failed',
            'message': str(e),
            'code': 'KEY_GENERATION_ERROR'
        }, status=500)


@login_required
@require_http_methods(["POST"])
def revoke_api_key(request, key_id):
    """
    Revoke an API key
    DISABLED: Users cannot revoke their own keys
    Only admins can revoke keys via /api/admin/revoke-key/<uuid>/
    """
    return JsonResponse({
        'error': 'Access denied',
        'message': 'Users cannot revoke their own API keys. Please contact an administrator.',
        'code': 'SELF_KEY_REVOCATION_DISABLED'
    }, status=403)


# =============================================================================
# Web API Endpoints for React Frontend
# =============================================================================

@login_required
@require_http_methods(["GET"])
def api_user_info(request):
    """
    Get current user's API information for React frontend
    GET /api/web/user-info/
    """
    try:
        from .models import APIUser, APIKey
        from main.decorators.cors_decorator import cors_allow_same_site
        
        try:
            api_user = APIUser.objects.get(user=request.user)
        except APIUser.DoesNotExist:
            return JsonResponse({
                'success': False,
                'error': 'You do not have API access. Please contact an administrator.'
            }, status=403)
        
        if not api_user.has_api_access():
            return JsonResponse({
                'success': False,
                'error': 'You do not have API access. Please contact an administrator.'
            }, status=403)
        
        # Get accessible sites info
        accessible_sites = api_user.get_user_accessible_sites()
        accessible_countries = api_user.get_user_accessible_countries()
        accessible_portfolios = api_user.get_user_accessible_portfolios()
        
        return JsonResponse({
            'success': True,
            'data': {
                'api_user': {
                    'id': api_user.id,
                    'name': api_user.name,
                    'access_level': api_user.access_level,
                    'access_level_display': api_user.get_access_level_display(),
                    'status': api_user.status,
                    'rate_limit_per_minute': api_user.rate_limit_per_minute,
                    'rate_limit_per_hour': api_user.rate_limit_per_hour,
                    'rate_limit_per_day': api_user.rate_limit_per_day,
                },
                'accessible_sites_count': accessible_sites.count() if accessible_sites else 0,
                'accessible_countries': list(accessible_countries) if accessible_countries else [],
                'accessible_portfolios': list(accessible_portfolios) if accessible_portfolios else [],
                'base_url': f"{request.scheme}://{request.get_host()}",
            }
        })
    except Exception as e:
        logger.error(f"Error in api_user_info: {str(e)}")
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@login_required
@require_http_methods(["GET"])
def list_api_keys(request):
    """
    List current user's API keys for React frontend
    GET /api/web/keys/
    """
    try:
        from .models import APIUser, APIKey
        
        try:
            api_user = APIUser.objects.get(user=request.user)
        except APIUser.DoesNotExist:
            return JsonResponse({
                'success': False,
                'error': 'You do not have API access.'
            }, status=403)
        
        api_keys = APIKey.objects.filter(api_user=api_user).order_by('-created_at')
        
        keys_data = [{
            'id': str(key.id),
            'name': key.name,
            'key_prefix': key.key_prefix,
            'status': key.status,
            'created_at': key.created_at.isoformat() if key.created_at else None,
            'expires_at': key.expires_at.isoformat() if key.expires_at else None,
            'last_used_at': key.last_used_at.isoformat() if key.last_used_at else None,
            'total_requests': key.total_requests,
        } for key in api_keys]
        
        return JsonResponse({
            'success': True,
            'data': keys_data,
            'count': len(keys_data)
        })
    except Exception as e:
        logger.error(f"Error in list_api_keys: {str(e)}")
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)
