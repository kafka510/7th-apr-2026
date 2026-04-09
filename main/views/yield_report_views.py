"""
Yield report views and API endpoints
"""
import json
import math
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from waffle import flag_is_active
from accounts.decorators import feature_required
from ..models import YieldData
from .shared.utilities import filter_data_by_user_sites, get_user_accessible_asset_numbers
#from .api_data_views import api_yield_data


@feature_required('yield_report')
@login_required
def yield_report_view(request):
    """Yield report view with data passed directly to template"""
    # Check if React version should be used
    if flag_is_active(request, 'react_yield_report'):
        return render(request, 'main/yield_report_react.html')
    
    # Legacy template
    try:
        # Use the filter_data_by_user_sites function for proper access control
        data = filter_data_by_user_sites(YieldData.objects.all(), 'assetno', request)
        
        # Debug: Calculate database sums
        total_ic_approved_budget = sum(record.ic_approved_budget or 0 for record in data if record.ic_approved_budget is not None and not math.isnan(record.ic_approved_budget))
        total_expected_budget = sum(record.expected_budget or 0 for record in data if record.expected_budget is not None and not math.isnan(record.expected_budget))
        total_actual_generation = sum(record.actual_generation or 0 for record in data if record.actual_generation is not None and not math.isnan(record.actual_generation))
        
                
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
                'budgeted_grid_curtailment': safe_val(record.budgeted_grid_curtailment),
                'grid_outage': safe_val(record.grid_outage),
                'operation_budget': safe_val(record.operation_budget),
                'breakdown_loss': safe_val(record.breakdown_loss),
                'scheduled_outage_loss': safe_val(record.scheduled_outage_loss),
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
                'created_at': record.created_at.isoformat() if record.created_at else "",
                'updated_at': record.updated_at.isoformat() if record.updated_at else "",
                'remarks': '',
            })
        
        return render(request, 'main/Yield Report_v2.html', {
            'yield_data_json': json.dumps(yield_data)
        })
    except Exception as e:
        return render(request, 'main/Yield Report_v2.html', {
            'yield_data_json': json.dumps([]),
            'error_message': str(e)
        })


@feature_required('yield_report')
@login_required
def yield_drilldown_view(request, category):
    """Yield drill-down view for detailed analysis of specific categories"""
    # Check if React version should be used
    if flag_is_active(request, 'react_yield_report'):
        # Valid categories for drill-down
        valid_categories = [
            'ic_approved_budget', 'expected_budget', 'weather_loss_or_gain',
            'grid_curtailment', 'grid_outage', 'operation_budget',
            'breakdown_loss', 'scheduled_outage_loss', 'unclassified_loss', 'actual_generation'
        ]
        
        if category not in valid_categories:
            return render(request, 'main/yield_drilldown_react.html', {
                'error_message': f'Invalid category: {category}',
                'drilldown_category': category,
                'drilldown_title': 'Invalid Category'
            })
        
        # Create a human-readable title for the category
        category_titles = {
            'ic_approved_budget': 'IC Approved Budget',
            'expected_budget': 'Expected Budget',
            'weather_loss_or_gain': 'Weather Loss or Gain',
            'grid_curtailment': 'Grid Curtailment',
            'grid_outage': 'Grid Outage',
            'operation_budget': 'Operation Budget',
            'breakdown_loss': 'Breakdown Loss',
            'scheduled_outage_loss': 'Scheduled Outage Loss',
            'unclassified_loss': 'Unclassified Loss or Gain',
            'actual_generation': 'Actual Generation'
        }
        
        return render(request, 'main/yield_drilldown_react.html', {
            'drilldown_category': category,
            'drilldown_title': category_titles.get(category, category.replace('_', ' ').title())
        })
    
    # Legacy template
    try:
        # Valid categories for drill-down
        valid_categories = [
            'ic_approved_budget', 'expected_budget', 'weather_loss_or_gain',
            'grid_curtailment', 'grid_outage', 'operation_budget',
            'breakdown_loss', 'scheduled_outage_loss', 'unclassified_loss', 'actual_generation'
        ]
        
        if category not in valid_categories:
            return render(request, 'main/Yield_Drilldown.html', {
                'error_message': f'Invalid category: {category}',
                'drilldown_category': category,
                'drilldown_title': 'Invalid Category'
            })
        
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
                'budgeted_grid_curtailment': safe_val(record.budgeted_grid_curtailment),
                'grid_outage': safe_val(record.grid_outage),
                'operation_budget': safe_val(record.operation_budget),
                'breakdown_loss': safe_val(record.breakdown_loss),
                'scheduled_outage_loss': safe_val(record.scheduled_outage_loss),
                'unclassified_loss': safe_val(record.unclassified_loss),
                'actual_generation': safe_val(record.actual_generation),
                'string failure': safe_val(record.string_failure),
                'inverter failure': safe_val(record.inverter_failure),
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
                'created_at': record.created_at.isoformat() if record.created_at else "",
                'updated_at': record.updated_at.isoformat() if record.updated_at else "",
                'remarks': '',
            })
        
        # Create a human-readable title for the category
        category_titles = {
            'ic_approved_budget': 'IC Approved Budget',
            'expected_budget': 'Expected Budget',
            'weather_loss_or_gain': 'Weather Loss or Gain',
            'grid_curtailment': 'Grid Curtailment',
            'grid_outage': 'Grid Outage',
            'operation_budget': 'Operation Budget',
            'breakdown_loss': 'Breakdown Loss',
            'scheduled_outage_loss': 'Scheduled Outage Loss',
            'unclassified_loss': 'Unclassified Loss or Gain',
            'actual_generation': 'Actual Generation'
        }
        
        return render(request, 'main/Yield_Drilldown.html', {
            'yield_data_json': json.dumps(yield_data),
            'drilldown_category': category,
            'drilldown_title': category_titles.get(category, category.replace('_', ' ').title())
        })
    except Exception as e:
        return render(request, 'main/Yield_Drilldown.html', {
            'yield_data_json': json.dumps([]),
            'error_message': str(e),
            'drilldown_category': category,
            'drilldown_title': 'Error'
        })


