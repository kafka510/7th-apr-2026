"""
Shared permissions module.
"""

from .permissions import (
    user_has_feature,
    user_has_capability,
    user_has_app_access,
    get_role_definition,
    get_all_features,
    list_all_capabilities,
    invalidate_permissions_cache,
)

# Import base permissions only if rest_framework is available
try:
    from .base_permissions import (
        HasFeaturePermission,
        HasCapabilityPermission,
        HasAppAccess,
    )
    __all__ = [
        'user_has_feature',
        'user_has_capability',
        'user_has_app_access',
        'get_role_definition',
        'get_all_features',
        'list_all_capabilities',
        'invalidate_permissions_cache',
        'HasFeaturePermission',
        'HasCapabilityPermission',
        'HasAppAccess',
    ]
except ImportError:
    # rest_framework not available, skip DRF permission classes
    __all__ = [
        'user_has_feature',
        'user_has_capability',
        'user_has_app_access',
        'get_role_definition',
        'get_all_features',
        'list_all_capabilities',
        'invalidate_permissions_cache',
    ]

