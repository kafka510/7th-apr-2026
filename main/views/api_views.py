"""
API views for IP and User blocking management
"""

from django.http import JsonResponse
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.decorators.http import require_http_methods
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.utils import timezone
from django.db import transaction
from django.core.exceptions import ValidationError
from django.conf import settings
import json
import logging
import traceback

from accounts.decorators import role_required, role_required_api
from main.models import BlockedIP, BlockedUser, IPBlockingLog, UserBlockingLog
from main.middleware.realtime_ip_blocker import realtime_blocker

logger = logging.getLogger(__name__)
DEBUG = getattr(settings, 'DEBUG', False)


@ensure_csrf_cookie
@login_required
@role_required_api(allowed_roles=['admin'])
@require_http_methods(["GET"])
def blocking_stats_api(request):
    """Get blocking statistics"""
    try:
        stats = realtime_blocker.get_blocking_stats()
        
        # Add additional database stats
        active_ips = BlockedIP.objects.filter(status='active').count()
        active_users = BlockedUser.objects.filter(status='active').count()
        
        # Recent activity (last 24 hours)
        since = timezone.now() - timezone.timedelta(hours=24)
        recent_ip_blocks = IPBlockingLog.objects.filter(blocked_at__gte=since).count()
        recent_user_blocks = UserBlockingLog.objects.filter(blocked_at__gte=since).count()
        
        return JsonResponse({
            'success': True,
            'data': {
                'active_blocked_ips': active_ips,
                'active_blocked_users': active_users,
                'recent_ip_blocks_24h': recent_ip_blocks,
                'recent_user_blocks_24h': recent_user_blocks,
                'tracked_ips': stats.get('tracked_ips', 0),
                'company_ips_protected': stats.get('company_ips_protected', 0),
            }
        })
    except Exception as e:
        logger.error(f"Error getting blocking stats: {str(e)}")
        return JsonResponse({
            'success': False,
            'error': 'Failed to get blocking statistics'
        }, status=500)


@ensure_csrf_cookie
@login_required
@role_required_api(allowed_roles=['admin'])
@require_http_methods(["GET"])
def blocked_ips_api(request):
    """Get list of blocked IPs"""
    try:
        page = int(request.GET.get('page', 1))
        per_page_param = request.GET.get('per_page', '100')
        # Allow 'all' to fetch all IPs, or a number
        if per_page_param.lower() == 'all':
            per_page = None  # No pagination
        else:
            per_page = int(per_page_param)
        status = request.GET.get('status', 'active')
        
        # Filter blocked IPs
        queryset = BlockedIP.objects.all()
        total_count_all = queryset.count()
        if status != 'all':
            queryset = queryset.filter(status=status)
        
        total_count = queryset.count()
        
        # Pagination
        if per_page is None:
            # Return all IPs
            blocked_ips = queryset.order_by('-created_at')
            total_pages = 1
        else:
            start = (page - 1) * per_page
            end = start + per_page
            blocked_ips = queryset.order_by('-created_at')[start:end]
            total_pages = (total_count + per_page - 1) // per_page
        
        data = []
        for blocked_ip in blocked_ips:
            data.append({
                'id': blocked_ip.id,
                'ip_address': blocked_ip.ip_address,
                'reason': blocked_ip.reason,
                'description': blocked_ip.description,
                'status': blocked_ip.status,
                'priority': blocked_ip.priority,
                'created_at': blocked_ip.created_at.isoformat(),
                'expires_at': blocked_ip.expires_at.isoformat() if blocked_ip.expires_at else None,
                'block_count': blocked_ip.block_count,
                'last_seen': blocked_ip.last_seen.isoformat() if blocked_ip.last_seen else None,
                'is_active': blocked_ip.is_active,
                'is_expired': blocked_ip.is_expired,
            })
        
        return JsonResponse({
            'success': True,
            'data': data,
            'pagination': {
                'page': page,
                'per_page': per_page if per_page else total_count,
                'total_count': total_count,
                'total_count_all': total_count_all,
                'total_pages': total_pages,
            }
        })
    except Exception as e:
        logger.error(f"Error getting blocked IPs: {str(e)}")
        return JsonResponse({
            'success': False,
            'error': 'Failed to get blocked IPs'
        }, status=500)


@ensure_csrf_cookie
@login_required
@role_required_api(allowed_roles=['admin'])
@require_http_methods(["GET"])
def blocked_users_api(request):
    """
    Get list of blocked/inactive users
    
    Two tables involved:
    1. User table (auth_user) - has is_active field (True/False) - determines if user can log in
    2. BlockedUser table (blocked_user) - has status field ('active'/'inactive') - tracks blocking history
    
    Filter logic:
    - "Active Blocks": Show BlockedUser records with status='active' where user.is_active=False
    - "Inactive": Show ALL inactive users (user.is_active=False), including those without BlockedUser records
    - "All": Show all BlockedUser records where user.is_active=False
    """
    try:
        page = int(request.GET.get('page', 1))
        per_page = int(request.GET.get('per_page', 20))
        status = request.GET.get('status', 'active')
        
        # Handle "Inactive" status differently - show ALL inactive users, not just BlockedUser records
        if status == 'inactive':
            # Show ONLY truly inactive users (user.is_active=False) - these are users who need to be reactivated
            # Include inactive users with or without BlockedUser records
            from django.contrib.auth.models import User
            inactive_users = User.objects.filter(is_active=False)
            
            # Get BlockedUser records for inactive users only
            inactive_user_ids = set(inactive_users.values_list('id', flat=True))
            blocked_user_records = {bu.user_id: bu for bu in BlockedUser.objects.filter(user_id__in=inactive_user_ids)}
            
            data_list = []
            
            # Create data list from inactive users (user.is_active=False)
            for user in inactive_users:
                blocked_user = blocked_user_records.get(user.id)
                
                if blocked_user:
                    # User has BlockedUser record
                    data_list.append({
                        'id': blocked_user.id,
                        'username': user.username,
                        'email': user.email,
                        'reason': blocked_user.reason,
                        'description': blocked_user.description,
                        'status': blocked_user.status,
                        'priority': blocked_user.priority,
                        'created_at': blocked_user.created_at.isoformat(),
                        'expires_at': blocked_user.expires_at.isoformat() if blocked_user.expires_at else None,
                        'block_count': blocked_user.block_count,
                        'last_seen': blocked_user.last_seen.isoformat() if blocked_user.last_seen else None,
                        'is_active': blocked_user.is_active,
                        'is_expired': blocked_user.is_expired,
                        'user_is_active': user.is_active,
                    })
                else:
                    # User is inactive but doesn't have BlockedUser record
                    data_list.append({
                        'id': None,
                        'username': user.username,
                        'email': user.email,
                        'reason': 'User account is inactive',
                        'description': 'User account has been deactivated',
                        'status': 'inactive',
                        'priority': 'medium',
                        'created_at': user.date_joined.isoformat() if user.date_joined else None,
                        'expires_at': None,
                        'block_count': 0,
                        'last_seen': None,
                        'is_active': False,
                        'is_expired': False,
                        'user_is_active': user.is_active,
                    })
            
            # Sort by created_at descending
            data_list.sort(key=lambda x: x['created_at'] or '', reverse=True)
            
            # Pagination
            total_count = len(data_list)
            start = (page - 1) * per_page
            end = start + per_page
            paginated_data = data_list[start:end]
            
            return JsonResponse({
                'success': True,
                'data': paginated_data,
                'pagination': {
                    'page': page,
                    'per_page': per_page,
                    'total_count': total_count,
                    'total_pages': (total_count + per_page - 1) // per_page,
                }
            })
        
        # For "active" and "all" status, use BlockedUser table
        queryset = BlockedUser.objects.all()
        if status != 'all':
            queryset = queryset.filter(status=status)
        
        # Always filter out reactivated users (user.is_active=True) from the blocked users list
        # Reactivated users shouldn't appear because they can log in
        # Only show users who are currently inactive (user.is_active=False)
        queryset = queryset.filter(user__is_active=False)
        
        # Pagination
        start = (page - 1) * per_page
        end = start + per_page
        
        blocked_users = queryset.order_by('-created_at')[start:end]
        total_count = queryset.count()
        
        data = []
        for blocked_user in blocked_users:
            data.append({
                'id': blocked_user.id,
                'username': blocked_user.user.username,
                'email': blocked_user.user.email,
                'reason': blocked_user.reason,
                'description': blocked_user.description,
                'status': blocked_user.status,
                'priority': blocked_user.priority,
                'created_at': blocked_user.created_at.isoformat(),
                'expires_at': blocked_user.expires_at.isoformat() if blocked_user.expires_at else None,
                'block_count': blocked_user.block_count,
                'last_seen': blocked_user.last_seen.isoformat() if blocked_user.last_seen else None,
                'is_active': blocked_user.is_active,
                'is_expired': blocked_user.is_expired,
                'user_is_active': blocked_user.user.is_active,  # Add user's actual is_active status
            })
        
        return JsonResponse({
            'success': True,
            'data': data,
            'pagination': {
                'page': page,
                'per_page': per_page,
                'total_count': total_count,
                'total_pages': (total_count + per_page - 1) // per_page,
            }
        })
    except Exception as e:
        logger.error(f"Error getting blocked users: {str(e)}")
        return JsonResponse({
            'success': False,
            'error': 'Failed to get blocked users'
        }, status=500)


@login_required
@role_required_api(allowed_roles=['admin'])
@require_http_methods(["POST"])
def block_ip_api(request):
    """Block an IP address"""
    try:
        data = json.loads(request.body)
        
        ip_address = data.get('ip_address')
        reason = data.get('reason', 'Manual block via API')
        description = data.get('description', '')
        priority = data.get('priority', 'medium')
        expires_hours = data.get('expires_hours')
        
        if not ip_address:
            return JsonResponse({
                'success': False,
                'error': 'IP address is required'
            }, status=400)
        
        # Validate IP address format
        import ipaddress
        try:
            ipaddress.ip_address(ip_address)
        except ValueError:
            return JsonResponse({
                'success': False,
                'error': f'Invalid IP address format: {ip_address}'
            }, status=400)
        
        # Validate priority
        if priority not in ['low', 'medium', 'high', 'critical']:
            return JsonResponse({
                'success': False,
                'error': 'Invalid priority level'
            }, status=400)
        
        # Calculate expiration time
        expires_at = None
        if expires_hours:
            expires_at = timezone.now() + timezone.timedelta(hours=expires_hours)
        
        with transaction.atomic():
            # Create or update BlockedIP record
            blocked_ip, created = BlockedIP.objects.get_or_create(
                ip_address=ip_address,
                defaults={
                    'reason': reason,
                    'description': description,
                    'priority': priority,
                    'status': 'active',
                    'blocked_by': request.user,
                    'expires_at': expires_at,
                    'last_seen': timezone.now(),
                }
            )
            
            if not created:
                # Update existing record
                blocked_ip.reason = reason
                blocked_ip.description = description
                blocked_ip.priority = priority
                blocked_ip.status = 'active'
                blocked_ip.blocked_by = request.user
                blocked_ip.expires_at = expires_at
                blocked_ip.block_count += 1
                blocked_ip.last_seen = timezone.now()
                blocked_ip.save()
            
            # Create IPBlockingLog entry
            IPBlockingLog.objects.create(
                ip_address=ip_address,
                block_type='manual',
                block_reason='other',
                reason_details=reason,
                blocked_by=request.user,
                expires_at=expires_at,
                metadata={
                    'api_request': True,
                    'priority': priority,
                    'description': description
                }
            )
            
            # Invalidate cache to force reload
            realtime_blocker._invalidate_cache()
        
        return JsonResponse({
            'success': True,
            'message': f'Successfully blocked IP {ip_address}',
            'data': {
                'ip_address': ip_address,
                'reason': reason,
                'priority': priority,
                'created': created,
                'expires_at': expires_at.isoformat() if expires_at else None,
            }
        })
        
    except json.JSONDecodeError:
        return JsonResponse({
            'success': False,
            'error': 'Invalid JSON data'
        }, status=400)
    except ValueError as e:
        # IP validation error
        logger.error(f"Error blocking IP via API: {str(e)}")
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=400)
    except Exception as e:
        logger.error(f"Error blocking IP via API: {str(e)}")
        error_message = 'Failed to block IP address'
        # Check if it's a database validation error
        if 'invalid input syntax for type inet' in str(e).lower():
            error_message = f'Invalid IP address format. Please check the IP address and try again.'
        return JsonResponse({
            'success': False,
            'error': error_message
        }, status=500)


@ensure_csrf_cookie
@login_required
@role_required_api(allowed_roles=['admin'])
@require_http_methods(["GET"])
def check_ip_status_api(request, ip_address):
    """Check if an IP address is currently blocked"""
    try:
        blocked_ip = BlockedIP.objects.filter(ip_address=ip_address, status='active').first()
        
        return JsonResponse({
            'success': True,
            'is_blocked': blocked_ip is not None,
            'ip_address': ip_address,
            'blocked_ip': {
                'id': blocked_ip.id,
                'reason': blocked_ip.reason,
                'description': blocked_ip.description,
                'created_at': blocked_ip.created_at.isoformat(),
                'block_count': blocked_ip.block_count,
                'blocked_by': blocked_ip.blocked_by.username if blocked_ip.blocked_by else None,
            } if blocked_ip else None
        })
        
    except Exception as e:
        logger.error(f"Error checking IP status: {str(e)}")
        return JsonResponse({
            'success': False,
            'error': 'Failed to check IP status'
        }, status=500)

@login_required
@role_required_api(allowed_roles=['admin'])
@require_http_methods(["POST"])
def unblock_ip_api(request):
    """Unblock an IP address and optionally unblock associated users"""
    try:
        data = json.loads(request.body)
        
        ip_address = data.get('ip_address')
        reason = data.get('reason', 'Manual unblock via API')
        unblock_users = data.get('unblock_users', True)  # Default: also unblock users
        
        if not ip_address:
            return JsonResponse({
                'success': False,
                'error': 'IP address is required'
            }, status=400)
        
        try:
            blocked_ip = BlockedIP.objects.get(ip_address=ip_address, status='active')
        except BlockedIP.DoesNotExist:
            return JsonResponse({
                'success': False,
                'error': f'IP {ip_address} is not currently blocked'
            }, status=404)
        
        with transaction.atomic():
            # Find users that were blocked from this IP
            from main.models import UserBlockingLog, BlockedUser
            
            affected_users = []
            if unblock_users:
                # Find active user blocks from this IP
                user_blocks = UserBlockingLog.objects.filter(
                    ip_address=ip_address,
                    status='active'
                ).select_related('user')
                
                for user_block in user_blocks:
                    try:
                        # Find the corresponding BlockedUser record
                        blocked_user = BlockedUser.objects.get(
                            user=user_block.user,
                            status='active'
                        )
                        
                        # Unblock the user
                        blocked_user.status = 'inactive'
                        blocked_user.updated_at = timezone.now()
                        blocked_user.save()
                        
                        # Re-enable the user account
                        user_block.user.is_active = True
                        user_block.user.save()
                        
                        # Update blocking log
                        user_block.status = 'unblocked'
                        user_block.unblocked_by = request.user
                        user_block.unblocked_at = timezone.now()
                        user_block.unblock_reason = f"Auto-unblocked due to IP unblock: {reason}"
                        user_block.save()
                        
                        # Invalidate cache to force reload
                        realtime_blocker._invalidate_cache()
                        
                        # Clear failed login attempts for this user
                        from accounts.models import LoginAttempt
                        LoginAttempt.clear_attempts(user_block.user.username)
                        
                        affected_users.append(user_block.user.username)
                        logger.info(f"Auto-unblocked user {user_block.user.username} when unblocking IP {ip_address}")
                        
                    except BlockedUser.DoesNotExist:
                        # User block log exists but no BlockedUser record, just update the log
                        user_block.status = 'unblocked'
                        user_block.unblocked_by = request.user
                        user_block.unblocked_at = timezone.now()
                        user_block.unblock_reason = f"Auto-unblocked due to IP unblock: {reason}"
                        user_block.save()
                        
                        # Still try to re-enable the account
                        user_block.user.is_active = True
                        user_block.user.save()
                        
                        realtime_blocker.blocked_users.discard(user_block.user.username)
                        
                        # Clear failed login attempts for this user
                        from accounts.models import LoginAttempt
                        LoginAttempt.clear_attempts(user_block.user.username)
                        
                        affected_users.append(user_block.user.username)
            
            # Update BlockedIP record
            blocked_ip.status = 'inactive'
            blocked_ip.updated_at = timezone.now()
            blocked_ip.save()
            
            # Create IPBlockingLog entry for unblocking
            IPBlockingLog.objects.create(
                ip_address=ip_address,
                block_type='manual',
                block_reason='other',
                reason_details=f"Unblocked: {reason}",
                blocked_by=blocked_ip.blocked_by,
                status='unblocked',
                unblocked_by=request.user,
                unblocked_at=timezone.now(),
                unblock_reason=reason,
                metadata={
                    'api_request': True,
                    'original_reason': blocked_ip.reason,
                    'unblocked_users': affected_users
                }
            )
            
            # Invalidate cache to force reload
            realtime_blocker._invalidate_cache()
        
        response_message = f'Successfully unblocked IP {ip_address}'
        if affected_users:
            response_message += f' and {len(affected_users)} user(s): {", ".join(affected_users)}'
        
        return JsonResponse({
            'success': True,
            'message': response_message,
            'data': {
                'ip_address': ip_address,
                'original_reason': blocked_ip.reason,
                'unblock_reason': reason,
                'unblocked_users': affected_users,
            }
        })
        
    except json.JSONDecodeError:
        return JsonResponse({
            'success': False,
            'error': 'Invalid JSON data'
        }, status=400)
    except Exception as e:
        logger.error(f"Error unblocking IP via API: {str(e)}")
        return JsonResponse({
            'success': False,
            'error': 'Failed to unblock IP address'
        }, status=500)


@login_required
@role_required_api(allowed_roles=['admin'])
@require_http_methods(["POST"])
def block_user_api(request):
    """Block a user account"""
    try:
        data = json.loads(request.body)
        
        username = data.get('username')
        reason = data.get('reason', 'Manual block via API')
        description = data.get('description', '')
        priority = data.get('priority', 'medium')
        expires_hours = data.get('expires_hours')
        
        if not username:
            return JsonResponse({
                'success': False,
                'error': 'Username is required'
            }, status=400)
        
        # Validate priority
        if priority not in ['low', 'medium', 'high', 'critical']:
            return JsonResponse({
                'success': False,
                'error': 'Invalid priority level'
            }, status=400)
        
        # Check if user exists
        try:
            user = User.objects.get(username=username)
        except User.DoesNotExist:
            return JsonResponse({
                'success': False,
                'error': f'User {username} not found'
            }, status=404)
        
        # Calculate expiration time
        expires_at = None
        if expires_hours:
            expires_at = timezone.now() + timezone.timedelta(hours=expires_hours)
        
        with transaction.atomic():
            # Create or update BlockedUser record
            blocked_user, created = BlockedUser.objects.get_or_create(
                user=user,
                defaults={
                    'reason': reason,
                    'description': description,
                    'priority': priority,
                    'status': 'active',
                    'blocked_by': request.user,
                    'expires_at': expires_at,
                    'last_seen': timezone.now(),
                }
            )
            
            if not created:
                # Update existing record
                blocked_user.reason = reason
                blocked_user.description = description
                blocked_user.priority = priority
                blocked_user.status = 'active'
                blocked_user.blocked_by = request.user
                blocked_user.expires_at = expires_at
                blocked_user.block_count += 1
                blocked_user.last_seen = timezone.now()
                blocked_user.save()
            
            # Create UserBlockingLog entry
            UserBlockingLog.objects.create(
                user=user,
                block_type='manual',
                block_reason='other',
                reason_details=reason,
                ip_address=request.META.get('REMOTE_ADDR', '127.0.0.1'),
                blocked_by=request.user,
                expires_at=expires_at,
                metadata={
                    'api_request': True,
                    'priority': priority,
                    'description': description
                }
            )
            
            # Disable the user account
            user.is_active = False
            user.save()
            
            # Invalidate cache to force reload
            realtime_blocker._invalidate_cache()
        
        return JsonResponse({
            'success': True,
            'message': f'Successfully blocked user {username}',
            'data': {
                'username': username,
                'email': user.email,
                'reason': reason,
                'priority': priority,
                'created': created,
                'expires_at': expires_at.isoformat() if expires_at else None,
            }
        })
        
    except json.JSONDecodeError:
        return JsonResponse({
            'success': False,
            'error': 'Invalid JSON data'
        }, status=400)
    except Exception as e:
        error_trace = traceback.format_exc()
        logger.error(f"Error blocking user via API: {str(e)}\n{error_trace}")
        error_message = f'Failed to block user account: {str(e)}' if DEBUG else 'Failed to block user account'
        return JsonResponse({
            'success': False,
            'error': error_message,
            'details': str(e) if DEBUG else None
        }, status=500)


@login_required
@role_required_api(allowed_roles=['admin'])
@require_http_methods(["POST"])
def unblock_user_api(request):
    """Unblock a user account"""
    try:
        data = json.loads(request.body)
        
        username = data.get('username')
        reason = data.get('reason', 'Manual unblock via API')
        
        if not username:
            return JsonResponse({
                'success': False,
                'error': 'Username is required'
            }, status=400)
        
        try:
            user = User.objects.get(username=username)
            blocked_user = BlockedUser.objects.get(user=user, status='active')
        except User.DoesNotExist:
            return JsonResponse({
                'success': False,
                'error': f'User {username} not found'
            }, status=404)
        except BlockedUser.DoesNotExist:
            return JsonResponse({
                'success': False,
                'error': f'User {username} is not currently blocked'
            }, status=404)
        
        with transaction.atomic():
            # Update BlockedUser record
            blocked_user.status = 'inactive'
            blocked_user.updated_at = timezone.now()
            blocked_user.save()
            
            # Create UserBlockingLog entry for unblocking
            UserBlockingLog.objects.create(
                user=user,
                block_type='manual',
                block_reason='other',
                reason_details=f"Unblocked: {reason}",
                ip_address=request.META.get('REMOTE_ADDR', '127.0.0.1'),
                blocked_by=blocked_user.blocked_by,
                status='unblocked',
                unblocked_by=request.user,
                unblocked_at=timezone.now(),
                unblock_reason=reason,
                metadata={
                    'api_request': True,
                    'original_reason': blocked_user.reason
                }
            )
            
            # Reactivate the user account
            user.is_active = True
            user.save()
            
            # Clear failed login attempts from database
            from accounts.models import LoginAttempt
            LoginAttempt.clear_attempts(username)
            
            # Invalidate cache to force reload
            realtime_blocker._invalidate_cache()
        
        return JsonResponse({
            'success': True,
            'message': f'Successfully unblocked user {username}',
            'data': {
                'username': username,
                'email': user.email,
                'original_reason': blocked_user.reason,
                'unblock_reason': reason,
            }
        })
        
    except json.JSONDecodeError:
        return JsonResponse({
            'success': False,
            'error': 'Invalid JSON data'
        }, status=400)
    except Exception as e:
        logger.error(f"Error unblocking user via API: {str(e)}")
        return JsonResponse({
            'success': False,
            'error': 'Failed to unblock user account'
        }, status=500)


@ensure_csrf_cookie
@require_http_methods(["GET", "OPTIONS"])
def get_csrf_token_api(request):
    """
    Get CSRF token for API requests - Secure Double Submit Cookie Pattern.
    
    This endpoint:
    - Sets the CSRF cookie (HttpOnly, Secure) - JS cannot read it
    - Returns the token in JSON response - JS gets token from here
    - Does NOT require authentication - accessible to all users
    
    Frontend should:
    1. Call this endpoint to get the CSRF token
    2. Send the token in X-CSRFToken header for POST requests
    3. Include credentials: 'include' in fetch options
    """
    # Handle OPTIONS preflight for CORS
    if request.method == 'OPTIONS':
        response = JsonResponse({})
        response['Access-Control-Allow-Origin'] = request.META.get('HTTP_ORIGIN', '*')
        response['Access-Control-Allow-Methods'] = 'GET, OPTIONS'
        response['Access-Control-Allow-Credentials'] = 'true'
        response['Access-Control-Allow-Headers'] = 'Content-Type, X-CSRFToken'
        return response
    
    from django.middleware.csrf import get_token
    token = get_token(request)
    
    response = JsonResponse({
        'success': True,
        'csrfToken': token,  # Use camelCase for consistency with frontend
        'token_length': len(token) if token else 0,
        'header_name': 'X-CSRFToken',
        'instructions': {
            'step1': 'Call this endpoint to get CSRF token',
            'step2': 'Store token in memory (do not store in localStorage/cookie)',
            'step3': 'Send token in X-CSRFToken header for POST/PUT/DELETE requests',
            'step4': 'Always include credentials: "include" in fetch options',
            'note': 'Token is 64 characters. Cookie is HttpOnly (JS cannot read it).'
        }
    })
    
    # Set CORS headers for cross-origin requests
    origin = request.META.get('HTTP_ORIGIN')
    if origin:
        response['Access-Control-Allow-Origin'] = origin
        response['Access-Control-Allow-Credentials'] = 'true'
    
    return response
