"""
ViewSet for KPI endpoints (React app).
Reuses existing logic from main.services.kpi_service
"""

from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from shared_app.permissions.base_permissions import HasFeaturePermission
from shared_app.utils.helpers import parse_list_query_param
from shared_app.utils.exceptions import ValidationError
from ..serializers.kpi_serializers import (
    KPIMetricsResponseSerializer,
    KPISummarySerializer
)
# Import existing service - don't duplicate logic!
# Lazy import to avoid circular import issues


class HasKPIAccess(HasFeaturePermission):
    """Permission class for KPI Dashboard access"""
    required_feature = 'kpi_dashboard'


class KPIViewSet(viewsets.ViewSet):
    """
    ViewSet for KPI endpoints (React app)
    GET /api/v2/main/kpi/metrics/
    GET /api/v2/main/kpi/summary/
    """
    permission_classes = [IsAuthenticated, HasKPIAccess]
    
    @action(detail=False, methods=['get'], url_path='metrics')
    def metrics(self, request):
        """
        Get KPI metrics for React app
        GET /api/v2/main/kpi/metrics/
        
        Query Parameters:
        - date: Optional date filter (YYYY-MM-DD)
        - asset_codes: Comma-separated list of asset codes
        - countries: Comma-separated list of countries
        - portfolios: Comma-separated list of portfolios
        """
        try:
            # Parse query parameters using shared utilities
            filters = {
                'date': request.query_params.get('date'),
                'asset_codes': parse_list_query_param(request, 'asset_codes'),
                'countries': parse_list_query_param(request, 'countries'),
                'portfolios': parse_list_query_param(request, 'portfolios'),
            }
            
            # Reuse existing service - don't duplicate!
            # Lazy import to avoid circular import
            from main.services.kpi_service import KPIService
            service = KPIService(request)
            entries = service.get_realtime_entries(filters)
            
            # Serialize response
            serializer = KPIMetricsResponseSerializer({
                'count': len(entries),
                'results': entries,
            })
            
            return Response(serializer.data, status=status.HTTP_200_OK)
            
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=False, methods=['get'], url_path='summary')
    def summary(self, request):
        """
        Get KPI summary for React app
        GET /api/v2/main/kpi/summary/
        """
        try:
            # Reuse existing service
            # Lazy import to avoid circular import
            from main.services.kpi_service import KPIService
            service = KPIService(request)
            summary = service.get_summary()
            
            # Serialize response
            serializer = KPISummarySerializer(summary)
            return Response(serializer.data, status=status.HTTP_200_OK)
            
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

