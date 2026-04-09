"""
Service for user-related operations across apps.
"""


class UserService:
    """Service for user operations"""
    
    @staticmethod
    def has_app_access(user, app_name: str) -> bool:
        """Check if user has access to app"""
        from shared_app.permissions.permissions import user_has_app_access
        return user_has_app_access(user, app_name)
    
    @staticmethod
    def get_user_permissions(user):
        """Get all permissions for user across apps"""
        from shared_app.permissions.permissions import (
            get_role_definition,
            get_all_features
        )
        
        profile = getattr(user, "userprofile", None)
        if not profile:
            return {}
        
        role = getattr(profile, "role", None)
        if not role:
            return {}
        
        role_def = get_role_definition(role)
        features = role_def.get("features", ())
        
        all_features = get_all_features()
        user_features = {}
        
        if features and features[0] == "__all__":
            user_features = all_features
        else:
            for feature in features:
                if feature in all_features:
                    user_features[feature] = all_features[feature]
        
        return user_features

