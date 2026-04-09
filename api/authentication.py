"""
API Authentication & Authorization
-----------------------------------
Secure authentication system with:
- API Key validation
- Active Token management
- Rate limiting
- IP restrictions
- Request logging
"""

from django.http import JsonResponse
from django.utils import timezone
from functools import wraps
import time
from datetime import datetime, timedelta
from .models import APIKey, ActiveToken, APIRequestLog, RateLimitTracker
import logging

logger = logging.getLogger(__name__)


class APIAuthenticationError(Exception):
    """Custom exception for API authentication errors"""
    pass


class APIRateLimitError(Exception):
    """Custom exception for rate limit violations"""
    pass


def get_client_ip(request):
    """Extract client IP address from request"""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip


def get_user_agent(request):
    """Extract user agent from request"""
    return request.META.get('HTTP_USER_AGENT', '')


def extract_api_credentials(request):
    """
    Extract API credentials from request
    Supports multiple authentication methods:
    1. Authorization header: Bearer <api_key>
    2. X-API-Key header: <api_key>
    3. Query parameter: ?api_key=<api_key>
    """
    # Method 1: Authorization header
    auth_header = request.META.get('HTTP_AUTHORIZATION', '')
    if auth_header.startswith('Bearer '):
        return auth_header[7:]
    
    # Method 2: X-API-Key header
    api_key = request.META.get('HTTP_X_API_KEY', '')
    if api_key:
        return api_key
    
    # Method 3: Query parameter
    api_key = request.GET.get('api_key', '')
    if api_key:
        return api_key
    
    return None


def extract_active_token(request):
    """
    Extract active token from request
    Token should be in X-API-Token header
    """
    return request.META.get('HTTP_X_API_TOKEN', '')


def check_rate_limit(api_key):
    """
    Check if API key has exceeded rate limits
    Returns (allowed: bool, limit_type: str, retry_after: int)
    """
    now = timezone.now()
    api_user = api_key.api_user
    
    # Check minute limit
    minute_start = now.replace(second=0, microsecond=0)
    minute_tracker, _ = RateLimitTracker.objects.get_or_create(
        api_key=api_key,
        period='minute',
        period_start=minute_start,
        defaults={'request_count': 0}
    )
    
    if minute_tracker.request_count >= api_user.rate_limit_per_minute:
        retry_after = 60 - now.second
        return False, 'minute', retry_after
    
    # Check hour limit
    hour_start = now.replace(minute=0, second=0, microsecond=0)
    hour_tracker, _ = RateLimitTracker.objects.get_or_create(
        api_key=api_key,
        period='hour',
        period_start=hour_start,
        defaults={'request_count': 0}
    )
    
    if hour_tracker.request_count >= api_user.rate_limit_per_hour:
        retry_after = (60 - now.minute) * 60 - now.second
        return False, 'hour', retry_after
    
    # Check day limit
    day_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    day_tracker, _ = RateLimitTracker.objects.get_or_create(
        api_key=api_key,
        period='day',
        period_start=day_start,
        defaults={'request_count': 0}
    )
    
    if day_tracker.request_count >= api_user.rate_limit_per_day:
        tomorrow = day_start + timedelta(days=1)
        retry_after = int((tomorrow - now).total_seconds())
        return False, 'day', retry_after
    
    # Increment all trackers
    minute_tracker.request_count += 1
    minute_tracker.save()
    hour_tracker.request_count += 1
    hour_tracker.save()
    day_tracker.request_count += 1
    day_tracker.save()
    
    return True, None, 0


def log_api_request(request, api_key, active_token, status_code, response_time_ms, 
                   records_returned=0, error_message='', is_suspicious=False):
    """
    Log API request for analytics and security
    """
    try:
        query_params = dict(request.GET.items())
        # Remove sensitive data from logs
        query_params.pop('api_key', None)
        
        request_body = {}
        if request.method in ['POST', 'PUT', 'PATCH']:
            try:
                import json
                request_body = json.loads(request.body.decode('utf-8')) if request.body else {}
            except:
                request_body = {'_raw': str(request.body)}
        
        APIRequestLog.objects.create(
            api_key=api_key,
            active_token=active_token,
            endpoint=request.path,
            method=request.method,
            ip_address=get_client_ip(request),
            user_agent=get_user_agent(request),
            query_params=query_params,
            request_body=request_body,
            status_code=status_code,
            response_time_ms=response_time_ms,
            records_returned=records_returned,
            error_message=error_message,
            is_suspicious=is_suspicious
        )
    except Exception as e:
        logger.error(f"Failed to log API request: {e}")


def require_api_auth(use_active_token=False):
    """
    Decorator for API endpoints that require authentication
    
    Args:
        use_active_token: If True, require active token in addition to API key
    """
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            start_time = time.time()
            api_key = None
            active_token = None
            
            try:
                # Step 1: Extract and verify API key
                api_key_string = extract_api_credentials(request)
                if not api_key_string:
                    response = JsonResponse({
                        'error': 'Authentication required',
                        'message': 'API key not provided. Include your API key in Authorization header, X-API-Key header, or api_key query parameter.',
                        'code': 'AUTH_REQUIRED'
                    }, status=401)
                    return response
                
                # Verify API key
                api_key = APIKey.verify_key(api_key_string)
                if not api_key:
                    response = JsonResponse({
                        'error': 'Invalid API key',
                        'message': 'The provided API key is invalid, expired, or has been revoked.',
                        'code': 'INVALID_API_KEY'
                    }, status=401)
                    return response
                
                # Step 2: Check IP restrictions
                client_ip = get_client_ip(request)
                if not api_key.api_user.check_ip_allowed(client_ip):
                    log_api_request(request, api_key, None, 403, 
                                  (time.time() - start_time) * 1000,
                                  error_message=f'IP not allowed: {client_ip}',
                                  is_suspicious=True)
                    response = JsonResponse({
                        'error': 'Access denied',
                        'message': f'Your IP address ({client_ip}) is not authorized to use this API key.',
                        'code': 'IP_NOT_ALLOWED'
                    }, status=403)
                    return response
                
                # Step 3: Verify active token if required
                if use_active_token:
                    token_string = extract_active_token(request)
                    if not token_string:
                        response = JsonResponse({
                            'error': 'Active token required',
                            'message': 'This endpoint requires an active token. Include it in X-API-Token header.',
                            'code': 'TOKEN_REQUIRED'
                        }, status=401)
                        return response
                    
                    active_token = ActiveToken.verify_token(token_string)
                    if not active_token:
                        response = JsonResponse({
                            'error': 'Invalid active token',
                            'message': 'The provided active token is invalid, expired, or revoked.',
                            'code': 'INVALID_TOKEN'
                        }, status=401)
                        return response
                    
                    # Verify token belongs to this API key
                    if active_token.api_key.id != api_key.id:
                        response = JsonResponse({
                            'error': 'Token mismatch',
                            'message': 'The active token does not match the provided API key.',
                            'code': 'TOKEN_MISMATCH'
                        }, status=401)
                        return response
                    
                    # Update token usage
                    active_token.request_count += 1
                    active_token.last_used_at = timezone.now()
                    active_token.save()
                
                # Step 4: Check rate limits
                allowed, limit_type, retry_after = check_rate_limit(api_key)
                if not allowed:
                    log_api_request(request, api_key, active_token, 429,
                                  (time.time() - start_time) * 1000,
                                  error_message=f'Rate limit exceeded: {limit_type}')
                    response = JsonResponse({
                        'error': 'Rate limit exceeded',
                        'message': f'You have exceeded the {limit_type}ly rate limit. Please try again later.',
                        'limit_type': limit_type,
                        'retry_after_seconds': retry_after,
                        'code': 'RATE_LIMIT_EXCEEDED'
                    }, status=429)
                    response['Retry-After'] = str(retry_after)
                    return response
                
                # Step 5: Update usage statistics
                api_key.last_used_at = timezone.now()
                api_key.total_requests += 1
                api_key.save(update_fields=['last_used_at', 'total_requests'])
                
                api_key.api_user.last_request_at = timezone.now()
                api_key.api_user.total_requests += 1
                api_key.api_user.save(update_fields=['last_request_at', 'total_requests'])
                
                # Step 6: Check app access (ensure user has API app access)
                # This enforces app-level restrictions even for API users
                try:
                    from main.permissions import user_has_app_access
                    if not user_has_app_access(api_key.api_user.user, 'api'):
                        log_api_request(request, api_key, active_token, 403,
                                      (time.time() - start_time) * 1000,
                                      error_message='API app access denied')
                        response = JsonResponse({
                            'error': 'Access denied',
                            'message': 'You do not have access to the API application. Please contact an administrator.',
                            'code': 'APP_ACCESS_DENIED'
                        }, status=403)
                        return response
                except Exception as e:
                    # If app access check fails, log but don't block (for backward compatibility)
                    logger.warning(f"App access check failed: {e}")
                
                # Step 7: Attach authentication info to request
                request.api_key = api_key
                request.api_user = api_key.api_user
                request.active_token = active_token
                
                # Step 8: Call the actual view
                response = view_func(request, *args, **kwargs)
                
                # Step 9: Log successful request
                response_time_ms = (time.time() - start_time) * 1000
                records_returned = getattr(response, 'records_returned', 0)
                log_api_request(request, api_key, active_token, response.status_code,
                              response_time_ms, records_returned)
                
                # Add rate limit headers to response
                response['X-RateLimit-Limit-Minute'] = str(api_key.api_user.rate_limit_per_minute)
                response['X-RateLimit-Limit-Hour'] = str(api_key.api_user.rate_limit_per_hour)
                response['X-RateLimit-Limit-Day'] = str(api_key.api_user.rate_limit_per_day)
                
                return response
                
            except Exception as e:
                logger.exception(f"API authentication error: {e}")
                response_time_ms = (time.time() - start_time) * 1000
                if api_key:
                    log_api_request(request, api_key, active_token, 500,
                                  response_time_ms, error_message=str(e))
                
                response = JsonResponse({
                    'error': 'Internal server error',
                    'message': 'An unexpected error occurred while processing your request.',
                    'code': 'INTERNAL_ERROR'
                }, status=500)
                return response
        
        return wrapper
    return decorator


def require_table_permission(table_name, require_write=False):
    """
    Decorator to check table-level permissions
    """
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            # Check if user has permission for this table
            api_user = request.api_user
            
            try:
                permission = api_user.table_permissions.get(table_name=table_name)
                
                if not permission.can_read:
                    return JsonResponse({
                        'error': 'Permission denied',
                        'message': f'You do not have read access to table: {table_name}',
                        'code': 'TABLE_ACCESS_DENIED'
                    }, status=403)
                
                # Attach permission to request for use in view
                request.table_permission = permission
                
                return view_func(request, *args, **kwargs)
                
            except Exception as e:
                return JsonResponse({
                    'error': 'Permission denied',
                    'message': f'You do not have access to table: {table_name}',
                    'code': 'TABLE_ACCESS_DENIED'
                }, status=403)
        
        return wrapper
    return decorator

