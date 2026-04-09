from rest_framework.permissions import BasePermission, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
import math

from main.permissions import user_has_feature
from main.models import YieldData
from main.views.shared.utilities import filter_data_by_user_sites


class HasYieldFeaturePermission(BasePermission):
    message = 'You do not have access to the yield report.'

    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated and user_has_feature(request.user, 'yield_report')


class YieldDataView(APIView):
    """API endpoint for yield data with filtering support"""
    permission_classes = [IsAuthenticated, HasYieldFeaturePermission]

    def get(self, request):
        # Parse filter parameters
        filters = {
            'month': request.query_params.get('month'),
            'year': request.query_params.get('year'),
            'countries': [c for c in request.query_params.get('countries', '').split(',') if c],
            'portfolios': [p for p in request.query_params.get('portfolios', '').split(',') if p],
            'assets': [a for a in request.query_params.get('assets', '').split(',') if a],
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
            def safe_val(val):
                return "" if val is None or (isinstance(val, float) and math.isnan(val)) else val
            
            yield_data.append({
                'month': safe_val(record.month),
                'country': safe_val(record.country),
                'portfolio': safe_val(record.portfolio),
                'assetno': safe_val(record.assetno),
                'dc_capacity_mw': safe_val(record.dc_capacity_mw),
                'ic_approved_budget': safe_val(record.ic_approved_budget),
                'expected_budget': safe_val(record.expected_budget),
                'weather_loss_or_gain': safe_val(record.weather_loss_or_gain),
                'grid_curtailment': safe_val(record.grid_curtailment),
                'budgeted_grid_curtailment': safe_val(record.budgeted_grid_curtailment),
                'grid_outage': safe_val(record.grid_outage),
                'operation_budget': safe_val(record.operation_budget),
                'breakdown_loss': safe_val(record.breakdown_loss),
                'scheduled_outage_loss': safe_val(record.scheduled_outage_loss),
                'unclassified_loss': safe_val(record.unclassified_loss),
                'actual_generation': safe_val(record.actual_generation),
                'string_failure': safe_val(record.string_failure),
                'inverter_failure': safe_val(record.inverter_failure),
                'ac_failure': safe_val(record.ac_failure),
                'expected_pr': safe_val(record.expected_pr),
                'actual_pr': safe_val(record.actual_pr),
                'pr_gap': safe_val(record.pr_gap),
                'pr_gap_observation': safe_val(record.pr_gap_observation),
                'pr_gap_action_need_to_taken': safe_val(record.pr_gap_action_need_to_taken),
                'revenue_loss': safe_val(record.revenue_loss),
                'revenue_loss_observation': safe_val(record.revenue_loss_observation),
                'revenue_loss_action_need_to_taken': safe_val(record.revenue_loss_action_need_to_taken),
                'actual_irradiation': safe_val(record.actual_irradiation),
                'ac_capacity_mw': safe_val(record.ac_capacity_mw),
                'bess_capacity_mwh': safe_val(record.bess_capacity_mwh),
                'bess_generation_mwh': safe_val(record.bess_generation_mwh),
                'ppa_rate': safe_val(record.ppa_rate),
                'ic_approved_budget_dollar': safe_val(record.ic_approved_budget_dollar),
                'expected_budget_dollar': safe_val(record.expected_budget_dollar),
                'actual_generation_dollar': safe_val(record.actual_generation_dollar),
                'operational_budget_dollar': safe_val(record.operational_budget_dollar),
                'revenue_loss_op': safe_val(record.revenue_loss_op),
                'created_at': record.created_at.isoformat() if record.created_at else "",
                'updated_at': record.updated_at.isoformat() if record.updated_at else "",
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

        response_data = {
            'count': len(yield_data),
            'results': yield_data,
        }

        if filter_options:
            response_data['filter_options'] = filter_options

        return Response(response_data)

