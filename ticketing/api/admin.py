"""
API views for ticketing admin management
"""
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.shortcuts import get_object_or_404

from main.permissions import user_has_capability
from ..models import LossCategory, PreventiveMaintenanceRule, Ticket, TicketCategory, TicketSubCategory
from ..tasks import process_pm_rules_task
from ..utils import has_ticketing_access


def check_admin_permission(user, capability):
    """Helper to check admin permissions"""
    if not has_ticketing_access(user):
        return Response({"detail": "Access denied. Ticketing access required."}, status=403)
    if not user_has_capability(user, capability):
        return Response({"detail": "Access denied. Admin privileges required."}, status=403)
    return None


# Ticket Categories API
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def ticket_categories_list(request):
    """List all ticket categories"""
    error = check_admin_permission(request.user, 'ticketing.manage_settings')
    if error:
        return error
    
    categories = TicketCategory.objects.all().order_by('display_order', 'name')
    data = [
        {
            'id': cat.id,
            'name': cat.name,
            'description': cat.description or '',
            'display_order': cat.display_order,
            'is_active': cat.is_active,
            'created_at': cat.created_at.isoformat(),
            'updated_at': cat.updated_at.isoformat(),
        }
        for cat in categories
    ]
    return Response({'categories': data})


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def ticket_category_create(request):
    """Create a new ticket category"""
    error = check_admin_permission(request.user, 'ticketing.manage_settings')
    if error:
        return error
    
    name = request.data.get('name', '').strip()
    description = request.data.get('description', '').strip()
    display_order = request.data.get('display_order', 0)
    is_active = request.data.get('is_active', True)
    
    if not name:
        return Response({"detail": "Name is required"}, status=400)
    
    if TicketCategory.objects.filter(name=name).exists():
        return Response({"detail": "A category with this name already exists"}, status=400)
    
    category = TicketCategory.objects.create(
        name=name,
        description=description,
        display_order=display_order,
        is_active=is_active
    )
    
    return Response({
        'id': category.id,
        'name': category.name,
        'description': category.description or '',
        'display_order': category.display_order,
        'is_active': category.is_active,
        'created_at': category.created_at.isoformat(),
        'updated_at': category.updated_at.isoformat(),
    }, status=201)


@api_view(['PUT', 'PATCH'])
@permission_classes([IsAuthenticated])
def ticket_category_update(request, pk):
    """Update a ticket category"""
    error = check_admin_permission(request.user, 'ticketing.manage_settings')
    if error:
        return error
    
    category = get_object_or_404(TicketCategory, pk=pk)
    
    name = request.data.get('name', '').strip()
    if name:
        if TicketCategory.objects.filter(name=name).exclude(pk=pk).exists():
            return Response({"detail": "A category with this name already exists"}, status=400)
        category.name = name
    
    if 'description' in request.data:
        category.description = request.data.get('description', '').strip()
    if 'display_order' in request.data:
        category.display_order = request.data.get('display_order', 0)
    if 'is_active' in request.data:
        category.is_active = request.data.get('is_active', True)
    
    category.save()
    
    return Response({
        'id': category.id,
        'name': category.name,
        'description': category.description or '',
        'display_order': category.display_order,
        'is_active': category.is_active,
        'created_at': category.created_at.isoformat(),
        'updated_at': category.updated_at.isoformat(),
    })


@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def ticket_category_delete(request, pk):
    """Delete a ticket category (superuser only)"""
    error = check_admin_permission(request.user, 'ticketing.manage_settings')
    if error:
        return error
    
    if not request.user.is_superuser:
        return Response({"detail": "Only superusers can delete categories"}, status=403)
    
    category = get_object_or_404(TicketCategory, pk=pk)
    
    # Check if category is in use and reassign tickets to a default category
    tickets_count = Ticket.objects.filter(category=category).count()
    if tickets_count > 0:
        # Find another active category to reassign tickets to
        default_category = TicketCategory.objects.filter(is_active=True).exclude(pk=pk).first()
        
        if not default_category:
            # If no other active category exists, try any other category
            default_category = TicketCategory.objects.exclude(pk=pk).first()
        
        if default_category:
            # Reassign all tickets to the default category
            Ticket.objects.filter(category=category).update(category=default_category)
            category_name = category.name
            category.delete()
            return Response({
                "success": True, 
                "message": f"Category '{category_name}' deleted successfully. {tickets_count} ticket(s) were reassigned to '{default_category.name}'."
            })
        else:
            # No other category exists, cannot delete
            return Response({
                "detail": f"Cannot delete category because it is being used by {tickets_count} ticket(s) and no other category exists to reassign them to."
            }, status=400)
    
    category_name = category.name
    category.delete()
    
    return Response({"success": True, "message": f"Category '{category_name}' deleted successfully"})


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def ticket_subcategories_list(request):
    """List all ticket sub-categories, optionally filtered by category"""
    error = check_admin_permission(request.user, 'ticketing.manage_settings')
    if error:
        return error

    category_id = request.query_params.get('category')
    queryset = TicketSubCategory.objects.all()
    if category_id:
        queryset = queryset.filter(category_id=category_id)

    subcategories = queryset.order_by('category__display_order', 'display_order', 'name')
    data = [
        {
            'id': sub.id,
            'name': sub.name,
            'description': sub.description or '',
            'display_order': sub.display_order,
            'is_active': sub.is_active,
            'category': {
                'id': sub.category.id,
                'name': sub.category.name,
            } if sub.category else None,
            'created_at': sub.created_at.isoformat(),
            'updated_at': sub.updated_at.isoformat(),
        }
        for sub in subcategories
    ]
    return Response({'subCategories': data})


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def ticket_subcategory_create(request):
    """Create a new ticket sub-category"""
    error = check_admin_permission(request.user, 'ticketing.manage_settings')
    if error:
        return error

    name = request.data.get('name', '').strip()
    description = request.data.get('description', '').strip()
    display_order = request.data.get('display_order', 0)
    is_active = request.data.get('is_active', True)
    category_id = request.data.get('category')

    if not name:
        return Response({"detail": "Name is required"}, status=400)
    if not category_id:
        return Response({"detail": "Category is required"}, status=400)

    category = get_object_or_404(TicketCategory, pk=category_id)

    if TicketSubCategory.objects.filter(name=name, category=category).exists():
        return Response({"detail": "A sub-category with this name already exists for the selected category"}, status=400)

    sub_category = TicketSubCategory.objects.create(
        name=name,
        category=category,
        description=description,
        display_order=display_order,
        is_active=is_active,
    )

    return Response({
        'id': sub_category.id,
        'name': sub_category.name,
        'description': sub_category.description or '',
        'display_order': sub_category.display_order,
        'is_active': sub_category.is_active,
        'category': {
            'id': category.id,
            'name': category.name,
        },
        'created_at': sub_category.created_at.isoformat(),
        'updated_at': sub_category.updated_at.isoformat(),
    }, status=201)


@api_view(['PUT', 'PATCH'])
@permission_classes([IsAuthenticated])
def ticket_subcategory_update(request, pk):
    """Update an existing ticket sub-category"""
    error = check_admin_permission(request.user, 'ticketing.manage_settings')
    if error:
        return error

    sub_category = get_object_or_404(TicketSubCategory, pk=pk)

    if 'name' in request.data:
        name = request.data.get('name', '').strip()
        if not name:
            return Response({"detail": "Name cannot be empty"}, status=400)
        if TicketSubCategory.objects.filter(name=name, category=sub_category.category).exclude(pk=pk).exists():
            return Response({"detail": "A sub-category with this name already exists for the selected category"}, status=400)
        sub_category.name = name

    if 'category' in request.data:
        category_id = request.data.get('category')
        category = get_object_or_404(TicketCategory, pk=category_id)
        sub_category.category = category

    if 'description' in request.data:
        sub_category.description = request.data.get('description', '').strip()
    if 'display_order' in request.data:
        sub_category.display_order = request.data.get('display_order', 0)
    if 'is_active' in request.data:
        sub_category.is_active = request.data.get('is_active', True)

    sub_category.save()

    return Response({
        'id': sub_category.id,
        'name': sub_category.name,
        'description': sub_category.description or '',
        'display_order': sub_category.display_order,
        'is_active': sub_category.is_active,
        'category': {
            'id': sub_category.category.id,
            'name': sub_category.category.name,
        } if sub_category.category else None,
        'created_at': sub_category.created_at.isoformat(),
        'updated_at': sub_category.updated_at.isoformat(),
    })


@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def ticket_subcategory_delete(request, pk):
    """Delete a ticket sub-category (superuser only)"""
    error = check_admin_permission(request.user, 'ticketing.manage_settings')
    if error:
        return error

    if not request.user.is_superuser:
        return Response({"detail": "Only superusers can delete sub-categories"}, status=403)

    sub_category = get_object_or_404(TicketSubCategory, pk=pk)

    tickets_count = Ticket.objects.filter(sub_category=sub_category).count()
    if tickets_count > 0:
        Ticket.objects.filter(sub_category=sub_category).update(sub_category=None)

    name = sub_category.name
    sub_category.delete()

    if tickets_count > 0:
        return Response({
            "success": True,
            "message": f"Sub-category '{name}' deleted. {tickets_count} ticket(s) were updated to remove this sub-category."
        })

    return Response({"success": True, "message": f"Sub-category '{name}' deleted successfully"})


# Loss Categories API
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def loss_categories_list(request):
    """List all loss categories"""
    error = check_admin_permission(request.user, 'ticketing.manage_settings')
    if error:
        return error
    
    categories = LossCategory.objects.all().order_by('display_order', 'name')
    data = [
        {
            'id': cat.id,
            'name': cat.name,
            'description': cat.description or '',
            'display_order': cat.display_order,
            'is_active': cat.is_active,
            'created_at': cat.created_at.isoformat(),
            'updated_at': cat.updated_at.isoformat(),
        }
        for cat in categories
    ]
    return Response({'categories': data})


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def loss_category_create(request):
    """Create a new loss category"""
    error = check_admin_permission(request.user, 'ticketing.manage_settings')
    if error:
        return error
    
    name = request.data.get('name', '').strip()
    description = request.data.get('description', '').strip()
    display_order = request.data.get('display_order', 0)
    is_active = request.data.get('is_active', True)
    
    if not name:
        return Response({"detail": "Name is required"}, status=400)
    
    if LossCategory.objects.filter(name=name).exists():
        return Response({"detail": "A category with this name already exists"}, status=400)
    
    category = LossCategory.objects.create(
        name=name,
        description=description,
        display_order=display_order,
        is_active=is_active
    )
    
    return Response({
        'id': category.id,
        'name': category.name,
        'description': category.description or '',
        'display_order': category.display_order,
        'is_active': category.is_active,
        'created_at': category.created_at.isoformat(),
        'updated_at': category.updated_at.isoformat(),
    }, status=201)


@api_view(['PUT', 'PATCH'])
@permission_classes([IsAuthenticated])
def loss_category_update(request, pk):
    """Update a loss category"""
    error = check_admin_permission(request.user, 'ticketing.manage_settings')
    if error:
        return error
    
    category = get_object_or_404(LossCategory, pk=pk)
    
    name = request.data.get('name', '').strip()
    if name:
        if LossCategory.objects.filter(name=name).exclude(pk=pk).exists():
            return Response({"detail": "A category with this name already exists"}, status=400)
        category.name = name
    
    if 'description' in request.data:
        category.description = request.data.get('description', '').strip()
    if 'display_order' in request.data:
        category.display_order = request.data.get('display_order', 0)
    if 'is_active' in request.data:
        category.is_active = request.data.get('is_active', True)
    
    category.save()
    
    return Response({
        'id': category.id,
        'name': category.name,
        'description': category.description or '',
        'display_order': category.display_order,
        'is_active': category.is_active,
        'created_at': category.created_at.isoformat(),
        'updated_at': category.updated_at.isoformat(),
    })


@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def loss_category_delete(request, pk):
    """Delete a loss category (superuser only)"""
    error = check_admin_permission(request.user, 'ticketing.manage_settings')
    if error:
        return error
    
    if not request.user.is_superuser:
        return Response({"detail": "Only superusers can delete categories"}, status=403)
    
    category = get_object_or_404(LossCategory, pk=pk)
    
    # Check if category is in use and set to NULL (loss_category allows NULL)
    tickets_count = Ticket.objects.filter(loss_category=category).count()
    if tickets_count > 0:
        # Set loss_category to NULL for all tickets using this category
        Ticket.objects.filter(loss_category=category).update(loss_category=None)
    
    category_name = category.name
    category.delete()
    
    if tickets_count > 0:
        return Response({
            "success": True, 
            "message": f"Category '{category_name}' deleted successfully. {tickets_count} ticket(s) had their loss category cleared."
        })
    
    return Response({"success": True, "message": f"Category '{category_name}' deleted successfully"})


# PM Rules API
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def pm_rules_list(request):
    """List all PM rules"""
    error = check_admin_permission(request.user, 'ticketing.manage_pm_rules')
    if error:
        return error
    
    rules = PreventiveMaintenanceRule.objects.all().order_by('name')
    data = []
    for rule in rules:
        rule_data = {
            'id': rule.id,
            'name': rule.name,
            'description': rule.description or '',
            'rule_type': rule.rule_type,
            'rule_type_display': rule.get_rule_type_display(),
            'date_field_name': rule.date_field_name or '',
            'alert_days_before': rule.alert_days_before,
            'start_date_field': rule.start_date_field or '',
            'frequency_field': rule.frequency_field or '',
            'category': {
                'id': rule.category.id,
                'name': rule.category.name,
            } if rule.category else None,
            'priority': rule.priority,
            'priority_display': rule.get_priority_display(),
            'title_template': rule.title_template,
            'description_template': rule.description_template,
            'assign_to_role': rule.assign_to_role or '',
            'send_email_notification': rule.send_email_notification,
            'is_active': rule.is_active,
            'created_by': {
                'id': rule.created_by.id,
                'username': rule.created_by.username,
            } if rule.created_by else None,
            'created_at': rule.created_at.isoformat() if rule.created_at else None,
            'updated_at': rule.updated_at.isoformat() if rule.updated_at else None,
        }
        data.append(rule_data)
    
    return Response({'rules': data})


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def pm_rule_detail(request, pk):
    """Get a single PM rule"""
    error = check_admin_permission(request.user, 'ticketing.manage_pm_rules')
    if error:
        return error
    
    rule = get_object_or_404(PreventiveMaintenanceRule, pk=pk)
    
    return Response({
        'id': rule.id,
        'name': rule.name,
        'description': rule.description or '',
        'rule_type': rule.rule_type,
        'rule_type_display': rule.get_rule_type_display(),
        'date_field_name': rule.date_field_name or '',
        'alert_days_before': rule.alert_days_before,
        'start_date_field': rule.start_date_field or '',
        'frequency_field': rule.frequency_field or '',
        'category': {
            'id': rule.category.id,
            'name': rule.category.name,
        } if rule.category else None,
        'priority': rule.priority,
        'priority_display': rule.get_priority_display(),
        'title_template': rule.title_template,
        'description_template': rule.description_template,
        'assign_to_role': rule.assign_to_role or '',
        'send_email_notification': rule.send_email_notification,
        'is_active': rule.is_active,
        'created_by': {
            'id': rule.created_by.id,
            'username': rule.created_by.username,
        } if rule.created_by else None,
        'created_at': rule.created_at.isoformat() if rule.created_at else None,
        'updated_at': rule.updated_at.isoformat() if rule.updated_at else None,
    })


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def pm_rule_create(request):
    """Create a new PM rule"""
    error = check_admin_permission(request.user, 'ticketing.manage_pm_rules')
    if error:
        return error
    
    # Validate required fields
    name = request.data.get('name', '').strip()
    if not name:
        return Response({"detail": "Name is required"}, status=400)
    
    rule_type = request.data.get('rule_type')
    if rule_type not in ['date_based', 'frequency_based']:
        return Response({"detail": "Invalid rule_type. Must be 'date_based' or 'frequency_based'"}, status=400)
    
    # Validate rule type specific fields
    if rule_type == 'date_based':
        if not request.data.get('date_field_name'):
            return Response({"detail": "Date field is required for date-based rules"}, status=400)
        if not request.data.get('alert_days_before'):
            return Response({"detail": "Alert days before is required for date-based rules"}, status=400)
    elif rule_type == 'frequency_based':
        if not request.data.get('start_date_field'):
            return Response({"detail": "Start date field is required for frequency-based rules"}, status=400)
        if not request.data.get('frequency_field'):
            return Response({"detail": "Frequency field is required for frequency-based rules"}, status=400)
    
    category_id = request.data.get('category')
    if not category_id:
        return Response({"detail": "Category is required"}, status=400)
    
    try:
        category = TicketCategory.objects.get(pk=category_id, is_active=True)
    except TicketCategory.DoesNotExist:
        return Response({"detail": "Invalid category"}, status=400)
    
    # Create the rule
    rule = PreventiveMaintenanceRule.objects.create(
        name=name,
        description=request.data.get('description', '').strip(),
        rule_type=rule_type,
        date_field_name=request.data.get('date_field_name') or None,
        alert_days_before=request.data.get('alert_days_before'),
        start_date_field=request.data.get('start_date_field') or None,
        frequency_field=request.data.get('frequency_field') or None,
        category=category,
        priority=request.data.get('priority', 'medium'),
        title_template=request.data.get('title_template', ''),
        description_template=request.data.get('description_template', ''),
        assign_to_role=request.data.get('assign_to_role') or None,
        send_email_notification=request.data.get('send_email_notification', True),
        is_active=request.data.get('is_active', True),
        created_by=request.user,
    )
    
    return Response({
        'id': rule.id,
        'name': rule.name,
        'description': rule.description or '',
        'rule_type': rule.rule_type,
        'rule_type_display': rule.get_rule_type_display(),
        'date_field_name': rule.date_field_name or '',
        'alert_days_before': rule.alert_days_before,
        'start_date_field': rule.start_date_field or '',
        'frequency_field': rule.frequency_field or '',
        'category': {
            'id': rule.category.id,
            'name': rule.category.name,
        },
        'priority': rule.priority,
        'priority_display': rule.get_priority_display(),
        'title_template': rule.title_template,
        'description_template': rule.description_template,
        'assign_to_role': rule.assign_to_role or '',
        'send_email_notification': rule.send_email_notification,
        'is_active': rule.is_active,
        'created_by': {
            'id': rule.created_by.id,
            'username': rule.created_by.username,
        },
        'created_at': rule.created_at.isoformat() if rule.created_at else None,
        'updated_at': rule.updated_at.isoformat() if rule.updated_at else None,
    }, status=201)


@api_view(['PUT', 'PATCH'])
@permission_classes([IsAuthenticated])
def pm_rule_update(request, pk):
    """Update a PM rule"""
    error = check_admin_permission(request.user, 'ticketing.manage_pm_rules')
    if error:
        return error
    
    rule = get_object_or_404(PreventiveMaintenanceRule, pk=pk)
    
    # Update fields
    if 'name' in request.data:
        rule.name = request.data.get('name', '').strip()
    if 'description' in request.data:
        rule.description = request.data.get('description', '').strip()
    if 'rule_type' in request.data:
        rule.rule_type = request.data.get('rule_type')
    if 'date_field_name' in request.data:
        rule.date_field_name = request.data.get('date_field_name') or None
    if 'alert_days_before' in request.data:
        rule.alert_days_before = request.data.get('alert_days_before')
    if 'start_date_field' in request.data:
        rule.start_date_field = request.data.get('start_date_field') or None
    if 'frequency_field' in request.data:
        rule.frequency_field = request.data.get('frequency_field') or None
    if 'category' in request.data:
        category_id = request.data.get('category')
        if category_id:
            try:
                rule.category = TicketCategory.objects.get(pk=category_id, is_active=True)
            except TicketCategory.DoesNotExist:
                return Response({"detail": "Invalid category"}, status=400)
    if 'priority' in request.data:
        rule.priority = request.data.get('priority')
    if 'title_template' in request.data:
        rule.title_template = request.data.get('title_template', '')
    if 'description_template' in request.data:
        rule.description_template = request.data.get('description_template', '')
    if 'assign_to_role' in request.data:
        rule.assign_to_role = request.data.get('assign_to_role') or None
    if 'send_email_notification' in request.data:
        rule.send_email_notification = request.data.get('send_email_notification', True)
    if 'is_active' in request.data:
        rule.is_active = request.data.get('is_active', True)
    
    # Validate rule type specific fields
    if rule.rule_type == 'date_based':
        if not rule.date_field_name:
            return Response({"detail": "Date field is required for date-based rules"}, status=400)
        if not rule.alert_days_before:
            return Response({"detail": "Alert days before is required for date-based rules"}, status=400)
    elif rule.rule_type == 'frequency_based':
        if not rule.start_date_field:
            return Response({"detail": "Start date field is required for frequency-based rules"}, status=400)
        if not rule.frequency_field:
            return Response({"detail": "Frequency field is required for frequency-based rules"}, status=400)
    
    rule.save()
    
    return Response({
        'id': rule.id,
        'name': rule.name,
        'description': rule.description or '',
        'rule_type': rule.rule_type,
        'rule_type_display': rule.get_rule_type_display(),
        'date_field_name': rule.date_field_name or '',
        'alert_days_before': rule.alert_days_before,
        'start_date_field': rule.start_date_field or '',
        'frequency_field': rule.frequency_field or '',
        'category': {
            'id': rule.category.id,
            'name': rule.category.name,
        } if rule.category else None,
        'priority': rule.priority,
        'priority_display': rule.get_priority_display(),
        'title_template': rule.title_template,
        'description_template': rule.description_template,
        'assign_to_role': rule.assign_to_role or '',
        'send_email_notification': rule.send_email_notification,
        'is_active': rule.is_active,
        'created_by': {
            'id': rule.created_by.id,
            'username': rule.created_by.username,
        } if rule.created_by else None,
        'created_at': rule.created_at.isoformat() if rule.created_at else None,
        'updated_at': rule.updated_at.isoformat() if rule.updated_at else None,
    })


@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def pm_rule_delete(request, pk):
    """Delete a PM rule (superuser only)"""
    if not request.user.is_superuser:
        return Response({"detail": "Only superusers can delete PM rules"}, status=403)
    
    rule = get_object_or_404(PreventiveMaintenanceRule, pk=pk)
    rule_name = rule.name
    
    # Delete associated schedules
    rule.schedules.all().delete()
    rule.delete()
    
    return Response({"success": True, "message": f"PM Rule '{rule_name}' and all its schedules deleted successfully"})


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def pm_rule_toggle(request, pk):
    """Toggle PM rule active status"""
    error = check_admin_permission(request.user, 'ticketing.manage_pm_rules')
    if error:
        return error
    
    rule = get_object_or_404(PreventiveMaintenanceRule, pk=pk)
    rule.is_active = not rule.is_active
    rule.save()
    
    status_text = "activated" if rule.is_active else "deactivated"
    return Response({
        "success": True,
        "message": f"PM Rule '{rule.name}' {status_text} successfully",
        "is_active": rule.is_active
    })


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def pm_rule_trigger(request):
    """Trigger PM rule processing (superuser only)"""
    if not request.user.is_superuser:
        return Response({"detail": "Only superusers can trigger PM processing"}, status=403)
    
    task_result = process_pm_rules_task.delay()
    
    return Response({
        "success": True,
        "message": "Preventive Maintenance processing has been queued. This may take a few moments to complete.",
        "task_id": task_result.id
    })

