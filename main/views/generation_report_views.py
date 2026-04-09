"""
Generation Report views
"""
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from waffle import flag_is_active
from accounts.decorators import feature_required
from ..models import (
    YieldData, MapData, ActualGenerationDailyData, ExpectedBudgetDailyData, BudgetGIIDailyData, ActualGIIDailyData,
    ICApprovedBudgetDailyData
)
import json, math
from .shared.utilities import (
    get_user_accessible_sites
)



@feature_required('generation_report')
@login_required
def generation_report_view(request):
    """Generation Report view with optimized data processing"""
    # Check if React version should be used
    if flag_is_active(request, 'react_generation_report'):
        return render(request, 'main/generation_report_react.html')
    
    # Legacy template
    try:
        # Get user accessible sites
        accessible_sites = get_user_accessible_sites(request)
        
        if not accessible_sites.exists():
            return render(request, 'main/Generation Report.html', {
                'error_message': 'No accessible sites found for your account.'
            })
        
        # Get asset_number values from accessible_sites
        accessible_asset_numbers = accessible_sites.values_list('asset_number', flat=True)
        
        # Fetch all required data
        # 1. YieldData for revenue table
        yield_data_records = YieldData.objects.filter(
            assetno__in=accessible_asset_numbers
        )
        
        # Create yield data list
        yield_data_list = []
        for record in yield_data_records:
            def safe_val(val):
                return "" if val is None or (isinstance(val, float) and math.isnan(val)) else val
            yield_data_list.append({
                'assetno': safe_val(record.assetno),
                'dc_capacity_mw': safe_val(record.dc_capacity_mw),
                'month': safe_val(record.month),
                'country': safe_val(record.country),
                'portfolio': safe_val(record.portfolio),
                'ic_approved_budget_dollar': safe_val(record.ic_approved_budget_dollar),
                'expected_budget_dollar': safe_val(record.expected_budget_dollar),
                'actual_generation_dollar': safe_val(record.actual_generation_dollar),
                'operational_budget_dollar': safe_val(record.operational_budget_dollar),
                'revenue_loss_op': safe_val(record.revenue_loss_op),
                'ppa_rate': safe_val(record.ppa_rate),
            })
        
        # 2. IC Approved Budget Daily data
        ic_approved_budget_daily_data = ICApprovedBudgetDailyData.objects.filter(
            asset_code__in=accessible_asset_numbers
        )
        
        # Transform to wide format
        ic_approved_budget_daily_wide = {}
        for record in ic_approved_budget_daily_data:
            def safe_val(val):
                return "" if val is None or (isinstance(val, float) and math.isnan(val)) else val
            date_key = record.date.isoformat() if record.date else "unknown"
            if date_key not in ic_approved_budget_daily_wide:
                ic_approved_budget_daily_wide[date_key] = {'Date': date_key}
            asset_key = record.asset_code if record.asset_code else "unknown"
            ic_approved_budget_daily_wide[date_key][asset_key] = safe_val(record.ic_approved_budget_kwh)
        
        ic_approved_budget_daily_list = list(ic_approved_budget_daily_wide.values())
        
        # 3. Actual Generation Daily data - CORRECTED FIELD NAME
        actual_gen_data = ActualGenerationDailyData.objects.filter(
            asset_code__in=accessible_asset_numbers
        )
        
        # Transform to wide format
        actual_gen_wide = {}
        for record in actual_gen_data:
            def safe_val(val):
                return "" if val is None or (isinstance(val, float) and math.isnan(val)) else val
            date_key = record.date.isoformat() if record.date else "unknown"
            if date_key not in actual_gen_wide:
                actual_gen_wide[date_key] = {'Date': date_key}
            asset_key = record.asset_code if record.asset_code else "unknown"
            actual_gen_wide[date_key][asset_key] = safe_val(record.generation_kwh)  # CORRECTED: generation_kwh not actual_generation_kwh
        
        actual_gen_list = list(actual_gen_wide.values())
        
        # 4. Expected Budget Daily data - CORRECTED FIELD NAME
        expected_budget_data = ExpectedBudgetDailyData.objects.filter(
            asset_code__in=accessible_asset_numbers
        )
        
        # Transform to wide format
        expected_budget_wide = {}
        for record in expected_budget_data:
            def safe_val(val):
                return "" if val is None or (isinstance(val, float) and math.isnan(val)) else val
            date_key = record.date.isoformat() if record.date else "unknown"
            if date_key not in expected_budget_wide:
                expected_budget_wide[date_key] = {'Date': date_key}
            asset_key = record.asset_code if record.asset_code else "unknown"
            expected_budget_wide[date_key][asset_key] = safe_val(record.expected_budget_kwh)  # CORRECTED: expected_budget_kwh
        
        expected_budget_list = list(expected_budget_wide.values())
        
        # 5. Budget GII Daily data - CORRECTED FIELD NAME
        budget_gii_data = BudgetGIIDailyData.objects.filter(
            asset_code__in=accessible_asset_numbers
        )
        
        # Transform to wide format
        budget_gii_wide = {}
        for record in budget_gii_data:
            def safe_val(val):
                return "" if val is None or (isinstance(val, float) and math.isnan(val)) else val
            date_key = record.date.isoformat() if record.date else "unknown"
            if date_key not in budget_gii_wide:
                budget_gii_wide[date_key] = {'Date': date_key}
            asset_key = record.asset_code if record.asset_code else "unknown"
            budget_gii_wide[date_key][asset_key] = safe_val(record.budget_gii_kwh)  # CORRECTED: budget_gii_kwh
        
        budget_gii_list = list(budget_gii_wide.values())
        
        # 6. Actual GII Daily data - CORRECTED FIELD NAME
        actual_gii_data = ActualGIIDailyData.objects.filter(
            asset_code__in=accessible_asset_numbers
        )
        
        # Transform to wide format
        actual_gii_wide = {}
        for record in actual_gii_data:
            def safe_val(val):
                return "" if val is None or (isinstance(val, float) and math.isnan(val)) else val
            date_key = record.date.isoformat() if record.date else "unknown"
            if date_key not in actual_gii_wide:
                actual_gii_wide[date_key] = {'Date': date_key}
            asset_key = record.asset_code if record.asset_code else "unknown"
            actual_gii_wide[date_key][asset_key] = safe_val(record.actual_gii_kwh)  # CORRECTED: actual_gii_kwh
        
        actual_gii_list = list(actual_gii_wide.values())
        
        # 7. Map data for DC capacity
        map_data = MapData.objects.filter(
            asset_no__in=accessible_asset_numbers
        )
        
        map_data_list = []
        for record in map_data:
            def safe_val(val):
                return "" if val is None or (isinstance(val, float) and math.isnan(val)) else val
            map_data_list.append({
                'asset_no': safe_val(record.asset_no),
                'dc_capacity_mwp': safe_val(record.dc_capacity_mwp),
                'country': safe_val(record.country),
                'portfolio': safe_val(record.portfolio),
            })
        
        return render(request, 'main/Generation Report.html', {
            'map_data_json': json.dumps(map_data_list),
            'ic_approved_budget_daily_json': json.dumps(ic_approved_budget_daily_list),
            'actual_gen_data_json': json.dumps(actual_gen_list),
            'expected_budget_data_json': json.dumps(expected_budget_list),
            'budget_gii_data_json': json.dumps(budget_gii_list),
            'actual_gii_data_json': json.dumps(actual_gii_list),
            'yield_data_json': json.dumps(yield_data_list),
        })
        
    except Exception as e:
        return render(request, 'main/Generation Report.html', {
            'map_data_json': json.dumps([]),
            'ic_approved_budget_daily_json': json.dumps([]),
            'actual_gen_data_json': json.dumps([]),
            'expected_budget_data_json': json.dumps([]),
            'budget_gii_data_json': json.dumps([]),
            'actual_gii_data_json': json.dumps([]),
            'yield_data_json': json.dumps([]),
            'error_message': f'An error occurred while loading the generation report: {str(e)}'
        })
