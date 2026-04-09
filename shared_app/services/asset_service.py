"""
Service for asset-related operations across apps.
Used by React app APIs.
"""


class AssetService:
    """Service for asset operations"""
    
    @staticmethod
    def get_asset(asset_code: str):
        """Get asset by code"""
        from main.models import AssetList
        try:
            return AssetList.objects.get(asset_code=asset_code)
        except AssetList.DoesNotExist:
            return None
    
    @staticmethod
    def get_assets_for_user(user):
        """Get assets accessible to user based on permissions"""
        from main.models import AssetList
        
        if user.is_superuser:
            return AssetList.objects.all()
        
        # Apply user-specific filtering based on permissions
        # TODO: Implement based on your permission system
        return AssetList.objects.all()
    
    @staticmethod
    def validate_asset_code(asset_code: str) -> bool:
        """Validate asset code format"""
        if not asset_code or len(asset_code) < 3:
            return False
        return True

