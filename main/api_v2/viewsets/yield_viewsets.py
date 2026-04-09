"""
ViewSet for Yield Report endpoints (React app).
Reuses existing logic from main.api.yield_report.YieldDataView
"""

import math
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from shared_app.permissions.base_permissions import HasFeaturePermission
from shared_app.utils.helpers import parse_list_query_param
from shared_app.utils.exceptions import ValidationError
from ..serializers.yield_serializers import (
    YieldDataResponseSerializer,
    YieldDataWithOptionsResponseSerializer,
)


class HasYieldAccess(HasFeaturePermission):
    """Permission class for Yield Report access"""
    required_feature = 'yield_report'


class YieldViewSet(viewsets.ViewSet):
    """
    ViewSet for Yield Report endpoints (React app)
    GET /api/v2/main/yield/data/
    """
    permission_classes = [IsAuthenticated, HasYieldAccess]

    def safe_val(self, val, is_numeric=False):
        """Convert None or NaN to None for numeric fields, empty string for text fields"""
        if val is None or (isinstance(val, float) and math.isnan(val)):
            return None if is_numeric else ""
        # If it's a string that's empty or just whitespace, convert to None for numeric fields
        if is_numeric and isinstance(val, str) and (not val.strip() or val.strip() == ''):
            return None
        return val

    @action(detail=False, methods=['get'], url_path='data')
    def data(self, request):
        """
        Get yield data for React app
        GET /api/v2/main/yield/data/
        
        Query Parameters:
        - month: Optional month filter (YYYY-MM)
        - year: Optional year filter (YYYY)
        - countries: Comma-separated list of countries
        - portfolios: Comma-separated list of portfolios
        - assets: Comma-separated list of asset numbers
        - include_filter_options: Set to '1' to include filter options
        """
        try:
            # Lazy import to avoid circular dependency
            from main.models import YieldData
            from main.views.shared.utilities import filter_data_by_user_sites

            # Parse query parameters
            filters = {
                'month': request.query_params.get('month'),
                'year': request.query_params.get('year'),
                'countries': parse_list_query_param(request, 'countries'),
                'portfolios': parse_list_query_param(request, 'portfolios'),
                'assets': parse_list_query_param(request, 'assets'),
            }

            # Get filtered data based on user's accessible sites
            queryset = filter_data_by_user_sites(YieldData.objects.all(), 'assetno', request)

            # Apply filters
            if filters['month']:
                queryset = queryset.filter(month=filters['month'])
            elif filters['year']:
                # Filter by year (month format is YYYY-MM)
                queryset = queryset.filter(month__startswith=f"{filters['year']}-")
            
            if filters['countries']:
                queryset = queryset.filter(country__in=filters['countries'])
            
            if filters['portfolios']:
                queryset = queryset.filter(portfolio__in=filters['portfolios'])
            
            if filters['assets']:
                queryset = queryset.filter(assetno__in=filters['assets'])

            # Serialize data
            yield_data = []
            for record in queryset:
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
                    'budgeted_grid_curtailment': self.safe_val(record.budgeted_grid_curtailment, is_numeric=True),
                    'grid_outage': self.safe_val(record.grid_outage, is_numeric=True),
                    'operation_budget': self.safe_val(record.operation_budget, is_numeric=True),
                    'breakdown_loss': self.safe_val(record.breakdown_loss, is_numeric=True),
                    'scheduled_outage_loss': self.safe_val(record.scheduled_outage_loss, is_numeric=True),
                    'unclassified_loss': self.safe_val(record.unclassified_loss, is_numeric=True),
                    'actual_generation': self.safe_val(record.actual_generation, is_numeric=True),
                    'string failure': self.safe_val(record.string_failure, is_numeric=True),
                    'inverter failure': self.safe_val(record.inverter_failure, is_numeric=True),
                    'ac failure': self.safe_val(record.ac_failure, is_numeric=True),
                    # Also include underscore versions for compatibility
                    'string_failure': self.safe_val(record.string_failure, is_numeric=True),
                    'inverter_failure': self.safe_val(record.inverter_failure, is_numeric=True),
                    'ac_failure': self.safe_val(record.ac_failure, is_numeric=True),
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
                    'remarks': self.safe_val(getattr(record, 'remarks', '')),
                })

            # Get unique filter options if requested
            filter_options = None
            if request.query_params.get('include_filter_options') == '1':
                all_data = filter_data_by_user_sites(YieldData.objects.all(), 'assetno', request)
                filter_options = {
                    'months': sorted(set([r.month for r in all_data if r.month]), reverse=True),
                    'years': sorted(set([r.month.split('-')[0] for r in all_data if r.month and '-' in r.month]), reverse=True),
                    'countries': sorted(set([r.country for r in all_data if r.country])),
                    'portfolios': sorted(set([r.portfolio for r in all_data if r.portfolio])),
                    'assets': sorted(set([r.assetno for r in all_data if r.assetno])),
                }

            # Serialize response
            if filter_options:
                serializer = YieldDataWithOptionsResponseSerializer({
                    'count': len(yield_data),
                    'results': yield_data,
                    'filter_options': filter_options,
                })
            else:
                serializer = YieldDataResponseSerializer({
                    'count': len(yield_data),
                    'results': yield_data,
                })
            
            return Response(serializer.data, status=status.HTTP_200_OK)
            
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

