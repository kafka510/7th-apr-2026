"""
Base permission classes for DRF ViewSets.
"""

from rest_framework.permissions import BasePermission
from shared_app.permissions.permissions import (
    user_has_feature,
    user_has_capability,
    user_has_app_access
)


class HasFeaturePermission(BasePermission):
    """
    Base permission class for feature-based access control.
    
    Usage:
        class HasKPIAccess(HasFeaturePermission):
            required_feature = 'kpi_dashboard'
    """
    
    required_feature = None
    message = 'You do not have permission to access this resource.'
    
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        
        if self.required_feature:
            return user_has_feature(request.user, self.required_feature)
        
        return True


class HasCapabilityPermission(BasePermission):
    """
    Base permission class for capability-based access control.
    
    Usage:
        class HasTicketingManage(HasCapabilityPermission):
            required_capability = 'ticketing.manage'
    """
    
    required_capability = None
    message = 'You do not have the required capability.'
    
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        
        if self.required_capability:
            return user_has_capability(request.user, self.required_capability)
        
        return True


class HasAppAccess(BasePermission):
    """
    Permission class for app-level access control.
    
    Usage:
        class HasBillingAccess(HasAppAccess):
            required_app = 'billing'
    """
    
    required_app = None
    message = 'You do not have access to this app.'
    
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        
        if self.required_app:
            return user_has_app_access(request.user, self.required_app)
        
        return True

