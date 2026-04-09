"""
Admin views for ticketing system management
"""
from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_http_methods

from main.permissions import user_has_capability
from ..forms import LossCategoryForm, TicketCategoryForm
from ..forms_pm import PreventiveMaintenanceRuleForm
from ..models import LossCategory, PreventiveMaintenanceRule, TicketCategory
from ..tasks import process_pm_rules_task
from ..utils import has_ticketing_access

@login_required
def ticketing_admin_view(request):
    """Main admin page for ticketing system settings"""
    if not has_ticketing_access(request.user):
        return render(request, 'ticketing/access_denied.html', status=403)
    if not user_has_capability(request.user, 'ticketing.manage_settings'):
        return render(request, 'ticketing/access_denied.html', {'message': 'Access denied. Admin privileges required.'}, status=403)
    
    # Check for React version flag
    from waffle import flag_is_active
    if flag_is_active(request, 'react_ticket_admin'):
        context = {
            'is_superuser': request.user.is_superuser,
        }
        return render(request, 'ticketing/ticketing_admin_react.html', context)
    
    ticket_categories = TicketCategory.objects.all().order_by('display_order', 'name')
    loss_categories = LossCategory.objects.all().order_by('display_order', 'name')
    pm_rules = PreventiveMaintenanceRule.objects.all().order_by('name')
    last_pm_trigger_task_id = request.session.pop('last_pm_trigger_task_id', None)
    
    context = {
        'ticket_categories': ticket_categories,
        'loss_categories': loss_categories,
        'pm_rules': pm_rules,
        'is_superuser': request.user.is_superuser,
        'last_pm_trigger_task_id': last_pm_trigger_task_id,
    }
    
    return render(request, 'ticketing/ticketing_admin.html', context)


@login_required
@require_http_methods(["GET", "POST"])
def create_ticket_category(request):
    """Create a new ticket category"""
    if not has_ticketing_access(request.user):
        return render(request, 'ticketing/access_denied.html', status=403)
    if not user_has_capability(request.user, 'ticketing.manage_settings'):
        return render(request, 'ticketing/access_denied.html', {'message': 'Access denied. Admin privileges required.'}, status=403)
    
    if request.method == 'POST':
        form = TicketCategoryForm(request.POST)
        if form.is_valid():
            category = form.save()
            messages.success(request, f'Ticket category "{category.name}" created successfully!')
            return redirect('ticketing:ticketing_admin')
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = TicketCategoryForm()
    
    return render(request, 'ticketing/category_form.html', {
        'form': form,
        'category_type': 'Ticket Category',
        'action': 'Create'
    })


@login_required
@require_http_methods(["GET", "POST"])
def edit_ticket_category(request, pk):
    """Edit an existing ticket category"""
    if not has_ticketing_access(request.user):
        return render(request, 'ticketing/access_denied.html', status=403)
    if not user_has_capability(request.user, 'ticketing.manage_settings'):
        return render(request, 'ticketing/access_denied.html', {'message': 'Access denied. Admin privileges required.'}, status=403)
    
    category = get_object_or_404(TicketCategory, pk=pk)
    
    if request.method == 'POST':
        form = TicketCategoryForm(request.POST, instance=category)
        if form.is_valid():
            category = form.save()
            messages.success(request, f'Ticket category "{category.name}" updated successfully!')
            return redirect('ticketing:ticketing_admin')
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = TicketCategoryForm(instance=category)
    
    return render(request, 'ticketing/category_form.html', {
        'form': form,
        'category': category,
        'category_type': 'Ticket Category',
        'action': 'Edit'
    })


@login_required
@require_http_methods(["POST"])
def delete_ticket_category(request, pk):
    """Delete a ticket category (superuser only)"""
    if not has_ticketing_access(request.user):
        return render(request, 'ticketing/access_denied.html', status=403)
    if not user_has_capability(request.user, 'ticketing.manage_settings'):
        return render(request, 'ticketing/access_denied.html', {'message': 'Access denied. Admin privileges required.'}, status=403)
    
    if not request.user.is_superuser:
        messages.error(request, 'Only superusers can delete categories.')
        return redirect('ticketing:ticketing_admin')
    
    category = get_object_or_404(TicketCategory, pk=pk)
    category_name = category.name
    
    # Check if category is in use
    from ..models import Ticket
    tickets_using_category = Ticket.objects.filter(category=category).count()
    
    if tickets_using_category > 0:
        messages.error(request, f'Cannot delete category "{category_name}" because it is being used by {tickets_using_category} ticket(s).')
        return redirect('ticketing:ticketing_admin')
    
    category.delete()
    messages.success(request, f'Ticket category "{category_name}" deleted successfully!')
    return redirect('ticketing:ticketing_admin')


@login_required
@require_http_methods(["GET", "POST"])
def create_loss_category(request):
    """Create a new loss category"""
    if not has_ticketing_access(request.user):
        return render(request, 'ticketing/access_denied.html', status=403)
    if not user_has_capability(request.user, 'ticketing.manage_settings'):
        return render(request, 'ticketing/access_denied.html', {'message': 'Access denied. Admin privileges required.'}, status=403)
    
    if request.method == 'POST':
        form = LossCategoryForm(request.POST)
        if form.is_valid():
            category = form.save()
            messages.success(request, f'Loss category "{category.name}" created successfully!')
            return redirect('ticketing:ticketing_admin')
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = LossCategoryForm()
    
    return render(request, 'ticketing/category_form.html', {
        'form': form,
        'category_type': 'Loss Category',
        'action': 'Create'
    })


@login_required
@require_http_methods(["GET", "POST"])
def edit_loss_category(request, pk):
    """Edit an existing loss category"""
    if not has_ticketing_access(request.user):
        return render(request, 'ticketing/access_denied.html', status=403)
    if not user_has_capability(request.user, 'ticketing.manage_settings'):
        return render(request, 'ticketing/access_denied.html', {'message': 'Access denied. Admin privileges required.'}, status=403)
    
    category = get_object_or_404(LossCategory, pk=pk)
    
    if request.method == 'POST':
        form = LossCategoryForm(request.POST, instance=category)
        if form.is_valid():
            category = form.save()
            messages.success(request, f'Loss category "{category.name}" updated successfully!')
            return redirect('ticketing:ticketing_admin')
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = LossCategoryForm(instance=category)
    
    return render(request, 'ticketing/category_form.html', {
        'form': form,
        'category': category,
        'category_type': 'Loss Category',
        'action': 'Edit'
    })


@login_required
@require_http_methods(["POST"])
def delete_loss_category(request, pk):
    """Delete a loss category (superuser only)"""
    if not has_ticketing_access(request.user):
        return render(request, 'ticketing/access_denied.html', status=403)
    if not user_has_capability(request.user, 'ticketing.manage_settings'):
        return render(request, 'ticketing/access_denied.html', {'message': 'Access denied. Admin privileges required.'}, status=403)
    
    if not request.user.is_superuser:
        messages.error(request, 'Only superusers can delete categories.')
        return redirect('ticketing:ticketing_admin')
    
    category = get_object_or_404(LossCategory, pk=pk)
    category_name = category.name
    
    # Check if category is in use
    from ..models import Ticket
    tickets_using_category = Ticket.objects.filter(loss_category=category).count()
    
    if tickets_using_category > 0:
        messages.error(request, f'Cannot delete category "{category_name}" because it is being used by {tickets_using_category} ticket(s).')
        return redirect('ticketing:ticketing_admin')
    
    category.delete()
    messages.success(request, f'Loss category "{category_name}" deleted successfully!')
    return redirect('ticketing:ticketing_admin')


# Preventive Maintenance Rule Management Views

@login_required
def create_pm_rule(request):
    """Create a new PM rule"""
    if not has_ticketing_access(request.user):
        return render(request, 'ticketing/access_denied.html', status=403)
    if not user_has_capability(request.user, 'ticketing.manage_pm_rules'):
        return render(request, 'ticketing/access_denied.html', {'message': 'Access denied. Admin privileges required.'}, status=403)
    
    if request.method == 'POST':
        form = PreventiveMaintenanceRuleForm(request.POST)
        if form.is_valid():
            pm_rule = form.save(commit=False)
            pm_rule.created_by = request.user
            pm_rule.save()
            messages.success(request, f'PM Rule "{pm_rule.name}" created successfully!')
            return redirect('ticketing:ticketing_admin')
    else:
        form = PreventiveMaintenanceRuleForm()
    
    return render(request, 'ticketing/pm_rule_form.html', {
        'form': form,
        'title': 'Create Preventive Maintenance Rule',
        'action': 'Create'
    })


@login_required
def edit_pm_rule(request, pk):
    """Edit an existing PM rule"""
    if not has_ticketing_access(request.user):
        return render(request, 'ticketing/access_denied.html', status=403)
    if not user_has_capability(request.user, 'ticketing.manage_pm_rules'):
        return render(request, 'ticketing/access_denied.html', {'message': 'Access denied. Admin privileges required.'}, status=403)
    
    pm_rule = get_object_or_404(PreventiveMaintenanceRule, pk=pk)
    
    if request.method == 'POST':
        form = PreventiveMaintenanceRuleForm(request.POST, instance=pm_rule)
        if form.is_valid():
            form.save()
            messages.success(request, f'PM Rule "{pm_rule.name}" updated successfully!')
            return redirect('ticketing:ticketing_admin')
    else:
        form = PreventiveMaintenanceRuleForm(instance=pm_rule)
    
    return render(request, 'ticketing/pm_rule_form.html', {
        'form': form,
        'title': 'Edit Preventive Maintenance Rule',
        'action': 'Update',
        'pm_rule': pm_rule
    })


@login_required
def delete_pm_rule(request, pk):
    """Delete a PM rule (superuser only)"""
    if not request.user.is_superuser:
        return render(request, 'ticketing/access_denied.html', {'message': 'Access denied. Superuser privileges required.'}, status=403)
    
    pm_rule = get_object_or_404(PreventiveMaintenanceRule, pk=pk)
    
    if request.method == 'POST':
        rule_name = pm_rule.name
        # Also delete all associated schedules
        pm_rule.schedules.all().delete()
        pm_rule.delete()
        messages.success(request, f'PM Rule "{rule_name}" and all its schedules deleted successfully!')
        return redirect('ticketing:ticketing_admin')
    
    return render(request, 'ticketing/pm_rule_confirm_delete.html', {'pm_rule': pm_rule})


@login_required
def toggle_pm_rule(request, pk):
    """Toggle PM rule active status"""
    if not has_ticketing_access(request.user):
        return render(request, 'ticketing/access_denied.html', status=403)
    if not user_has_capability(request.user, 'ticketing.manage_pm_rules'):
        return render(request, 'ticketing/access_denied.html', {'message': 'Access denied. Admin privileges required.'}, status=403)
    
    pm_rule = get_object_or_404(PreventiveMaintenanceRule, pk=pk)
    pm_rule.is_active = not pm_rule.is_active
    pm_rule.save()
    
    status = "activated" if pm_rule.is_active else "deactivated"
    messages.success(request, f'PM Rule "{pm_rule.name}" {status} successfully!')
    return redirect('ticketing:ticketing_admin')


@login_required
@require_http_methods(["POST"])
def trigger_pm_processing(request):
    """Allow superusers to manually trigger PM rule processing via Celery."""
    if not request.user.is_superuser:
        return render(request, 'ticketing/access_denied.html', {
            'message': 'Access denied. Superuser privileges required to trigger PM processing.'
        }, status=403)

    task_result = process_pm_rules_task.delay()
    messages.success(
        request,
        'Preventive Maintenance processing has been queued. This may take a few moments to complete.'
    )
    if getattr(settings, 'CELERY_TASK_ALWAYS_EAGER', False):
        messages.info(request, 'Celery is configured for synchronous execution; processing ran immediately.')

    request.session['last_pm_trigger_task_id'] = task_result.id
    return redirect('ticketing:ticketing_admin')

