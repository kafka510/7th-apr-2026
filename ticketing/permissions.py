"""
Permission utilities for the teckting app
"""
from functools import wraps
from django.http import HttpResponseForbidden, JsonResponse
from django.shortcuts import get_object_or_404
from .models import Ticket
from .utils import can_user_edit_ticket, can_user_assign_ticket, can_user_close_ticket


def can_edit_ticket(view_func):
    """Decorator to check if user can edit ticket"""
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        ticket = get_object_or_404(Ticket, pk=kwargs.get('pk') or kwargs.get('ticket_id'))
        
        if not can_user_edit_ticket(request.user, ticket):
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'error': "You don't have permission to edit this ticket."
                }, status=403)
            return HttpResponseForbidden("You don't have permission to edit this ticket.")
        
        return view_func(request, *args, **kwargs)
    return _wrapped_view


def can_assign_ticket(view_func):
    """Decorator to check if user can assign tickets"""
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if not can_user_assign_ticket(request.user):
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'error': "You don't have permission to assign tickets."
                }, status=403)
            return HttpResponseForbidden("You don't have permission to assign tickets.")
        
        return view_func(request, *args, **kwargs)
    return _wrapped_view


def can_close_ticket(view_func):
    """Decorator to check if user can close ticket"""
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        ticket = get_object_or_404(Ticket, pk=kwargs.get('pk') or kwargs.get('ticket_id'))
        
        if not can_user_close_ticket(request.user, ticket):
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'error': "You don't have permission to close this ticket."
                }, status=403)
            return HttpResponseForbidden("You don't have permission to close this ticket.")
        
        return view_func(request, *args, **kwargs)
    return _wrapped_view

