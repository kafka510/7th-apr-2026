"""
Security management views
"""
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required

from django.contrib import messages

from accounts.decorators import role_required

import json, os, math
#from datetime import timezone
from django.utils import timezone

"""
@login_required
def security_alerts_view(request):
    "Security alerts view"
    return render(request, 'main/security_alerts.html')


@superuser_required
def get_blocked_ips(request):
    "Get blocked IPs"
    return JsonResponse({'blocked_ips': []})


@superuser_required
def get_blocked_users(request):
    "Get blocked users"
    return JsonResponse({'blocked_users': []})


@superuser_required
def block_ip_manual(request):
    "Manually block an IP"
    return JsonResponse({'status': 'success', 'message': 'IP blocked'})


@superuser_required
def unblock_ip_manual(request):
    "Manually unblock an IP"
    return JsonResponse({'status': 'success', 'message': 'IP unblocked'})


@superuser_required
def block_user_manual(request):
    "Manually block a user"
    return JsonResponse({'status': 'success', 'message': 'User blocked'})


@superuser_required
def unblock_user_manual(request):
    "Manually unblock a user"
    return JsonResponse({'status': 'success', 'message': 'User unblocked'})


@superuser_required
def delete_user_permanent(request):
    "Permanently delete a user"
    return JsonResponse({'status': 'success', 'message': 'User deleted'})


@login_required
def test_security_endpoint(request):
    "Test security endpoint"
    return JsonResponse({'status': 'success', 'message': 'Security test passed'})

"""

try:
    from ..models import UserProfile, AssetList, ActiveUserSession, UserActivityLog, SecurityAlert, BlockedIP
except ImportError:
    # Handle case where new models haven't been migrated yet
    from ..models import UserProfile, AssetList
    ActiveUserSession = None
    UserActivityLog = None
    SecurityAlert = None
    BlockedIP = None
    
@login_required
@role_required(allowed_roles=['admin'])  # ADMIN ONLY ACCESS
def security_alerts_view(request):
    """View for managing security alerts - ADMIN ONLY"""
    # Check if models are available
    if not SecurityAlert:
        messages.error(request, 'Security alerts not available. Please run migrations.')
        return redirect('main:user_management')
        
    try:
        # Get filter parameters
        status_filter = request.GET.get('status', 'open')
        severity_filter = request.GET.get('severity', '')
        alert_type_filter = request.GET.get('alert_type', '')
        
        # Build queryset
        queryset = SecurityAlert.objects.select_related('user', 'resolved_by').all()
        
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        
        if severity_filter:
            queryset = queryset.filter(severity=severity_filter)
        
        if alert_type_filter:
            queryset = queryset.filter(alert_type=alert_type_filter)
        
        alerts = queryset.order_by('-created_at')
        
        # Get blocking status for all unique IP addresses in one query (efficient)
        ip_blocking_status = {}
        if BlockedIP:
            # Get all unique IP addresses from alerts
            unique_ips = set()
            for alert in alerts:
                if alert.ip_address:
                    unique_ips.add(alert.ip_address)
            
            # Fetch all blocked IPs in one query
            if unique_ips:
                blocked_ips = BlockedIP.objects.filter(
                    ip_address__in=unique_ips,
                    status='active'
                ).select_related('blocked_by')
                
                # Create a dictionary mapping IP to blocking info
                for blocked_ip in blocked_ips:
                    ip_blocking_status[blocked_ip.ip_address] = {
                        'is_blocked': True,
                        'reason': blocked_ip.reason,
                        'description': blocked_ip.description,
                        'blocked_by': blocked_ip.blocked_by.username if blocked_ip.blocked_by else 'System',
                        'created_at': blocked_ip.created_at,
                        'block_count': blocked_ip.block_count,
                    }
        
        # Add blocking status as an attribute to each alert for easy template access
        for alert in alerts:
            if alert.ip_address and alert.ip_address in ip_blocking_status:
                alert.ip_is_blocked = True
                alert.ip_blocking_info = ip_blocking_status[alert.ip_address]
            else:
                alert.ip_is_blocked = False
                alert.ip_blocking_info = None
        
        # Handle POST requests (resolve alerts)
        if request.method == 'POST':
            alert_id = request.POST.get('alert_id')
            action = request.POST.get('action')
            notes = request.POST.get('notes', '')
            
            try:
                alert = SecurityAlert.objects.get(id=alert_id)
                if action == 'resolve':
                    alert.status = 'resolved'
                    alert.resolved_by = request.user
                    alert.resolved_at = timezone.now()
                    alert.resolution_notes = notes
                    alert.save()
                    messages.success(request, 'Alert resolved successfully.')
                elif action == 'false_positive':
                    alert.status = 'false_positive'
                    alert.resolved_by = request.user
                    alert.resolved_at = timezone.now()
                    alert.resolution_notes = notes
                    alert.save()
                    messages.success(request, 'Alert marked as false positive.')
                
                return redirect('main:security_alerts')
                
            except SecurityAlert.DoesNotExist:
                messages.error(request, 'Alert not found.')
        
        return render(request, 'main/security_alerts.html', {
            'alerts': alerts,
            'ip_blocking_status': ip_blocking_status,  # Dictionary mapping IP to blocking info
            'status_filter': status_filter,
            'severity_filter': severity_filter,
            'alert_type_filter': alert_type_filter,
            'status_choices': SecurityAlert.STATUS_CHOICES,
            'severity_choices': SecurityAlert.SEVERITY_CHOICES,
            'alert_type_choices': SecurityAlert.ALERT_TYPE_CHOICES,
        })
        
    except Exception as e:
        messages.error(request, f'Error loading security alerts: {str(e)}')
        return redirect('main:user_management')
