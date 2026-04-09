"""
Shared permission-related utility functions
"""
from ...models import UserProfile
from main.permissions import user_has_capability


def get_user_accessible_sites_debug(request):
    """
    Debug version to see what's happening with user access
    """
    try:
        user_profile = UserProfile.objects.get(user=request.user)
        print(f"Debug - User {request.user.username} has profile with role: {user_profile.role}")
        
        if user_has_capability(request.user, 'ticketing.view_all_sites'):
            print("Debug - User is admin, returning all sites")
            from ...models import AssetList
            return AssetList.objects.all()
        
        accessible_sites = user_profile.get_accessible_sites()
        print(f"Debug - User has access to {accessible_sites.count()} sites")
        
        return accessible_sites
        
    except UserProfile.DoesNotExist:
        print(f"Debug - No UserProfile found for user {request.user.username}")
        from ...models import AssetList
        return AssetList.objects.none()


def check_user_site_access(request, asset_code):
    """
    Check if a user has access to a specific site/asset
    """
    accessible_sites = get_user_accessible_sites_debug(request)
    
    if accessible_sites.filter(asset_code=asset_code).exists():
        return True
    
    # Also check by asset_number if provided
    if accessible_sites.filter(asset_number=asset_code).exists():
        return True
    
    return False
