"""
ViewSet for Portfolio Map endpoints (React app).
Reuses existing logic from main.api.portfolio_map
"""

import math
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from shared_app.permissions.base_permissions import HasFeaturePermission


class HasPortfolioMapAccess(HasFeaturePermission):
    """Permission class for Portfolio Map access"""
    required_feature = 'portfolio_map'


class PortfolioMapViewSet(viewsets.ViewSet):
    """
    ViewSet for Portfolio Map endpoints (React app)
    GET /api/v2/main/portfolio-map/map-data/
    """
    permission_classes = [IsAuthenticated, HasPortfolioMapAccess]

    def safe_val(self, val, is_numeric=False):
        """Convert None or NaN to None for numeric fields, empty string for text fields"""
        if val is None or (isinstance(val, float) and math.isnan(val)):
            return None if is_numeric else ""
        # If it's a string that's empty or just whitespace, convert to None for numeric fields
        if is_numeric and isinstance(val, str) and (not val.strip() or val.strip() == ''):
            return None
        return val

    def safe_coord(self, val):
        """Safely convert coordinate value to float or None"""
        if val is None:
            return None
        # Handle string values first (including '-' and empty strings)
        if isinstance(val, str):
            val = val.strip()
            if not val or val == '-' or val == '':
                return None
            # Try to convert string to float
            try:
                return float(val)
            except (ValueError, TypeError):
                return None
        # Handle NaN floats
        if isinstance(val, float) and math.isnan(val):
            return None
        # Convert Decimal to float for JSON serialization
        if hasattr(val, '__float__'):
            try:
                return float(val)
            except (ValueError, TypeError):
                return None
        # Try direct conversion
        try:
            return float(val)
        except (ValueError, TypeError):
            return None

    @action(detail=False, methods=['get'], url_path='map-data')
    def map_data(self, request):
        """
        Get portfolio map data for React app
        GET /api/v2/main/portfolio-map/map-data/
        
        Returns map data and yield data for the portfolio map page
        """
        try:
            # Lazy import to avoid circular dependency
            from main.models import YieldData, MapData
            from main.views.shared.utilities import filter_data_by_user_sites

            # Use the filter_data_by_user_sites function for proper access control
            map_data_queryset = filter_data_by_user_sites(MapData.objects.all(), 'asset_no', request)
            yield_data_queryset = filter_data_by_user_sites(YieldData.objects.all(), 'assetno', request)

            # Process map data
            map_data = []
            countries_found = set()
            for record in map_data_queryset:
                country_val = self.safe_val(record.country)
                countries_found.add(country_val)
                map_data.append({
                    'id': record.id,
                    'asset_no': self.safe_val(record.asset_no),
                    'country': country_val,
                    'site_name': self.safe_val(record.site_name),
                    'portfolio': self.safe_val(record.portfolio),
                    'installation_type': self.safe_val(record.installation_type),
                    'dc_capacity_mwp': self.safe_val(record.dc_capacity_mwp, is_numeric=True),
                    'pcs_capacity': self.safe_val(record.pcs_capacity, is_numeric=True),
                    'battery_capacity_mw': self.safe_val(record.battery_capacity_mw, is_numeric=True),
                    'plant_type': self.safe_val(record.plant_type),
                    'offtaker': self.safe_val(record.offtaker),
                    'cod': self.safe_val(record.cod),
                    'latitude': self.safe_coord(record.latitude),
                    'longitude': self.safe_coord(record.longitude),
                    'created_at': record.created_at.isoformat() if record.created_at else None,
                    'updated_at': record.updated_at.isoformat() if record.updated_at else None,
                })

            # Process yield data for performance calculations
            yield_data = []
            for record in yield_data_queryset:
                yield_data.append({
                    'month': self.safe_val(record.month),
                    'country': self.safe_val(record.country),
                    'portfolio': self.safe_val(record.portfolio),
                    'assetno': self.safe_val(record.assetno),
                    'dc_capacity_mw': self.safe_val(record.dc_capacity_mw, is_numeric=True),
                    'ic_approved_budget': self.safe_val(record.ic_approved_budget, is_numeric=True),
                    'expected_budget': self.safe_val(record.expected_budget, is_numeric=True),
                    'actual_generation': self.safe_val(record.actual_generation, is_numeric=True),
                    'created_at': record.created_at.isoformat() if record.created_at else "",
                    'updated_at': record.updated_at.isoformat() if record.updated_at else "",
                })

            response_data = {
                'mapData': map_data,
                'yieldData': yield_data,
            }

            # Return response directly - data is already sanitized
            # Using serializer causes validation issues with '-' string values
            return Response(response_data, status=status.HTTP_200_OK)

        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

