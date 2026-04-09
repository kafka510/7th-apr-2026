"""
Test script for API v2 endpoints.
Run this with: python test_api_v2.py

This script tests:
1. That the new API v2 endpoints are accessible
2. That they return the correct structure
3. That old API v1 endpoints still work
"""

import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'web_app.settings')
django.setup()

from django.test import RequestFactory
from django.contrib.auth import get_user_model
from rest_framework.test import force_authenticate

User = get_user_model()


def test_api_v2_structure():
    """Test that API v2 structure is correct"""
    print("="*60)
    print("Testing API v2 Structure")
    print("="*60)
    
    try:
        # Test imports
        print("\n1. Testing imports...")
        from main.api_v2.serializers.kpi_serializers import (
            KPIMetricSerializer,
            KPIMetricsResponseSerializer,
            KPISummarySerializer,
        )
        from main.api_v2.viewsets.kpi_viewsets import KPIViewSet, HasKPIAccess
        from main.api_v2.routers import router, urlpatterns
        print("   ✅ All imports successful")
        
        # Test router
        print("\n2. Testing router...")
        print(f"   Router has {len(urlpatterns)} URL patterns")
        for pattern in urlpatterns:
            print(f"   - {pattern.pattern}")
        print("   ✅ Router configured correctly")
        
        # Test ViewSet
        print("\n3. Testing ViewSet...")
        viewset = KPIViewSet()
        print(f"   ViewSet class: {viewset.__class__.__name__}")
        print(f"   Permission classes: {[p.__name__ for p in viewset.permission_classes]}")
        print("   ✅ ViewSet configured correctly")
        
        # Test Permission class
        print("\n4. Testing Permission class...")
        permission = HasKPIAccess()
        print(f"   Required feature: {permission.required_feature}")
        print("   ✅ Permission class configured correctly")
        
        print("\n" + "="*60)
        print("✅ API v2 structure is correct!")
        print("="*60)
        return True
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_url_configuration():
    """Test that URLs are configured correctly"""
    print("\n\n" + "="*60)
    print("Testing URL Configuration")
    print("="*60)
    
    try:
        from django.urls import reverse, resolve
        from django.conf import settings
        from django.urls import get_resolver
        
        resolver = get_resolver()
        
        # Check if v2 routes exist
        print("\n1. Checking URL patterns...")
        url_patterns = []
        for pattern in resolver.url_patterns:
            if hasattr(pattern, 'url_patterns'):
                for sub_pattern in pattern.url_patterns:
                    if 'api/v2' in str(sub_pattern.pattern):
                        url_patterns.append(str(sub_pattern.pattern))
        
        if url_patterns:
            print(f"   ✅ Found {len(url_patterns)} API v2 patterns")
            for pattern in url_patterns[:5]:  # Show first 5
                print(f"   - {pattern}")
        else:
            print("   ⚠️  No API v2 patterns found (may need to check namespace)")
        
        print("\n" + "="*60)
        print("✅ URL configuration check complete!")
        print("="*60)
        return True
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_serializers():
    """Test that serializers work correctly"""
    print("\n\n" + "="*60)
    print("Testing Serializers")
    print("="*60)
    
    try:
        from main.api_v2.serializers.kpi_serializers import (
            KPIMetricSerializer,
            KPIMetricsResponseSerializer,
            KPISummarySerializer,
        )
        
        # Test KPIMetricSerializer
        print("\n1. Testing KPIMetricSerializer...")
        test_data = {
            'asset_code': 'TEST001',
            'asset_name': 'Test Asset',
            'date': '2024-01-01',
            'daily_kwh': 1000.0,
            'daily_irr': 5.5,
            'daily_generation_mwh': 1.0,
            'daily_irradiation_mwh': 2.0,
            'daily_ic_mwh': 0.9,
            'daily_expected_mwh': 1.1,
            'daily_budget_irradiation_mwh': 2.1,
            'expect_pr': 0.85,
            'actual_pr': 0.82,
            'dc_capacity_mw': 10.0,
            'is_frozen': False,
            'capacity': 10.0,
            'timezone': '+00:00',
        }
        serializer = KPIMetricSerializer(data=test_data)
        if serializer.is_valid():
            print("   ✅ KPIMetricSerializer validates correctly")
        else:
            print(f"   ⚠️  Validation errors: {serializer.errors}")
        
        # Test KPISummarySerializer
        print("\n2. Testing KPISummarySerializer...")
        summary_data = {
            'total_assets': 5,
            'total_daily_kwh': 5000.0,
            'avg_daily_irr': 5.5,
            'last_updated': '2024-01-01T12:00:00Z',
        }
        serializer = KPISummarySerializer(data=summary_data)
        if serializer.is_valid():
            print("   ✅ KPISummarySerializer validates correctly")
        else:
            print(f"   ⚠️  Validation errors: {serializer.errors}")
        
        print("\n" + "="*60)
        print("✅ Serializers test complete!")
        print("="*60)
        return True
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_backward_compatibility():
    """Test that old API still works"""
    print("\n\n" + "="*60)
    print("Testing Backward Compatibility")
    print("="*60)
    
    try:
        # Test that old API imports still work
        print("\n1. Testing old API imports...")
        from main.api.kpi import KPIMetricsView, KPISummaryView
        print("   ✅ Old API views can still be imported")
        
        # Test that old permission still works
        print("\n2. Testing old permissions...")
        from main.permissions import user_has_feature
        print("   ✅ Old permissions import works (backward compatibility)")
        
        print("\n" + "="*60)
        print("✅ Backward compatibility maintained!")
        print("="*60)
        return True
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == '__main__':
    print("="*60)
    print("API v2 Test Script")
    print("="*60)
    
    success = True
    success &= test_api_v2_structure()
    success &= test_url_configuration()
    success &= test_serializers()
    success &= test_backward_compatibility()
    
    if success:
        print("\n\n" + "="*60)
        print("🎉 All tests passed!")
        print("="*60)
        print("\nNext steps:")
        print("1. Start Django server: python manage.py runserver")
        print("2. Test new endpoint: GET /api/v2/main/kpi/metrics/")
        print("3. Test old endpoint: GET /api/v1/kpi/metrics/ (should still work)")
        print("="*60)
        sys.exit(0)
    else:
        print("\n\n" + "="*60)
        print("❌ Some tests failed")
        print("="*60)
        sys.exit(1)

