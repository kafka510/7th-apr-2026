from rest_framework.permissions import BasePermission

from ..utils import has_ticketing_access


class HasTicketingAccess(BasePermission):
    """Ensures the authenticated user can access the ticketing system."""

    def has_permission(self, request, view):
        user = getattr(request, "user", None)
        if user is None or not user.is_authenticated:
            return False
        return has_ticketing_access(user)



