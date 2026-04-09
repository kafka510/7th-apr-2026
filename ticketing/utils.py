"""
Utility functions for the teckting app
"""

from main.permissions import user_has_capability
from .models import Ticket, TicketActivity


def log_ticket_activity(ticket, user, action_type, old_value=None, new_value=None,
                       field_changed=None, notes='', ip_address=None):
    """
    Log ticket activity with timestamp and timezone
    
    Args:
        ticket: Ticket instance
        user: User who performed the action
        action_type: Type of action (from TicketActivity.ACTION_CHOICES)
        old_value: Previous value (optional)
        new_value: New value (optional)
        field_changed: Name of field that changed (optional)
        notes: Additional notes (optional)
        ip_address: IP address of user (optional)
    
    Returns:
        TicketActivity instance
    """
    activity = TicketActivity.objects.create(
        ticket=ticket,
        user=user,
        action_type=action_type,
        old_value=old_value,
        new_value=new_value,
        field_changed=field_changed,
        notes=notes,
        ip_address=ip_address
    )
    return activity


def get_accessible_sites_for_user(user):
    """
    Get sites user can access based on RBAC
    
    Args:
        user: User instance
    
    Returns:
        QuerySet of AssetList objects
    """
    from main.models import AssetList, UserProfile
    
    if user.is_superuser or user_has_capability(user, 'ticketing.view_all_sites'):
        return AssetList.objects.all()

    try:
        user_profile = user.userprofile
        return user_profile.get_accessible_sites()
    except UserProfile.DoesNotExist:
        return AssetList.objects.none()


def get_user_display_name(user):
    """
    Get display name for user (first_name last_name or username)
    
    Args:
        user: User instance
    
    Returns:
        str: Display name
    """
    if user.first_name or user.last_name:
        return f"{user.first_name} {user.last_name}".strip()
    return user.username


def can_user_edit_ticket(user, ticket):
    """
    Check if user can edit a ticket
    
    Args:
        user: User instance
        ticket: Ticket instance
    
    Returns:
        bool: True if user can edit
    """
    if not user.is_authenticated:
        return False
    
    # Superuser or users with the explicit capability can edit
    if user.is_superuser or user_has_capability(user, 'ticketing.edit_any'):
        return True
    
    # Creator can edit
    if ticket.created_by == user:
        return True
    
    # Assigned user can edit
    if ticket.assigned_to == user:
        return True
    
    # Watchers can edit
    if ticket.watchers.filter(id=user.id).exists():
        return True
    
    return False


def has_ticketing_access(user):
    """
    Check if user has access to the ticketing system
    
    Args:
        user: User instance
    
    Returns:
        bool: True if user has ticketing access or an explicit capability
    """
    if not user.is_authenticated:
        return False
    
    if user.is_superuser or user_has_capability(user, 'ticketing.access_portal'):
        return True

    try:
        user_profile = getattr(user, 'userprofile', None)
        if user_profile:
            return user_profile.ticketing_access
    except Exception:
        pass
    
    return False


def can_user_assign_ticket(user):
    """
    Check if user can assign tickets
    
    Args:
        user: User instance
    
    Returns:
        bool: True if user can assign
    """
    if not user.is_authenticated:
        return False
    
    if user.is_superuser:
        return True

    return user_has_capability(user, 'ticketing.assign')


def can_user_manage_watchers(user):
    """Check if user can manage ticket watchers."""
    if not user.is_authenticated:
        return False

    if user.is_superuser:
        return True

    return user_has_capability(user, 'ticketing.manage_watchers')


def can_user_close_ticket(user, ticket):
    """
    Check if user can close a ticket
    
    Args:
        user: User instance
        ticket: Ticket instance
    
    Returns:
        bool: True if user can close
    """
    if not user.is_authenticated:
        return False
    
    # Superuser or explicit capability can always close
    if user.is_superuser or user_has_capability(user, 'ticketing.close_any'):
        return True
    
    # Creator can close
    if ticket.created_by == user:
        return True
    
    # Assigned user can close
    if ticket.assigned_to == user:
        return True
    
    return False

