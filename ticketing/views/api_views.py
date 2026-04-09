from django.http import JsonResponse, HttpResponseForbidden
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from django.db.models import Q
from django.shortcuts import get_object_or_404
import json

from main.models import device_list
from ..models import Ticket, TicketCategory, LossCategory, TicketFieldDefinition
from ..services import TicketDashboardService
from ..utils import get_accessible_sites_for_user, has_ticketing_access


@login_required
@require_http_methods(["GET"])
def api_get_sites(request):
    """API endpoint to get accessible sites for the user"""
    if not has_ticketing_access(request.user):
        return JsonResponse({'error': 'Access denied. You do not have access to the ticketing system.'}, status=403)
    sites = get_accessible_sites_for_user(request.user)
    
    sites_data = [{
        'asset_code': site.asset_code,
        'asset_name': site.asset_name,
        'country': site.country,
        'portfolio': site.portfolio
    } for site in sites]
    
    return JsonResponse({'sites': sites_data})


@login_required
@require_http_methods(["GET"])
def api_get_device_types(request):
    """API endpoint to get device types for a selected site"""
    if not has_ticketing_access(request.user):
        return JsonResponse({'error': 'Access denied. You do not have access to the ticketing system.'}, status=403)
    asset_code = request.GET.get('site')
    
    if not asset_code:
        return JsonResponse({'error': 'Site parameter is required'}, status=400)
    
    # Get device types for the selected site
    device_types = device_list.objects.filter(
        parent_code=asset_code
    ).values_list('device_type', flat=True).distinct().order_by('device_type')
    
    return JsonResponse({'device_types': list(device_types)})


@login_required
@require_http_methods(["GET"])
def api_get_device_sub_groups(request):
    """API endpoint to get device sub groups for a selected site and device type"""
    if not has_ticketing_access(request.user):
        return JsonResponse({'error': 'Access denied. You do not have access to the ticketing system.'}, status=403)
    asset_code = request.GET.get('site')
    device_type = request.GET.get('type')
    
    if not asset_code or not device_type:
        return JsonResponse({'error': 'Site and type parameters are required'}, status=400)
    
    # Get device sub groups
    device_sub_groups = device_list.objects.filter(
        parent_code=asset_code,
        device_type=device_type
    ).values_list('device_sub_group', flat=True).distinct().order_by('device_sub_group')
    
    return JsonResponse({'device_sub_groups': list(device_sub_groups)})


@login_required
@require_http_methods(["GET"])
def api_get_devices(request):
    """API endpoint to get devices for a selected site, device type, and device sub group"""
    if not has_ticketing_access(request.user):
        return JsonResponse({'error': 'Access denied. You do not have access to the ticketing system.'}, status=403)
    asset_code = request.GET.get('site')
    device_type = request.GET.get('type')
    device_sub_group = request.GET.get('subgroup')
    
    if not asset_code:
        return JsonResponse({'error': 'Site parameter is required'}, status=400)
    
    # Build query
    query = Q(parent_code=asset_code)
    
    if device_type:
        query &= Q(device_type=device_type)
    
    if device_sub_group:
        # If subgroup is provided, filter by device_sub_group field
        # This can be either a device_sub_group value or a device_id (for sub devices)
        query &= Q(device_sub_group=device_sub_group)
    
    # Get devices
    devices = device_list.objects.filter(query).order_by('device_name')
    
    devices_data = [{
        'device_id': device.device_id,
        'device_name': device.device_name,
        'device_code': device.device_code,
        'device_type': device.device_type,
        'device_sub_group': device.device_sub_group,
        'device_make': device.device_make,
        'device_model': device.device_model
    } for device in devices]
    
    return JsonResponse({'devices': devices_data})


@login_required
@require_http_methods(["GET"])
def api_get_ticket_stats(request):
    """API endpoint to get ticket statistics for dashboard"""
    if not has_ticketing_access(request.user):
        return JsonResponse({'error': 'Access denied. You do not have access to the ticketing system.'}, status=403)

    service = TicketDashboardService(request.user)
    tickets = service.get_queryset(request.GET)
    data = service.serialize_ticket_stats(tickets)
    return JsonResponse(data)


@login_required
@require_http_methods(["GET"])
def api_get_field_definitions(request):
    """API endpoint to get active field definitions for dynamic fields"""
    if not has_ticketing_access(request.user):
        return JsonResponse({'error': 'Access denied. You do not have access to the ticketing system.'}, status=403)
    field_definitions = TicketFieldDefinition.objects.filter(
        is_active=True
    ).order_by('display_order', 'field_label')
    
    fields_data = [{
        'field_name': field.field_name,
        'field_label': field.field_label,
        'field_type': field.field_type,
        'field_options': field.field_options,
        'is_required': field.is_required,
        'display_order': field.display_order
    } for field in field_definitions]
    
    return JsonResponse({'field_definitions': fields_data})


@login_required
@require_http_methods(["GET"])
def api_get_categories(request):
    """API endpoint to get ticket categories"""
    if not has_ticketing_access(request.user):
        return JsonResponse({'error': 'Access denied. You do not have access to the ticketing system.'}, status=403)
    categories = TicketCategory.objects.filter(is_active=True).order_by('display_order', 'name')
    
    categories_data = [{
        'id': category.id,
        'name': category.name,
        'description': category.description
    } for category in categories]
    
    return JsonResponse({'categories': categories_data})


@login_required
@require_http_methods(["GET"])
def api_get_loss_categories(request):
    """API endpoint to get loss categories"""
    if not has_ticketing_access(request.user):
        return JsonResponse({'error': 'Access denied. You do not have access to the ticketing system.'}, status=403)
    loss_categories = LossCategory.objects.filter(is_active=True).order_by('display_order', 'name')
    
    categories_data = [{
        'id': category.id,
        'name': category.name,
        'description': category.description
    } for category in loss_categories]
    
    return JsonResponse({'loss_categories': categories_data})


@login_required
@require_http_methods(["GET"])
def ticket_quickview(request, pk):
    """API endpoint for quick view drawer - returns ticket summary as JSON"""
    if not has_ticketing_access(request.user):
        return JsonResponse({'error': 'Access denied. You do not have access to the ticketing system.'}, status=403)
    
    ticket = get_object_or_404(Ticket, pk=pk, is_active=True)
    
    # Check if user has access to this ticket
    from main.permissions import user_has_capability
    if not user_has_capability(request.user, 'ticketing.view_all_tickets'):
        accessible_sites = get_accessible_sites_for_user(request.user)
        if ticket.asset_code not in accessible_sites:
            # Check if user is creator, assigned, or watcher
            if not (ticket.created_by == request.user or 
                    ticket.assigned_to == request.user or 
                    ticket.watchers.filter(id=request.user.id).exists()):
                return JsonResponse({'error': 'You do not have access to this ticket.'}, status=403)
    
    data = {
        "ticket_number": ticket.ticket_number,
        "title": ticket.title,
        "description": ticket.description,
        "status": ticket.status,
        "status_display": ticket.get_status_display(),
        "priority": ticket.priority,
        "priority_display": ticket.get_priority_display(),
        "category": ticket.category.name,
        "site": ticket.asset_code.asset_name,
        "created_at": ticket.created_at.strftime("%b %d, %Y"),
        "assigned_to": ticket.assigned_to.username if ticket.assigned_to else None,
    }
    
    return JsonResponse(data)

