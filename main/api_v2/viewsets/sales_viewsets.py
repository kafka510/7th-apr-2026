"""
ViewSet for Sales Dashboard endpoints (React app).
Reuses existing logic from main.api.sales
"""

import math
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from shared_app.permissions.base_permissions import HasFeaturePermission


class HasSalesAccess(HasFeaturePermission):
    """Permission class for Sales Dashboard access"""
    required_feature = 'sales'


class SalesViewSet(viewsets.ViewSet):
    """
    ViewSet for Sales Dashboard endpoints (React app)
    GET /api/v2/main/sales/sales-data/
    """
    permission_classes = [IsAuthenticated, HasSalesAccess]

    def safe_val(self, val, is_numeric=False):
        """Convert None or NaN to None for numeric fields, empty string for text fields"""
        if val is None or (isinstance(val, float) and math.isnan(val)):
            return None if is_numeric else ""
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

    @action(detail=False, methods=['get'], url_path='sales-data')
    def sales_data(self, request):
        """
        Get sales dashboard data for React app
        GET /api/v2/main/sales/sales-data/
        """
        try:
            # Lazy import to avoid circular dependency
            from main.models import YieldData, MapData
            from main.views.shared.utilities import filter_data_by_user_sites

            yield_data_queryset = filter_data_by_user_sites(YieldData.objects.all(), 'assetno', request)
            map_data_queryset = filter_data_by_user_sites(MapData.objects.all(), 'asset_no', request)

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
                    'weather_loss_or_gain': self.safe_val(record.weather_loss_or_gain, is_numeric=True),
                    'grid_curtailment': self.safe_val(record.grid_curtailment, is_numeric=True),
                    'grid_outage': self.safe_val(record.grid_outage, is_numeric=True),
                    'operation_budget': self.safe_val(record.operation_budget, is_numeric=True),
                    'breakdown_loss': self.safe_val(record.breakdown_loss, is_numeric=True),
                    'unclassified_loss': self.safe_val(record.unclassified_loss, is_numeric=True),
                    'actual_generation': self.safe_val(record.actual_generation, is_numeric=True),
                    'string_failure': self.safe_val(record.string_failure, is_numeric=True),
                    'inverter_failure': self.safe_val(record.inverter_failure, is_numeric=True),
                    'mv_failure': self.safe_val(record.mv_failure, is_numeric=True),
                    'hv_failure': self.safe_val(record.hv_failure, is_numeric=True),
                    'expected_pr': self.safe_val(record.expected_pr, is_numeric=True),
                    'actual_pr': self.safe_val(record.actual_pr, is_numeric=True),
                    'pr_gap': self.safe_val(record.pr_gap, is_numeric=True),
                    'pr_gap_observation': self.safe_val(record.pr_gap_observation),
                    'pr_gap_action_need_to_taken': self.safe_val(record.pr_gap_action_need_to_taken),
                    'revenue_loss': self.safe_val(record.revenue_loss, is_numeric=True),
                    'revenue_loss_observation': self.safe_val(record.revenue_loss_observation),
                    'revenue_loss_action_need_to_taken': self.safe_val(record.revenue_loss_action_need_to_taken),
                    'actual_irradiation': self.safe_val(record.actual_irradiation, is_numeric=True),
                    'ac_capacity_mw': self.safe_val(record.ac_capacity_mw, is_numeric=True),
                    'bess_capacity_mwh': self.safe_val(record.bess_capacity_mwh, is_numeric=True),
                    'bess_generation_mwh': self.safe_val(record.bess_generation_mwh, is_numeric=True),
                    'ppa_rate': self.safe_val(record.ppa_rate, is_numeric=True),
                    'ic_approved_budget_dollar': self.safe_val(record.ic_approved_budget_dollar, is_numeric=True),
                    'expected_budget_dollar': self.safe_val(record.expected_budget_dollar, is_numeric=True),
                    'actual_generation_dollar': self.safe_val(record.actual_generation_dollar, is_numeric=True),
                    'operational_budget_dollar': self.safe_val(record.operational_budget_dollar, is_numeric=True),
                    'revenue_loss_op': self.safe_val(record.revenue_loss_op, is_numeric=True),
                    'created_at': record.created_at.isoformat() if record.created_at else None,
                    'updated_at': record.updated_at.isoformat() if record.updated_at else None,
                })

            map_data = []
            for record in map_data_queryset:
                map_data.append({
                    'asset_no': self.safe_val(record.asset_no),
                    'country': self.safe_val(record.country),
                    'portfolio': self.safe_val(record.portfolio),
                    'site_name': self.safe_val(record.site_name),
                    'dc_capacity_mwp': self.safe_val(record.dc_capacity_mwp, is_numeric=True),
                    'battery_capacity_mw': self.safe_val(record.battery_capacity_mw, is_numeric=True),
                    'plant_type': self.safe_val(record.plant_type),
                    'installation_type': self.safe_val(record.installation_type),
                    'latitude': self.safe_coord(record.latitude),
                    'longitude': self.safe_coord(record.longitude),
                })

            response_data = {
                'yieldData': yield_data,
                'mapData': map_data,
            }

            # Return response directly - data is already sanitized
            # Using serializer causes validation issues with '-' string values
            return Response(response_data, status=status.HTTP_200_OK)

        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

