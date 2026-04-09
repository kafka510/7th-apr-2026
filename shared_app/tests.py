"""
Tests for shared_app functionality.
"""

from django.test import TestCase
from django.contrib.auth import get_user_model

User = get_user_model()


class SharedAppImportsTestCase(TestCase):
    """Test that all imports work correctly"""
    
    def test_permissions_imports(self):
        """Test that permissions can be imported"""
        from shared_app.permissions.permissions import (
            user_has_feature,
            user_has_capability,
            user_has_app_access,
            get_role_definition,
            get_all_features,
            list_all_capabilities,
        )
        self.assertTrue(callable(user_has_feature))
        self.assertTrue(callable(user_has_capability))
        self.assertTrue(callable(user_has_app_access))
        self.assertTrue(callable(get_role_definition))
        self.assertTrue(callable(get_all_features))
        self.assertTrue(callable(list_all_capabilities))
    
    def test_base_permissions_imports(self):
        """Test that base permission classes can be imported"""
        from shared_app.permissions.base_permissions import (
            HasFeaturePermission,
            HasCapabilityPermission,
            HasAppAccess,
        )
        self.assertTrue(issubclass(HasFeaturePermission, type))
        self.assertTrue(issubclass(HasCapabilityPermission, type))
        self.assertTrue(issubclass(HasAppAccess, type))
    
    def test_services_imports(self):
        """Test that services can be imported"""
        from shared_app.services.asset_service import AssetService
        from shared_app.services.user_service import UserService
        
        self.assertTrue(hasattr(AssetService, 'get_asset'))
        self.assertTrue(hasattr(AssetService, 'get_assets_for_user'))
        self.assertTrue(hasattr(AssetService, 'validate_asset_code'))
        self.assertTrue(hasattr(UserService, 'has_app_access'))
        self.assertTrue(hasattr(UserService, 'get_user_permissions'))
    
    def test_utils_imports(self):
        """Test that utilities can be imported"""
        from shared_app.utils.exceptions import (
            APIException,
            AssetNotFoundError,
            PermissionDeniedError,
            ValidationError,
        )
        from shared_app.utils.helpers import (
            parse_list_query_param,
            parse_query_param,
            format_currency,
            format_percentage,
        )
        from shared_app.utils.validators import (
            validate_asset_code,
            validate_date_format,
        )
        
        # Test exceptions
        self.assertTrue(issubclass(APIException, Exception))
        self.assertTrue(issubclass(AssetNotFoundError, APIException))
        self.assertTrue(issubclass(PermissionDeniedError, APIException))
        self.assertTrue(issubclass(ValidationError, APIException))
        
        # Test helpers are callable
        self.assertTrue(callable(parse_list_query_param))
        self.assertTrue(callable(parse_query_param))
        self.assertTrue(callable(format_currency))
        self.assertTrue(callable(format_percentage))
        
        # Test validators are callable
        self.assertTrue(callable(validate_asset_code))
        self.assertTrue(callable(validate_date_format))
    
    def test_serializers_imports(self):
        """Test that serializers can be imported"""
        from shared_app.serializers.base_serializers import (
            TimestampedSerializer,
            PaginatedResponseSerializer,
            ErrorResponseSerializer,
        )
        
        self.assertTrue(hasattr(TimestampedSerializer, 'Meta') or hasattr(TimestampedSerializer, 'fields'))


class SharedAppFunctionalityTestCase(TestCase):
    """Test that shared app functionality works"""
    
    def setUp(self):
        """Set up test data"""
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
    
    def test_permissions_functions(self):
        """Test that permission functions work"""
        from shared_app.permissions.permissions import (
            user_has_feature,
            user_has_capability,
            user_has_app_access,
            get_all_features,
            list_all_capabilities,
        )
        
        # Test that functions can be called (even if they return False)
        result = user_has_feature(self.user, 'kpi_dashboard')
        self.assertIsInstance(result, bool)
        
        result = user_has_capability(self.user, 'ticketing.manage')
        self.assertIsInstance(result, bool)
        
        result = user_has_app_access(self.user, 'web')
        self.assertIsInstance(result, bool)
        
        # Test that get functions return dictionaries
        features = get_all_features()
        self.assertIsInstance(features, dict)
        
        capabilities = list_all_capabilities()
        self.assertIsInstance(capabilities, (dict, tuple))
    
    def test_asset_service(self):
        """Test AssetService functionality"""
        from shared_app.services.asset_service import AssetService
        
        # Test validate_asset_code
        self.assertTrue(AssetService.validate_asset_code('ASSET001'))
        self.assertFalse(AssetService.validate_asset_code('AB'))
        self.assertFalse(AssetService.validate_asset_code(''))
        self.assertFalse(AssetService.validate_asset_code(None))
    
    def test_user_service(self):
        """Test UserService functionality"""
        from shared_app.services.user_service import UserService
        
        # Test has_app_access returns boolean
        result = UserService.has_app_access(self.user, 'web')
        self.assertIsInstance(result, bool)
        
        # Test get_user_permissions returns dict
        permissions = UserService.get_user_permissions(self.user)
        self.assertIsInstance(permissions, dict)
    
    def test_helpers(self):
        """Test helper functions"""
        from shared_app.utils.helpers import (
            parse_list_query_param,
            parse_query_param,
            format_currency,
            format_percentage,
        )
        from django.http import QueryDict
        
        # Create a mock request with query params
        class MockRequest:
            def __init__(self):
                self.query_params = QueryDict('asset_codes=ASSET1,ASSET2&date=2024-01-01')
        
        request = MockRequest()
        
        # Test parse_list_query_param
        result = parse_list_query_param(request, 'asset_codes')
        self.assertEqual(result, ['ASSET1', 'ASSET2'])
        
        result = parse_list_query_param(request, 'nonexistent')
        self.assertEqual(result, [])
        
        # Test parse_query_param
        result = parse_query_param(request, 'date')
        self.assertEqual(result, '2024-01-01')
        
        result = parse_query_param(request, 'nonexistent', 'default')
        self.assertEqual(result, 'default')
        
        # Test format_currency
        result = format_currency(1234.56)
        self.assertIn('USD', result)
        self.assertIn('1,234.56', result)
        
        # Test format_percentage
        result = format_percentage(45.678)
        self.assertEqual(result, '45.68%')
    
    def test_validators(self):
        """Test validator functions"""
        from shared_app.utils.validators import (
            validate_asset_code,
            validate_date_format,
        )
        
        # Test validate_asset_code
        self.assertTrue(validate_asset_code('ASSET001'))
        self.assertTrue(validate_asset_code('ABC'))
        self.assertFalse(validate_asset_code('AB'))
        self.assertFalse(validate_asset_code(''))
        
        # Test validate_date_format
        self.assertTrue(validate_date_format('2024-01-01', '%Y-%m-%d'))
        self.assertTrue(validate_date_format('01/01/2024', '%m/%d/%Y'))
        self.assertFalse(validate_date_format('invalid', '%Y-%m-%d'))
    
    def test_exceptions(self):
        """Test exception classes"""
        from shared_app.utils.exceptions import (
            APIException,
            AssetNotFoundError,
            PermissionDeniedError,
            ValidationError,
        )
        
        # Test APIException
        exc = APIException('Test error', 400)
        self.assertEqual(exc.message, 'Test error')
        self.assertEqual(exc.status_code, 400)
        
        # Test AssetNotFoundError
        exc = AssetNotFoundError('ASSET001')
        self.assertIn('ASSET001', exc.message)
        self.assertEqual(exc.status_code, 404)
        
        # Test PermissionDeniedError
        exc = PermissionDeniedError()
        self.assertEqual(exc.status_code, 403)
        
        # Test ValidationError
        exc = ValidationError('Invalid input')
        self.assertEqual(exc.message, 'Invalid input')
        self.assertEqual(exc.status_code, 400)


class BackwardCompatibilityTestCase(TestCase):
    """Test backward compatibility with main.permissions"""
    
    def test_main_permissions_import(self):
        """Test that main.permissions still works (backward compatibility)"""
        from main.permissions import (
            user_has_feature,
            user_has_capability,
            user_has_app_access,
        )
        
        # Should be able to import and use
        self.assertTrue(callable(user_has_feature))
        self.assertTrue(callable(user_has_capability))
        self.assertTrue(callable(user_has_app_access))
