"""
ViewSet for Site Onboarding endpoints (React app).
Reuses existing logic from main.views.site_onboarding_views
"""
import json
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.http import JsonResponse

from shared_app.permissions.base_permissions import HasFeaturePermission
from shared_app.utils.helpers import parse_list_query_param
from ..serializers.site_onboarding_serializers import (
    AssetListResponseSerializer,
    DeviceListResponseSerializer,
    DeviceMappingResponseSerializer,
    BudgetValuesResponseSerializer,
    ICBudgetResponseSerializer,
    ApiResponseSerializer,
    UniqueApiNamesResponseSerializer,
)


class HasSiteOnboardingAccess(HasFeaturePermission):
    required_feature = 'site_onboarding'


class SiteOnboardingViewSet(viewsets.ViewSet):
    permission_classes = [IsAuthenticated, HasSiteOnboardingAccess]

    # Asset List endpoints
    @action(detail=False, methods=['get'], url_path='asset-list')
    def asset_list(self, request):
        """Get asset list with pagination"""
        try:
            from main.views.site_onboarding_views import api_asset_list_data
            response = api_asset_list_data(request)
            if isinstance(response, JsonResponse):
                data = json.loads(response.content.decode('utf-8'))
                return Response(data, status=response.status_code)
            return response
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=False, methods=['post'], url_path='asset-list/create')
    def create_asset_list(self, request):
        """Create asset list entry"""
        try:
            from main.views.site_onboarding_views import api_create_asset_list
            response = api_create_asset_list(request)
            if isinstance(response, JsonResponse):
                data = json.loads(response.content.decode('utf-8'))
                return Response(data, status=response.status_code)
            return response
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=False, methods=['post'], url_path='asset-list/update')
    def update_asset_list(self, request):
        """Update asset list entry"""
        try:
            from main.views.site_onboarding_views import api_update_asset_list
            response = api_update_asset_list(request)
            if isinstance(response, JsonResponse):
                data = json.loads(response.content.decode('utf-8'))
                return Response(data, status=response.status_code)
            return response
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=False, methods=['delete'], url_path='asset-list/delete')
    def delete_asset_list(self, request):
        """Delete asset list entry"""
        try:
            asset_code = request.query_params.get('asset_code')
            if not asset_code:
                return Response({'error': 'asset_code parameter is required'}, status=status.HTTP_400_BAD_REQUEST)
            
            from main.views.site_onboarding_views import api_delete_asset_list
            # Create a mock request with the asset_code in the URL kwargs
            class MockRequest:
                def __init__(self, original_request, asset_code):
                    self.user = original_request.user
                    self.method = 'DELETE'
                    self.GET = original_request.GET
                    self.POST = original_request.POST
                    self.body = original_request.body
            from django.test import RequestFactory
            factory = RequestFactory()
            mock_request = factory.delete(f'/api/site-onboarding/asset-list/delete/{asset_code}/')
            mock_request.user = request.user
            
            response = api_delete_asset_list(mock_request, asset_code)
            if isinstance(response, JsonResponse):
                data = json.loads(response.content.decode('utf-8'))
                return Response(data, status=response.status_code)
            return response
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    # Device List endpoints
    @action(detail=False, methods=['get'], url_path='device-list')
    def device_list(self, request):
        """Get device list with pagination"""
        try:
            from main.views.site_onboarding_views import api_device_list_data
            response = api_device_list_data(request)
            if isinstance(response, JsonResponse):
                data = json.loads(response.content.decode('utf-8'))
                return Response(data, status=response.status_code)
            return response
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=False, methods=['post'], url_path='device-list/create')
    def create_device_list(self, request):
        """Create device list entry"""
        try:
            from main.views.site_onboarding_views import api_create_device_list
            response = api_create_device_list(request)
            if isinstance(response, JsonResponse):
                data = json.loads(response.content.decode('utf-8'))
                return Response(data, status=response.status_code)
            return response
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=False, methods=['post'], url_path='device-list/update')
    def update_device_list(self, request):
        """Update device list entry"""
        try:
            from main.views.site_onboarding_views import api_update_device_list
            response = api_update_device_list(request)
            if isinstance(response, JsonResponse):
                data = json.loads(response.content.decode('utf-8'))
                return Response(data, status=response.status_code)
            return response
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=False, methods=['delete'], url_path='device-list/delete')
    def delete_device_list(self, request):
        """Delete device list entry"""
        try:
            device_id = request.query_params.get('device_id')
            if not device_id:
                return Response({'error': 'device_id parameter is required'}, status=status.HTTP_400_BAD_REQUEST)
            
            from main.views.site_onboarding_views import api_delete_device_list
            from django.test import RequestFactory
            factory = RequestFactory()
            mock_request = factory.delete(f'/api/site-onboarding/device-list/delete/{device_id}/')
            mock_request.user = request.user
            
            response = api_delete_device_list(mock_request, device_id)
            if isinstance(response, JsonResponse):
                data = json.loads(response.content.decode('utf-8'))
                return Response(data, status=response.status_code)
            return response
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    # Device Mapping endpoints
    @action(detail=False, methods=['get'], url_path='device-mapping')
    def device_mapping(self, request):
        """Get device mapping with pagination"""
        try:
            from main.views.site_onboarding_views import api_device_mapping_data
            response = api_device_mapping_data(request)
            if isinstance(response, JsonResponse):
                data = json.loads(response.content.decode('utf-8'))
                return Response(data, status=response.status_code)
            return response
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=False, methods=['post'], url_path='device-mapping/create')
    def create_device_mapping(self, request):
        """Create device mapping entry"""
        try:
            from main.views.site_onboarding_views import api_create_device_mapping
            response = api_create_device_mapping(request)
            if isinstance(response, JsonResponse):
                data = json.loads(response.content.decode('utf-8'))
                return Response(data, status=response.status_code)
            return response
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=False, methods=['post'], url_path='device-mapping/update')
    def update_device_mapping(self, request):
        """Update device mapping entry"""
        try:
            from main.views.site_onboarding_views import api_update_device_mapping
            response = api_update_device_mapping(request)
            if isinstance(response, JsonResponse):
                data = json.loads(response.content.decode('utf-8'))
                return Response(data, status=response.status_code)
            return response
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=False, methods=['delete'], url_path='device-mapping/delete')
    def delete_device_mapping(self, request):
        """Delete device mapping entry"""
        try:
            mapping_id = request.query_params.get('mapping_id')
            if not mapping_id:
                return Response({'error': 'mapping_id parameter is required'}, status=status.HTTP_400_BAD_REQUEST)
            
            from main.views.site_onboarding_views import api_delete_device_mapping
            from django.test import RequestFactory
            factory = RequestFactory()
            mock_request = factory.delete(f'/api/site-onboarding/device-mapping/delete/{mapping_id}/')
            mock_request.user = request.user
            
            response = api_delete_device_mapping(mock_request, int(mapping_id))
            if isinstance(response, JsonResponse):
                data = json.loads(response.content.decode('utf-8'))
                return Response(data, status=response.status_code)
            return response
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    # Budget Values endpoints
    @action(detail=False, methods=['get'], url_path='budget-values')
    def budget_values(self, request):
        """Get budget values with pagination"""
        try:
            from main.views.site_onboarding_views import api_budget_values_data
            response = api_budget_values_data(request)
            if isinstance(response, JsonResponse):
                data = json.loads(response.content.decode('utf-8'))
                return Response(data, status=response.status_code)
            return response
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=False, methods=['post'], url_path='budget-values/create')
    def create_budget_values(self, request):
        """Create budget values entry"""
        try:
            from main.views.site_onboarding_views import api_create_budget_values
            response = api_create_budget_values(request)
            if isinstance(response, JsonResponse):
                data = json.loads(response.content.decode('utf-8'))
                return Response(data, status=response.status_code)
            return response
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=False, methods=['post'], url_path='budget-values/update')
    def update_budget_values(self, request):
        """Update budget values entry"""
        try:
            from main.views.site_onboarding_views import api_update_budget_values
            response = api_update_budget_values(request)
            if isinstance(response, JsonResponse):
                data = json.loads(response.content.decode('utf-8'))
                return Response(data, status=response.status_code)
            return response
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=False, methods=['delete'], url_path='budget-values/delete')
    def delete_budget_values(self, request):
        """Delete budget values entry"""
        try:
            budget_id = request.query_params.get('budget_id')
            if not budget_id:
                return Response({'error': 'budget_id parameter is required'}, status=status.HTTP_400_BAD_REQUEST)
            
            from main.views.site_onboarding_views import api_delete_budget_values
            from django.test import RequestFactory
            factory = RequestFactory()
            mock_request = factory.delete(f'/api/site-onboarding/budget-values/delete/{budget_id}/')
            mock_request.user = request.user
            
            response = api_delete_budget_values(mock_request, int(budget_id))
            if isinstance(response, JsonResponse):
                data = json.loads(response.content.decode('utf-8'))
                return Response(data, status=response.status_code)
            return response
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    # IC Budget endpoints
    @action(detail=False, methods=['get'], url_path='ic-budget')
    def ic_budget(self, request):
        """Get IC budget with pagination"""
        try:
            from main.views.site_onboarding_views import api_ic_budget_data
            response = api_ic_budget_data(request)
            if isinstance(response, JsonResponse):
                data = json.loads(response.content.decode('utf-8'))
                return Response(data, status=response.status_code)
            return response
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=False, methods=['post'], url_path='ic-budget/create')
    def create_ic_budget(self, request):
        """Create IC budget entry"""
        try:
            from main.views.site_onboarding_views import api_create_ic_budget
            response = api_create_ic_budget(request)
            if isinstance(response, JsonResponse):
                data = json.loads(response.content.decode('utf-8'))
                return Response(data, status=response.status_code)
            return response
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=False, methods=['post'], url_path='ic-budget/update')
    def update_ic_budget(self, request):
        """Update IC budget entry"""
        try:
            from main.views.site_onboarding_views import api_update_ic_budget
            response = api_update_ic_budget(request)
            if isinstance(response, JsonResponse):
                data = json.loads(response.content.decode('utf-8'))
                return Response(data, status=response.status_code)
            return response
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=False, methods=['delete'], url_path='ic-budget/delete')
    def delete_ic_budget(self, request):
        """Delete IC budget entry"""
        try:
            ic_budget_id = request.query_params.get('ic_budget_id')
            if not ic_budget_id:
                return Response({'error': 'ic_budget_id parameter is required'}, status=status.HTTP_400_BAD_REQUEST)
            
            from main.views.site_onboarding_views import api_delete_ic_budget
            from django.test import RequestFactory
            factory = RequestFactory()
            mock_request = factory.delete(f'/api/site-onboarding/ic-budget/delete/{ic_budget_id}/')
            mock_request.user = request.user
            
            response = api_delete_ic_budget(mock_request, int(ic_budget_id))
            if isinstance(response, JsonResponse):
                data = json.loads(response.content.decode('utf-8'))
                return Response(data, status=response.status_code)
            return response
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    # Utility endpoints
    @action(detail=False, methods=['get'], url_path='api-names')
    def api_names(self, request):
        """Get unique API names"""
        try:
            from main.views.site_onboarding_views import api_get_unique_api_names
            response = api_get_unique_api_names(request)
            if isinstance(response, JsonResponse):
                data = json.loads(response.content.decode('utf-8'))
                return Response(data, status=response.status_code)
            return response
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

