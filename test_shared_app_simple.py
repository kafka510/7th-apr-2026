"""
Simple test script to verify shared_app imports work.
Run this with: python test_shared_app_simple.py
"""

import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'web_app.settings')
django.setup()

def test_imports():
    """Test that all imports work"""
    print("Testing shared_app imports...")
    
    try:
        # Test permissions imports
        print("\n1. Testing permissions imports...")
        from shared_app.permissions.permissions import (
            user_has_feature,
            user_has_capability,
            user_has_app_access,
            get_all_features,
            list_all_capabilities,
        )
        print("   ✅ Permissions imported successfully")
        
        # Test base permissions (may fail if rest_framework not installed)
        print("\n2. Testing base permissions imports...")
        try:
            from shared_app.permissions.base_permissions import (
                HasFeaturePermission,
                HasCapabilityPermission,
                HasAppAccess,
            )
            print("   ✅ Base permissions imported successfully")
        except ImportError as e:
            print(f"   ⚠️  Base permissions not available (rest_framework may not be installed): {e}")
        
        # Test services
        print("\n3. Testing services imports...")
        from shared_app.services.asset_service import AssetService
        from shared_app.services.user_service import UserService
        print("   ✅ Services imported successfully")
        
        # Test utils
        print("\n4. Testing utils imports...")
        from shared_app.utils.exceptions import APIException, AssetNotFoundError
        from shared_app.utils.helpers import parse_list_query_param, format_currency
        from shared_app.utils.validators import validate_asset_code
        print("   ✅ Utils imported successfully")
        
        # Test serializers (may fail if rest_framework not installed)
        print("\n5. Testing serializers imports...")
        try:
            from shared_app.serializers.base_serializers import TimestampedSerializer
            print("   ✅ Serializers imported successfully")
        except ImportError as e:
            print(f"   ⚠️  Serializers not available (rest_framework may not be installed): {e}")
        
        # Test backward compatibility
        print("\n6. Testing backward compatibility (main.permissions)...")
        from main.permissions import user_has_feature as main_user_has_feature
        print("   ✅ Backward compatibility works")
        
        print("\n" + "="*50)
        print("✅ All critical imports working!")
        print("="*50)
        return True
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_functionality():
    """Test basic functionality"""
    print("\n\nTesting functionality...")
    
    try:
        from shared_app.permissions.permissions import get_all_features
        from shared_app.services.asset_service import AssetService
        from shared_app.utils.helpers import format_currency
        from shared_app.utils.validators import validate_asset_code
        
        # Test get_all_features
        features = get_all_features()
        print(f"   ✅ get_all_features() returned {len(features)} features")
        
        # Test AssetService
        result = AssetService.validate_asset_code('ASSET001')
        print(f"   ✅ AssetService.validate_asset_code('ASSET001') = {result}")
        
        # Test format_currency
        result = format_currency(1234.56)
        print(f"   ✅ format_currency(1234.56) = {result}")
        
        # Test validate_asset_code
        result = validate_asset_code('ABC')
        print(f"   ✅ validate_asset_code('ABC') = {result}")
        
        print("\n" + "="*50)
        print("✅ All functionality tests passed!")
        print("="*50)
        return True
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == '__main__':
    print("="*50)
    print("Shared App Test Script")
    print("="*50)
    
    success = True
    success &= test_imports()
    success &= test_functionality()
    
    if success:
        print("\n🎉 All tests passed!")
        sys.exit(0)
    else:
        print("\n❌ Some tests failed")
        sys.exit(1)

