from datetime import timedelta
import csv
import re

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import EmptyPage, PageNotAnInteger, Paginator
from django.db.models import Avg, Count, Q
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.views.generic import CreateView, DetailView, ListView, UpdateView
from waffle import flag_is_active

from ..forms import (
    TicketAssignForm,
    TicketAttachmentForm,
    TicketCommentForm,
    TicketFilterForm,
    TicketForm,
    TicketStatusForm,
    TicketWatcherForm,
)
from ..models import Ticket, TicketActivity, TicketAttachment, TicketCategory, TicketComment, LossCategory
from ..permissions import can_assign_ticket, can_edit_ticket
from ..utils import (
    can_user_assign_ticket,
    can_user_edit_ticket,
    can_user_manage_watchers,
    get_accessible_sites_for_user,
    has_ticketing_access,
    log_ticket_activity,
)
from main.permissions import user_has_capability


def check_ticketing_access(user):
    """Helper function to check ticketing access and raise 403 if denied"""
    if not has_ticketing_access(user):
        from django.http import HttpResponseForbidden
        from django.template.loader import render_to_string
        return HttpResponseForbidden(
            render_to_string('ticketing/access_denied.html', {
                'message': 'You do not have access to the ticketing system. Please contact an administrator.'
            })
        )
    return None


@method_decorator(login_required, name='dispatch')
class MyTicketsView(ListView):
    """View for non-admin users to see tickets assigned to them"""
    model = Ticket
    template_name = 'ticketing/my_tickets.html'
    context_object_name = 'tickets'
    paginate_by = 20
    
    def dispatch(self, request, *args, **kwargs):
        """Check ticketing access before processing request"""
        access_check = check_ticketing_access(request.user)
        if access_check:
            return access_check
        return super().dispatch(request, *args, **kwargs)
    
    def get_queryset(self):
        """Get tickets created by, assigned to, or watched by the current user"""
        # Non-admin users can only see tickets they created, assigned to, or watching
        queryset = Ticket.objects.filter(
            is_active=True
        ).filter(
            Q(created_by=self.request.user) | Q(assigned_to=self.request.user) | Q(watchers=self.request.user)
        ).select_related(
            'asset_code', 'device_id', 'created_by', 'assigned_to',
            'category', 'loss_category'
        ).prefetch_related('watchers').distinct().order_by('-created_at')
        
        # Apply user access filtering
        if not user_has_capability(self.request.user, 'ticketing.view_all_sites'):
            accessible_sites = get_accessible_sites_for_user(self.request.user)
            queryset = queryset.filter(asset_code__in=accessible_sites)
        
        # Apply filters if provided
        status = self.request.GET.get('status')
        if status:
            queryset = queryset.filter(status=status)
        
        priority = self.request.GET.get('priority')
        if priority:
            queryset = queryset.filter(priority=priority)
        
        search = self.request.GET.get('search')
        if search:
            queryset = queryset.filter(
                Q(title__icontains=search) |
                Q(description__icontains=search) |
                Q(ticket_number__icontains=search)
            )
        
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['statuses'] = Ticket.STATUS_CHOICES
        context['priorities'] = Ticket.PRIORITY_CHOICES
        context['filter_form'] = TicketFilterForm(user=self.request.user, initial=self.request.GET.dict())
        return context


@method_decorator(login_required, name='dispatch')
class TicketListView(ListView):
    """List view for tickets with AJAX support for infinite scroll"""
    model = Ticket
    template_name = 'ticketing/ticket_list.html'
    context_object_name = 'tickets'
    paginate_by = 12  # 12 tickets per page (3 columns x 4 rows)
    allow_empty = True  # Allow page to render even with no results
    paginate_orphans = 0  # Don't combine last page

    def get_template_names(self):
        if flag_is_active(self.request, 'react_ticket_list'):
            return ['ticketing/ticket_list_react.html']
        return [self.template_name]

    def dispatch(self, request, *args, **kwargs):
        """Check ticketing access before processing request"""
        access_check = check_ticketing_access(request.user)
        if access_check:
            return access_check
        return super().dispatch(request, *args, **kwargs)

    def get_queryset(self):
        queryset = Ticket.objects.filter(is_active=True).select_related(
            'asset_code', 'device_id', 'created_by', 'assigned_to', 'category', 'loss_category'
        ).prefetch_related('watchers')
        
        # Apply user access filtering
        if not user_has_capability(self.request.user, 'ticketing.view_all_tickets'):
            queryset = queryset.filter(
                Q(created_by=self.request.user) | Q(assigned_to=self.request.user) | Q(watchers=self.request.user)
            ).distinct()
            accessible_sites = get_accessible_sites_for_user(self.request.user)
            queryset = queryset.filter(asset_code__in=accessible_sites)
        
        # Apply filters (support multiple values for multi-select)
        status_list = self.request.GET.getlist('status')
        if status_list:
            queryset = queryset.filter(status__in=status_list)
        
        priority_list = self.request.GET.getlist('priority')
        if priority_list:
            queryset = queryset.filter(priority__in=priority_list)
        
        category_list = self.request.GET.getlist('category')
        if category_list:
            queryset = queryset.filter(category_id__in=category_list)
        
        asset_code_list = self.request.GET.getlist('asset_code')
        if asset_code_list:
            queryset = queryset.filter(asset_code_id__in=asset_code_list)
        
        assigned_to = self.request.GET.get('assigned_to')
        if assigned_to:
            queryset = queryset.filter(assigned_to_id=assigned_to)
        
        # Search
        search = self.request.GET.get('search')
        if search:
            queryset = queryset.filter(
                Q(ticket_number__icontains=search) |
                Q(title__icontains=search) |
                Q(description__icontains=search)
            )
        
        # Apply column-based sorting
        sort_field = self.request.GET.get('sort', '')
        sort_order = self.request.GET.get('order', 'asc')
        
        # Map sort fields to actual database fields
        sort_map = {
            'ticket': 'ticket_number',
            'site': 'asset_code__asset_name',
            'category': 'category__name',
            'priority': 'priority',
            'status': 'status',
            'created': 'created_at',
            'assigned': 'assigned_to__username',
            'closed': 'closed_at',
        }
        
        if sort_field in sort_map:
            field = sort_map[sort_field]
            if sort_order == 'desc':
                field = f'-{field}'
            queryset = queryset.order_by(field)
        else:
            # Default sorting: newest first
            queryset = queryset.order_by('-created_at')
        
        return queryset

    def paginate_queryset(self, queryset, page_size):
        """Override pagination to handle EmptyPage gracefully"""
        paginator = self.get_paginator(
            queryset,
            page_size,
            orphans=self.get_paginate_orphans(),
            allow_empty_first_page=True,
        )
        page_kwarg = self.page_kwarg
        page = self.kwargs.get(page_kwarg) or self.request.GET.get(page_kwarg) or 1
        
        try:
            page_number = int(page)
        except (ValueError, TypeError):
            page_number = 1
        
        # If no items exist at all
        if paginator.count == 0:
            from django.core.paginator import Page
            empty_page = Page([], 1, paginator)
            return (paginator, empty_page, [], False)
        
        # Clamp page_number to valid range
        if page_number < 1:
            page_number = 1
        elif page_number > paginator.num_pages:
            page_number = paginator.num_pages
        
        try:
            page = paginator.page(page_number)
            return (paginator, page, page.object_list, page.has_other_pages())
        except (PageNotAnInteger, EmptyPage):
            # Fallback to page 1
            page = paginator.page(1)
            return (paginator, page, page.object_list, page.has_other_pages())
    
    def export_csv(self):
        """Export filtered tickets to CSV"""
        queryset = self.get_queryset()
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="tickets_export.csv"'
        
        writer = csv.writer(response)
        writer.writerow([
            'Ticket ID', 'Title', 'Status', 'Priority', 'Site', 
            'Category', 'Assigned To', 'Created At', 'Closed At'
        ])
        
        for ticket in queryset:
            writer.writerow([
                ticket.ticket_number,
                ticket.title,
                ticket.get_status_display(),
                ticket.get_priority_display(),
                ticket.asset_code.asset_name if ticket.asset_code else '',
                ticket.category.name if ticket.category else '',
                ticket.assigned_to.username if ticket.assigned_to else 'Unassigned',
                ticket.created_at.strftime('%Y-%m-%d %H:%M'),
                ticket.closed_at.strftime('%Y-%m-%d %H:%M') if ticket.closed_at else ''
            ])
        
        return response
    
    def get(self, request, *args, **kwargs):
        """Handle AJAX, CSV export, and regular requests"""
        # Handle CSV export
        if request.GET.get("export") == "1":
            return self.export_csv()
        
        # Handle AJAX requests for infinite scroll
        if request.GET.get("ajax") == "1":
            queryset = self.get_queryset()
            paginator = Paginator(queryset, self.paginate_by)
            page_number = request.GET.get('page', 1)
            
            try:
                page_number = int(page_number)
            except ValueError:
                page_number = 1
            
            # Check if page is out of range
            if page_number > paginator.num_pages:
                return HttpResponse('')  # Stop infinite scroll
            
            try:
                page_obj = paginator.page(page_number)
            except PageNotAnInteger:
                page_obj = paginator.page(1)
            except EmptyPage:
                return HttpResponse('')
            
            html = render_to_string(
                "ticketing/partials/ticket_list_items.html", 
                {
                    "tickets": page_obj.object_list,
                    "user": request.user,
                },
                request=request
            )
            return HttpResponse(html)
        
        # Regular page request - wrap in try-except to catch EmptyPage
        try:
            return super().get(request, *args, **kwargs)
        except EmptyPage:
            # If EmptyPage is raised, redirect to page 1
            query_dict = request.GET.copy()
            query_dict['page'] = '1'
            redirect_url = f"{request.path}?{query_dict.urlencode()}"
            return redirect(redirect_url)

    def get_context_data(self, **kwargs):
        try:
            context = super().get_context_data(**kwargs)
        except EmptyPage:
            # If EmptyPage is raised, manually create context
            context = {
                'tickets': [],
                'page_obj': None,
                'paginator': None,
                'is_paginated': False,
            }
        
        context['filter_form'] = TicketFilterForm(user=self.request.user, initial=self.request.GET.dict())
        context['statuses'] = Ticket.STATUS_CHOICES
        context['priorities'] = Ticket.PRIORITY_CHOICES
        context['categories'] = TicketCategory.objects.filter(is_active=True)
        context['current_sort'] = self.request.GET.get('sort', '')
        context['current_order'] = self.request.GET.get('order', 'asc')
        
        # Create a safe page_obj if it doesn't exist
        if not context.get('page_obj'):
            from django.core.paginator import Page, Paginator
            paginator = Paginator([], 1)
            context['page_obj'] = Page([], 1, paginator)
            context['paginator'] = paginator
            context['is_paginated'] = False
        
        return context


@method_decorator(login_required, name='dispatch')
class TicketCreateView(CreateView):
    def dispatch(self, request, *args, **kwargs):
        """Check ticketing access before processing request"""
        access_check = check_ticketing_access(request.user)
        if access_check:
            return access_check
        return super().dispatch(request, *args, **kwargs)
    """Create new ticket view"""
    model = Ticket
    form_class = TicketForm
    template_name = 'ticketing/ticket_create.html'
    success_url = None  # Will be set in get_success_url

    def get_template_names(self):
        from waffle import flag_is_active
        if flag_is_active(self.request, 'react_ticket_create'):
            return ['ticketing/ticket_create_react.html']
        return [self.template_name]
    
    def get_success_url(self):
        """Redirect to the created ticket's detail page"""
        return reverse('ticketing:ticket_detail', kwargs={'pk': self.object.pk})

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs

    def form_valid(self, form):
        form.instance.created_by = self.request.user
        
        # device_id is now a device_list object from clean_device_id, set it on instance
        device_id = form.cleaned_data.get('device_id')
        if device_id:
            form.instance.device_id = device_id
            
            # Store device information snapshot in metadata for historical tracking and analytics
            if not form.instance.metadata:
                form.instance.metadata = {}
            form.instance.metadata['device_info'] = {
                'device_id': device_id.device_id,
                'device_name': device_id.device_name,
                'device_serial': device_id.device_serial,
                'device_make': device_id.device_make,
                'device_model': device_id.device_model,
                'device_type': device_id.device_type,
            }
        
        # sub_device_id is a string, store it in metadata
        sub_device_id = form.cleaned_data.get('sub_device_id')
        if sub_device_id:
            if not form.instance.metadata:
                form.instance.metadata = {}
            form.instance.metadata['sub_device_id'] = sub_device_id
            
            # Also store sub device info if available
            try:
                from main.models import device_list
                sub_device = device_list.objects.get(device_id=sub_device_id)
                form.instance.metadata['sub_device_info'] = {
                    'device_id': sub_device.device_id,
                    'device_name': sub_device.device_name,
                    'device_serial': sub_device.device_serial,
                    'device_make': sub_device.device_make,
                    'device_model': sub_device.device_model,
                    'device_type': sub_device.device_type,
                }
            except:
                pass
        
        # Get IP address
        ip_address = self.request.META.get('REMOTE_ADDR')
        
        # Save watchers (many-to-many needs to be saved after the instance)
        watchers = form.cleaned_data.get('watchers', [])
        
        response = super().form_valid(form)
        
        # Set watchers after ticket is saved
        if watchers:
            self.object.watchers.set(watchers)
        
        # Log activity
        log_ticket_activity(
            ticket=self.object,
            user=self.request.user,
            action_type='created',
            ip_address=ip_address
        )
        
        # Send email notification
        from ..tasks import send_ticket_created_notification
        send_ticket_created_notification.delay(self.object.id)
        
        messages.success(self.request, f'Ticket {self.object.ticket_number} created successfully!')
        return response

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['categories'] = TicketCategory.objects.filter(is_active=True)
        context['loss_categories'] = LossCategory.objects.filter(is_active=True)
        return context


@method_decorator(login_required, name='dispatch')
class TicketDetailView(DetailView):
    model = Ticket
    template_name = 'ticketing/ticket_detail.html'
    context_object_name = 'ticket'

    def dispatch(self, request, *args, **kwargs):
        """Check ticketing access before processing request"""
        access_check = check_ticketing_access(request.user)
        if access_check:
            return access_check
        return super().dispatch(request, *args, **kwargs)

    def get_template_names(self):
        if flag_is_active(self.request, 'react_ticket_detail'):
            return ['ticketing/ticket_detail_react.html']
        return [self.template_name]
    """Detail view for ticket"""
    
    def get(self, request, *args, **kwargs):
        """Handle quickview mode"""
        if "quickview" in request.GET:
            self.object = self.get_object()
            return render(request, "ticketing/partials/quickview.html", {"ticket": self.object})
        return super().get(request, *args, **kwargs)

    def get_queryset(self):
        queryset = Ticket.objects.filter(is_active=True).select_related(
            'asset_code', 'device_id', 'created_by', 'assigned_to', 
            'closed_by', 'category', 'loss_category'
        ).prefetch_related('watchers')
        
        # Apply user access filtering
        if not user_has_capability(self.request.user, 'ticketing.view_all_tickets'):
            queryset = queryset.filter(
                Q(created_by=self.request.user) | Q(assigned_to=self.request.user) | Q(watchers=self.request.user)
            ).distinct()
            accessible_sites = get_accessible_sites_for_user(self.request.user)
            queryset = queryset.filter(asset_code__in=accessible_sites)
        
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        ticket = self.object
        
        # Check permissions - allow if user can manage ticket, is assigned, or a watcher
        is_assigned = ticket.assigned_to == self.request.user
        is_watcher = ticket.watchers.filter(id=self.request.user.id).exists()
        can_close_any = user_has_capability(self.request.user, 'ticketing.close_any')
        
        context['can_edit'] = can_user_edit_ticket(self.request.user, ticket) or is_assigned or is_watcher
        context['can_assign'] = can_user_assign_ticket(self.request.user)
        context['can_close'] = ticket.status != 'closed' and can_close_any
        context['can_change_status'] = ticket.status != 'closed' or can_close_any
        context['is_assigned_user'] = is_assigned
        context['is_watcher'] = is_watcher
        
        # Comments - allow if user can edit, is assigned, or is a watcher
        context['can_comment'] = can_user_edit_ticket(self.request.user, ticket) or is_assigned or is_watcher
        context['comments'] = ticket.comments.all().select_related('user').order_by('created_at')
        context['comment_form'] = TicketCommentForm()
        
        # Activities
        context['activities'] = ticket.activities.all().select_related('user').order_by('-timestamp')[:20]
        
        # Attachments
        context['attachments'] = ticket.attachments.all().select_related('uploaded_by').order_by('-uploaded_at')
        
        # Forms
        context['assign_form'] = TicketAssignForm()
        context['status_form'] = TicketStatusForm(initial={'status': ticket.status})
        context['attachment_form'] = TicketAttachmentForm()
        if can_user_manage_watchers(self.request.user):
            context['watcher_form'] = TicketWatcherForm(initial={'watchers': ticket.watchers.all()})
        else:
            context['watcher_form'] = None
        
        return context


@method_decorator(login_required, name='dispatch')
@method_decorator(can_edit_ticket, name='dispatch')
class TicketUpdateView(UpdateView):
    def dispatch(self, request, *args, **kwargs):
        """Check ticketing access before processing request"""
        access_check = check_ticketing_access(request.user)
        if access_check:
            return access_check
        return super().dispatch(request, *args, **kwargs)
    """Update ticket view"""
    model = Ticket
    form_class = TicketForm
    template_name = 'ticketing/ticket_edit.html'

    def get_template_names(self):
        from waffle import flag_is_active
        # Always use React template (same as create view behavior)
        # Only fallback to Django template if explicitly disabled via flag
        try:
            if flag_is_active(self.request, 'disable_react_ticket_edit'):
                return [self.template_name]
        except Exception:
            pass
        # Default to React template
        return ['ticketing/ticket_edit_react.html']

    def get_queryset(self):
        return Ticket.objects.filter(is_active=True)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs

    def form_valid(self, form):
        old_instance = Ticket.objects.get(pk=self.object.pk)
        old_status = old_instance.status
        old_priority = old_instance.priority
        old_assigned_to = old_instance.assigned_to
        
        ip_address = self.request.META.get('REMOTE_ADDR')
        
        # Save watchers (many-to-many needs to be saved after the instance)
        watchers = form.cleaned_data.get('watchers', [])
        
        response = super().form_valid(form)
        
        # Set watchers after ticket is saved
        if watchers is not None:
            self.object.watchers.set(watchers)
        
        # Log status change and send notification
        if old_status != self.object.status:
            log_ticket_activity(
                ticket=self.object,
                user=self.request.user,
                action_type='status_changed',
                old_value={'status': old_status},
                new_value={'status': self.object.status},
                field_changed='status',
                ip_address=ip_address
            )
            # Send status change notification
            from ..tasks import send_ticket_status_changed_notification
            send_ticket_status_changed_notification.delay(
                self.object.id, 
                old_status, 
                self.object.status
            )
        
        # Log priority change
        if old_priority != self.object.priority:
            log_ticket_activity(
                ticket=self.object,
                user=self.request.user,
                action_type='priority_changed',
                old_value={'priority': old_priority},
                new_value={'priority': self.object.priority},
                field_changed='priority',
                ip_address=ip_address
            )
        
        # Log assignment change and send notification
        if old_assigned_to != self.object.assigned_to:
            log_ticket_activity(
                ticket=self.object,
                user=self.request.user,
                action_type='assigned',
                old_value={'assigned_to': str(old_assigned_to) if old_assigned_to else None},
                new_value={'assigned_to': str(self.object.assigned_to) if self.object.assigned_to else None},
                field_changed='assigned_to',
                ip_address=ip_address
            )
            # Send assignment notification if newly assigned
            if self.object.assigned_to:
                from ..tasks import send_ticket_assignment_notification
                send_ticket_assignment_notification.delay(
                    self.object.id,
                    self.object.assigned_to.id
                )
        else:
            # General update
            log_ticket_activity(
                ticket=self.object,
                user=self.request.user,
                action_type='updated',
                ip_address=ip_address
            )
        
        messages.success(self.request, f'Ticket {self.object.ticket_number} updated successfully!')
        return response


@login_required
def add_comment(request, pk):
    """Add comment to ticket"""
    # Check ticketing access
    access_check = check_ticketing_access(request.user)
    if access_check:
        return access_check
    ticket = get_object_or_404(Ticket, pk=pk, is_active=True)
    
    if request.method == 'POST':
        form = TicketCommentForm(request.POST)
        if form.is_valid():
            comment = form.save(commit=False)
            comment.ticket = ticket
            comment.user = request.user
            comment.save()
            
            # Log activity
            log_ticket_activity(
                ticket=ticket,
                user=request.user,
                action_type='commented',
                notes=comment.comment[:100],
                ip_address=request.META.get('REMOTE_ADDR')
            )
            
            # Send comment notification
            from ..tasks import send_ticket_comment_notification
            send_ticket_comment_notification.delay(ticket.id, comment.id)
            
            messages.success(request, 'Comment added successfully!')
        else:
            messages.error(request, 'Error adding comment. Please try again.')
    
    return redirect('ticketing:ticket_detail', pk=pk)


@login_required
def change_ticket_status(request, pk):
    """Change ticket status (all users with ticketing access, but cannot close)"""
    # Check ticketing access
    access_check = check_ticketing_access(request.user)
    if access_check:
        return access_check
    ticket = get_object_or_404(Ticket, pk=pk, is_active=True)
    
    # Check if user has access to this ticket
    if not user_has_capability(request.user, 'ticketing.view_all_sites'):
        accessible_sites = get_accessible_sites_for_user(request.user)
        if ticket.asset_code not in accessible_sites:
            messages.error(request, "You don't have access to this ticket.")
            return redirect('ticketing:my_tickets')
    
    if request.method == 'POST':
        form = TicketStatusForm(request.POST)
        if form.is_valid():
            new_status = form.cleaned_data['status']
            old_status = ticket.status
            
            # Only users with close-any capability can close tickets
            can_close_any = user_has_capability(request.user, 'ticketing.close_any')
            if new_status == 'closed' and not can_close_any:
                messages.error(request, "Only administrators can close tickets.")
                return redirect('ticketing:ticket_detail', pk=pk)
            
            if old_status != new_status:
                ticket.status = new_status
                ticket.save()
                
                # Log activity
                log_ticket_activity(
                    ticket=ticket,
                    user=request.user,
                    action_type='status_changed',
                    old_value={'status': old_status},
                    new_value={'status': new_status},
                    field_changed='status',
                    notes=form.cleaned_data.get('notes', ''),
                    ip_address=request.META.get('REMOTE_ADDR')
                )
                
                # Send status change notification
                from ..tasks import send_ticket_status_changed_notification
                send_ticket_status_changed_notification.delay(ticket.id, old_status, new_status)
                
                messages.success(request, f'Ticket status changed to {ticket.get_status_display()}!')
            else:
                messages.info(request, 'Status unchanged.')
        else:
            messages.error(request, 'Error changing status. Please try again.')
    
    return redirect('ticketing:ticket_detail', pk=pk)


@login_required
def assign_ticket(request, pk):
    """Assign ticket to user"""
    # Check ticketing access
    access_check = check_ticketing_access(request.user)
    if access_check:
        return access_check
    ticket = get_object_or_404(Ticket, pk=pk, is_active=True)
    
    # Check if user has access to this ticket
    if not user_has_capability(request.user, 'ticketing.view_all_sites'):
        accessible_sites = get_accessible_sites_for_user(request.user)
        if ticket.asset_code not in accessible_sites:
            messages.error(request, "You don't have access to this ticket.")
            return redirect('ticketing:my_tickets')
    
    if request.method == 'POST':
        form = TicketAssignForm(request.POST)
        if form.is_valid():
            old_assigned_to = ticket.assigned_to
            ticket.assigned_to = form.cleaned_data['assigned_to']
            ticket.save()
            
            # Log activity
            log_ticket_activity(
                ticket=ticket,
                user=request.user,
                action_type='assigned',
                old_value={'assigned_to': str(old_assigned_to) if old_assigned_to else None},
                new_value={'assigned_to': str(ticket.assigned_to) if ticket.assigned_to else None},
                field_changed='assigned_to',
                notes=form.cleaned_data.get('notes', ''),
                ip_address=request.META.get('REMOTE_ADDR')
            )
            
            # Send assignment notification
            if ticket.assigned_to:
                from ..tasks import send_ticket_assignment_notification
                send_ticket_assignment_notification.delay(ticket.id, ticket.assigned_to.id)
            
            messages.success(request, f'Ticket assigned to {ticket.assigned_to.username}!')
        else:
            messages.error(request, 'Error assigning ticket. Please try again.')
    
    return redirect('ticketing:ticket_detail', pk=pk)


@login_required
def close_ticket(request, pk):
    """Close ticket (admin only)"""
    # Check ticketing access
    access_check = check_ticketing_access(request.user)
    if access_check:
        return access_check
    
    ticket = get_object_or_404(Ticket, pk=pk, is_active=True)
    
    # Only users with close-any capability (typically admins) can close tickets
    can_close = user_has_capability(request.user, 'ticketing.close_any')

    if not can_close:
        messages.error(request, "Only administrators can close tickets.")
        return redirect('ticketing:ticket_detail', pk=pk)
    
    if request.method == 'POST':
        old_status = ticket.status
        ticket.status = 'closed'
        ticket.closed_by = request.user
        ticket.closed_at = timezone.now()
        ticket.resolution_notes = request.POST.get('resolution_notes', '')
        ticket.save()
        
        # Log activity
        log_ticket_activity(
            ticket=ticket,
            user=request.user,
            action_type='closed',
            notes=ticket.resolution_notes,
            ip_address=request.META.get('REMOTE_ADDR')
        )
        
        # Send status change notification (closed)
        from ..tasks import send_ticket_status_changed_notification
        send_ticket_status_changed_notification.delay(ticket.id, old_status, 'closed')
        
        # If this is a PM ticket, update the schedule for next cycle
        if ticket.metadata.get('auto_generated') and ticket.metadata.get('schedule_id'):
            try:
                from ..models import PreventiveMaintenanceSchedule
                from dateutil.relativedelta import relativedelta
                
                schedule = PreventiveMaintenanceSchedule.objects.get(id=ticket.metadata['schedule_id'])
                rule = schedule.rule
                
                if rule.rule_type == 'frequency_based':
                    # Update to use closure date as new start
                    schedule.last_completed_date = ticket.closed_at.date()
                    
                    # Calculate next date
                    frequency_str = getattr(schedule.device, rule.frequency_field, '')
                    # Parse frequency (e.g., "6 months", "90 days")
                    match = re.match(r'(\d+)\s*(day|days|week|weeks|month|months|year|years)', str(frequency_str).lower())
                    if match:
                        value = int(match.group(1))
                        unit = match.group(2)
                        
                        if 'day' in unit:
                            schedule.next_maintenance_date = schedule.last_completed_date + timedelta(days=value)
                        elif 'week' in unit:
                            schedule.next_maintenance_date = schedule.last_completed_date + timedelta(weeks=value)
                        elif 'month' in unit:
                            schedule.next_maintenance_date = schedule.last_completed_date + relativedelta(months=value)
                        elif 'year' in unit:
                            schedule.next_maintenance_date = schedule.last_completed_date + relativedelta(years=value)
                        
                        schedule.save()
            except Exception as e:
                # Log but don't fail the ticket closure
                pass
        
        messages.success(request, f'Ticket {ticket.ticket_number} closed successfully!')
    
    return redirect('ticketing:ticket_detail', pk=pk)


@login_required
def reopen_ticket(request, pk):
    """Reopen closed ticket"""
    # Check ticketing access
    access_check = check_ticketing_access(request.user)
    if access_check:
        return access_check
    ticket = get_object_or_404(Ticket, pk=pk, is_active=True)
    
    if ticket.status != 'closed':
        messages.error(request, 'Only closed tickets can be reopened.')
        return redirect('ticketing:ticket_detail', pk=pk)
    
    if request.method == 'POST':
        old_status = ticket.status
        ticket.status = 'reopened'
        ticket.closed_by = None
        ticket.closed_at = None
        ticket.save()
        
        # Log activity
        log_ticket_activity(
            ticket=ticket,
            user=request.user,
            action_type='reopened',
            ip_address=request.META.get('REMOTE_ADDR')
        )
        
        # Send status change notification (reopened)
        from ..tasks import send_ticket_status_changed_notification
        send_ticket_status_changed_notification.delay(ticket.id, old_status, 'reopened')
        
        messages.success(request, f'Ticket {ticket.ticket_number} reopened!')
    
    return redirect('ticketing:ticket_detail', pk=pk)


@login_required
def upload_attachment(request, pk):
    """Upload file attachment to ticket"""
    # Check ticketing access
    access_check = check_ticketing_access(request.user)
    if access_check:
        return access_check
    ticket = get_object_or_404(Ticket, pk=pk, is_active=True)
    
    # Check if user has access to this ticket
    if not user_has_capability(request.user, 'ticketing.view_all_sites'):
        accessible_sites = get_accessible_sites_for_user(request.user)
        if ticket.asset_code not in accessible_sites:
            messages.error(request, "You don't have access to this ticket.")
            return redirect('ticketing:my_tickets')
    
    # Check if user can edit this ticket OR is assigned to it
    can_upload = can_user_edit_ticket(request.user, ticket) or ticket.assigned_to == request.user
    if not can_upload:
        messages.error(request, "You don't have permission to upload files to this ticket.")
        return redirect('ticketing:my_tickets' if ticket.assigned_to == request.user else 'ticketing:ticket_detail', pk=pk)
    
    if request.method == 'POST':
        # Handle pasted image
        pasted_image = request.POST.get('pasted_image')
        if pasted_image and not request.FILES.get('file'):
            # Convert base64 to file
            import base64
            from django.core.files.base import ContentFile
            from django.utils import timezone
            
            try:
                # Remove data URL prefix if present
                if ',' in pasted_image:
                    header, data = pasted_image.split(',', 1)
                else:
                    data = pasted_image
                
                image_data = base64.b64decode(data)
                file_name = f'pasted-image-{timezone.now().strftime("%Y%m%d-%H%M%S")}.png'
                file_obj = ContentFile(image_data, name=file_name)
                
                # Create attachment
                attachment = TicketAttachment(
                    ticket=ticket,
                    uploaded_by=request.user,
                    file=file_obj,
                    file_name=file_name,
                    file_size=len(image_data),
                    file_type='image/png'
                )
                attachment.save()
                
                # Log activity
                log_ticket_activity(
                    ticket=ticket,
                    user=request.user,
                    action_type='attachment_added',
                    notes=f'Image pasted and uploaded: {file_name}',
                    ip_address=request.META.get('REMOTE_ADDR')
                )
                
                messages.success(request, f'Image uploaded successfully!')
            except Exception as e:
                messages.error(request, f'Error uploading pasted image: {str(e)}')
        elif request.FILES.get('file'):
            # Handle regular file upload
            form = TicketAttachmentForm(request.POST, request.FILES)
            if form.is_valid():
                attachment = form.save(commit=False)
                attachment.ticket = ticket
                attachment.uploaded_by = request.user
                attachment.file_name = request.FILES['file'].name
                
                # Get file size
                try:
                    attachment.file_size = request.FILES['file'].size
                except:
                    attachment.file_size = 0
                
                # Get file type (MIME type)
                try:
                    import mimetypes
                    file_type, _ = mimetypes.guess_type(request.FILES['file'].name)
                    attachment.file_type = file_type or 'application/octet-stream'
                except:
                    attachment.file_type = 'application/octet-stream'
                
                attachment.save()
                
                # Log activity
                log_ticket_activity(
                    ticket=ticket,
                    user=request.user,
                    action_type='attachment_added',
                    notes=f'File uploaded: {attachment.file_name}',
                    ip_address=request.META.get('REMOTE_ADDR')
                )
                
                messages.success(request, f'File "{attachment.file_name}" uploaded successfully!')
            else:
                for error in form.errors.values():
                    messages.error(request, error[0])
        else:
            messages.error(request, 'Please select a file or paste an image.')
    else:
        messages.error(request, 'Invalid request method.')
    
    return redirect('ticketing:ticket_detail', pk=pk)


@login_required
def delete_attachment(request, pk, attachment_id):
    """Delete file attachment from ticket"""
    # Check ticketing access
    access_check = check_ticketing_access(request.user)
    if access_check:
        return access_check
    ticket = get_object_or_404(Ticket, pk=pk, is_active=True)
    attachment = get_object_or_404(TicketAttachment, id=attachment_id, ticket=ticket)
    
    # Check if user can edit this ticket or if they uploaded the file
    if not can_user_edit_ticket(request.user, ticket) and attachment.uploaded_by != request.user:
        messages.error(request, "You don't have permission to delete this file.")
        return redirect('ticketing:ticket_detail', pk=pk)
    
    if request.method == 'POST':
        file_name = attachment.file_name
        
        # Delete the file from storage
        try:
            if attachment.file:
                attachment.file.delete()
        except Exception as e:
            # Log error but continue with deletion
            print(f"Error deleting file: {str(e)}")
        
        # Delete the attachment record
        attachment.delete()
        
        # Log activity
        log_ticket_activity(
            ticket=ticket,
            user=request.user,
            action_type='attachment_added',  # Using attachment_added with notes about deletion
            notes=f'File deleted: {file_name}',
            ip_address=request.META.get('REMOTE_ADDR')
        )
        
        messages.success(request, f'File "{file_name}" deleted successfully!')
    else:
        messages.error(request, 'Invalid request method.')
    
    return redirect('ticketing:ticket_detail', pk=pk)


@login_required
def delete_ticket(request, pk):
    """Permanently delete a ticket and all related records (superuser only)."""
    access_check = check_ticketing_access(request.user)
    if access_check:
        return access_check

    ticket = get_object_or_404(Ticket, pk=pk)

    if not request.user.is_superuser:
        messages.error(request, 'Only superusers can delete tickets.')
        return redirect('ticketing:ticket_detail', pk=pk)

    if request.method == 'POST':
        schedule_id = None
        if ticket.metadata:
            schedule_id = ticket.metadata.get('schedule_id')

        # Delete associated files prior to ticket removal
        for attachment in ticket.attachments.all():
            try:
                if attachment.file:
                    attachment.file.delete(save=False)
            except Exception:
                pass

        # Cascade delete of related objects
        ticket.watchers.clear()
        ticket.comments.all().delete()
        ticket.activities.all().delete()
        ticket.attachments.all().delete()
        ticket.email_notifications.all().delete()

        # Update related PM schedule if applicable
        if schedule_id:
            try:
                from ..models import PreventiveMaintenanceSchedule
                schedule = PreventiveMaintenanceSchedule.objects.get(id=schedule_id)
                if schedule.last_ticket_id == ticket.id:
                    schedule.last_ticket = None
                    schedule.last_ticket_generated = None
                    schedule.save(update_fields=['last_ticket', 'last_ticket_generated', 'updated_at'])
            except Exception:
                pass

        ticket_number = ticket.ticket_number
        ticket.delete()
        messages.success(request, f'Ticket {ticket_number} and all related history were deleted successfully.')
        return redirect('ticketing:ticket_list')

    return render(request, 'ticketing/ticket_confirm_delete.html', {
        'ticket': ticket,
        'related_counts': {
            'comments': ticket.comments.count(),
            'attachments': ticket.attachments.count(),
            'activities': ticket.activities.count(),
            'emails': ticket.email_notifications.count(),
        }
    })


@login_required
def update_watchers(request, pk):
    """Update ticket watchers (admin and superuser)."""
    access_check = check_ticketing_access(request.user)
    if access_check:
        return access_check

    ticket = get_object_or_404(Ticket, pk=pk, is_active=True)

    if not can_user_manage_watchers(request.user):
        messages.error(request, "You don't have permission to manage watchers for this ticket.")
        return redirect('ticketing:ticket_detail', pk=pk)

    if request.method == 'POST':
        form = TicketWatcherForm(request.POST)
        if form.is_valid():
            watchers = form.cleaned_data['watchers']
            old_watchers = list(ticket.watchers.values_list('id', 'username'))
            ticket.watchers.set(watchers)
            new_watchers = list(ticket.watchers.values_list('id', 'username'))

            if sorted(old_watchers) != sorted(new_watchers):
                log_ticket_activity(
                    ticket=ticket,
                    user=request.user,
                    action_type='updated',
                    field_changed='watchers',
                    old_value={'watchers': old_watchers},
                    new_value={'watchers': new_watchers},
                    ip_address=request.META.get('REMOTE_ADDR')
                )

            messages.success(request, 'Watchers updated successfully.')
        else:
            messages.error(request, 'Unable to update watchers. Please check the selection.')

    return redirect('ticketing:ticket_detail', pk=pk)


@login_required
def update_scheduled_times(request, pk):
    """Update ticket scheduled start and end times."""
    access_check = check_ticketing_access(request.user)
    if access_check:
        return access_check

    ticket = get_object_or_404(Ticket, pk=pk, is_active=True)
    
    # Check if user can edit this ticket
    if not (can_user_edit_ticket(request.user, ticket) or 
            ticket.assigned_to == request.user or 
            ticket.watchers.filter(id=request.user.id).exists()):
        messages.error(request, "You don't have permission to update scheduled times for this ticket.")
        return redirect('ticketing:ticket_detail', pk=pk)

    if request.method == 'POST':
        scheduled_start_time = request.POST.get('scheduled_start_time', '').strip()
        scheduled_end_time = request.POST.get('scheduled_end_time', '').strip()
        
        # Get old values from metadata
        old_metadata = ticket.metadata.copy() if ticket.metadata else {}
        old_start = old_metadata.get('scheduled_start_time', '')
        old_end = old_metadata.get('scheduled_end_time', '')
        
        # Update metadata
        if not ticket.metadata:
            ticket.metadata = {}
        
        # Set or clear scheduled times
        if scheduled_start_time:
            ticket.metadata['scheduled_start_time'] = scheduled_start_time
        elif 'scheduled_start_time' in ticket.metadata:
            del ticket.metadata['scheduled_start_time']
            
        if scheduled_end_time:
            ticket.metadata['scheduled_end_time'] = scheduled_end_time
        elif 'scheduled_end_time' in ticket.metadata:
            del ticket.metadata['scheduled_end_time']
        
        ticket.save()
        
        # Log activity if values changed
        if (old_start != scheduled_start_time or old_end != scheduled_end_time):
            log_ticket_activity(
                ticket=ticket,
                user=request.user,
                action_type='updated',
                field_changed='scheduled_times',
                old_value={
                    'scheduled_start_time': old_start,
                    'scheduled_end_time': old_end
                },
                new_value={
                    'scheduled_start_time': scheduled_start_time,
                    'scheduled_end_time': scheduled_end_time
                },
                notes=f"Scheduled times updated: Start: {scheduled_start_time or 'None'}, End: {scheduled_end_time or 'None'}",
                ip_address=request.META.get('REMOTE_ADDR')
            )
            messages.success(request, 'Scheduled times updated successfully.')
        else:
            messages.info(request, 'No changes to scheduled times.')

    return redirect('ticketing:ticket_detail', pk=pk)


def update_analytics(request, pk):
    """Update ticket breakdown and analytics details."""
    access_check = check_ticketing_access(request.user)
    if access_check:
        return access_check

    ticket = get_object_or_404(Ticket, pk=pk, is_active=True)
    
    # Check if user can edit this ticket
    if not (can_user_edit_ticket(request.user, ticket) or 
            ticket.assigned_to == request.user or 
            ticket.watchers.filter(id=request.user.id).exists()):
        messages.error(request, "You don't have permission to update analytics for this ticket.")
        return redirect('ticketing:ticket_detail', pk=pk)

    if request.method == 'POST':
        # Get old values from metadata
        old_metadata = ticket.metadata.copy() if ticket.metadata else {}
        
        # Update metadata
        if not ticket.metadata:
            ticket.metadata = {}
        
        # Fields to update
        analytics_fields = [
            'breakdown_start', 'breakdown_end', 'downtime_hours',
            'root_cause', 'sub_cause', 'severity', 'loss_mwh',
            'revenue_loss', 'criticality', 'material_cost',
            'labour_cost', 'warranty_status'
        ]
        
        old_values = {}
        new_values = {}
        has_changes = False
        
        for field in analytics_fields:
            old_value = old_metadata.get(field, '')
            new_value = request.POST.get(field, '').strip()
            
            old_values[field] = old_value
            new_values[field] = new_value
            
            if old_value != new_value:
                has_changes = True
                if new_value:
                    ticket.metadata[field] = new_value
                elif field in ticket.metadata:
                    del ticket.metadata[field]
        
        # Handle file uploads if any
        if 'attachment' in request.FILES:
            files = request.FILES.getlist('attachment')
            if files:
                for file in files:
                    attachment = TicketAttachment(
                        ticket=ticket,
                        uploaded_by=request.user,
                        file=file,
                        file_name=file.name,
                        file_size=file.size,
                        file_type=file.content_type or 'application/octet-stream'
                    )
                    attachment.save()
                    
                    # Log activity for each file
                    log_ticket_activity(
                        ticket=ticket,
                        user=request.user,
                        action_type='attachment_added',
                        notes=f'File uploaded via analytics form: {file.name}',
                        ip_address=request.META.get('REMOTE_ADDR')
                    )
        
        if has_changes:
            ticket.save()
            
            # Log activity
            log_ticket_activity(
                ticket=ticket,
                user=request.user,
                action_type='updated',
                field_changed='analytics_details',
                old_value=old_values,
                new_value=new_values,
                notes="Breakdown & Analytics details updated",
                ip_address=request.META.get('REMOTE_ADDR')
            )
            messages.success(request, 'Analytics details updated successfully.')
        else:
            messages.info(request, 'No changes to analytics details.')

    return redirect('ticketing:ticket_detail', pk=pk)
