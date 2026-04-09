"""
Sales Dashboard API endpoints
"""
import math
import logging
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from accounts.decorators import feature_required
from ..models import YieldData, MapData
from ..views.shared.utilities import filter_data_by_user_sites

logger = logging.getLogger(__name__)


@login_required
@feature_required('sales')
def sales_data_view(request):
    """
    API endpoint to fetch sales dashboard data
    Returns yield data and map data for the sales page
    """
    logger.info(f"[sales_data_view] Called - Path: {request.path}, Method: {request.method}")

    try:
        yield_data_queryset = filter_data_by_user_sites(YieldData.objects.all(), 'assetno', request)
        map_data_queryset = filter_data_by_user_sites(MapData.objects.all(), 'asset_no', request)

        def safe_val(val):
            if val is None or (isinstance(val, float) and math.isnan(val)):
                return ""
            return val

        yield_data = []
        for record in yield_data_queryset:
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
                'grid_outage': safe_val(record.grid_outage),
                'operation_budget': safe_val(record.operation_budget),
                'breakdown_loss': safe_val(record.breakdown_loss),
                'unclassified_loss': safe_val(record.unclassified_loss),
                'actual_generation': safe_val(record.actual_generation),
                'string_failure': safe_val(record.string_failure),
                'inverter_failure': safe_val(record.inverter_failure),
                'mv_failure': safe_val(record.mv_failure),
                'hv_failure': safe_val(record.hv_failure),
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

        map_data = []
        for record in map_data_queryset:
            map_data.append({
                'asset_no': safe_val(record.asset_no),
                'country': safe_val(record.country),
                'portfolio': safe_val(record.portfolio),
                'site_name': safe_val(record.site_name),
                'dc_capacity_mwp': safe_val(record.dc_capacity_mwp),
                'battery_capacity_mw': safe_val(record.battery_capacity_mw),
                'plant_type': safe_val(record.plant_type),
                'installation_type': safe_val(record.installation_type),
                'latitude': safe_val(record.latitude),
                'longitude': safe_val(record.longitude),
            })

        response_data = {
            'yieldData': yield_data,
            'mapData': map_data,
        }

        logger.info(f"[sales_data_view] Returning {len(yield_data)} yield records and {len(map_data)} map records")

        response = JsonResponse(response_data, status=200)
        response['Cache-Control'] = 'no-cache, no-store, must-revalidate'
        response['Pragma'] = 'no-cache'
        response['Expires'] = '0'
        return response

    except Exception as e:
        logger.error(f"Sales dashboard error: {str(e)}", exc_info=True)
        return JsonResponse({
            'error': f'An error occurred while loading the sales dashboard: {str(e)}'
        }, status=500)

