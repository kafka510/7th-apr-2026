"""
Revenue loss analysis views
"""
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from waffle.decorators import flag_is_active
from accounts.decorators import feature_required


from ..models import (
    YieldData
)


import json, math

from .shared.utilities import (
	filter_data_by_user_sites
)


@feature_required('revenue_loss')
@login_required
def revenue_loss_view(request):
    """Revenue loss view - data is loaded via API endpoints"""
    if flag_is_active(request, 'react_revenue_loss'):
        return render(request, 'main/revenue_loss_react.html')
    try:
        # Use the filter_data_by_user_sites function for proper access control
        data = filter_data_by_user_sites(YieldData.objects.all(), 'assetno', request)
        
        
        yield_data = []
        for record in data:
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
                'grid_outage': safe_val(record.grid_outage),
                'operation_budget': safe_val(record.operation_budget),
                'breakdown_loss': safe_val(record.breakdown_loss),
                'unclassified_loss': safe_val(record.unclassified_loss),
                'actual_generation': safe_val(record.actual_generation),
                'string failure': safe_val(record.string_failure),
                'inverter failure': safe_val(record.inverter_failure),
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
                # Add the new dollar fields
                'ppa_rate': safe_val(record.ppa_rate),
                'ic_approved_budget_dollar': safe_val(record.ic_approved_budget_dollar),
                'expected_budget_dollar': safe_val(record.expected_budget_dollar),
                'actual_generation_dollar': safe_val(record.actual_generation_dollar),
                'operational_budget_dollar': safe_val(record.operational_budget_dollar),
                'revenue_loss_op': safe_val(record.revenue_loss_op),
                'created_at': record.created_at.isoformat() if record.created_at else "",
                'updated_at': record.updated_at.isoformat() if record.updated_at else "",
                'remarks': '',
            })
        
        
        
        return render(request, 'main/revenue_loss.html', {
            'yield_data_json': json.dumps(yield_data)
        })
    except Exception as e:
        print(f"DEBUG: Revenue Loss - Error: {str(e)}")
        return render(request, 'main/revenue_loss.html', {
            'yield_data_json': json.dumps([]),
            'error_message': str(e)
        })
