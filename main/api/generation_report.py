"""
Generation Report API endpoints
"""
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from accounts.decorators import feature_required
from django.db.models import Q
import math
import json
from ..models import (
    YieldData, MapData, ActualGenerationDailyData, ExpectedBudgetDailyData,
    BudgetGIIDailyData, ActualGIIDailyData, ICApprovedBudgetDailyData
)
from ..views.shared.utilities import get_user_accessible_sites
from main.permissions import user_has_feature


@login_required
@feature_required('generation_report')
def generation_report_data_view(request):
    """
    API endpoint to fetch generation report data
    Returns all data needed for the generation report page
    Uses function-based view with JsonResponse to bypass DRF pagination
    """
    import logging
    logger = logging.getLogger(__name__)
    logger.info("[generation_report_data_view] Function-based view called - START")
    logger.info(f"[generation_report_data_view] Request path: {request.path}")
    logger.info(f"[generation_report_data_view] Request method: {request.method}")
    
    try:
        # Get user accessible sites
        accessible_sites = get_user_accessible_sites(request)
        
        if not accessible_sites.exists():
            return JsonResponse({
                'error': 'No accessible sites found for your account.'
            }, status=403)
        
        # Get asset_number values from accessible_sites
        accessible_asset_numbers = accessible_sites.values_list('asset_number', flat=True)
        
        # Helper function to safely convert value
        def safe_val(val):
            if val is None or (isinstance(val, float) and math.isnan(val)):
                return ""
            return val
        
        # 1. YieldData for revenue table
        yield_data_records = YieldData.objects.filter(
            assetno__in=accessible_asset_numbers
        )
        
        yield_data_list = []
        for record in yield_data_records:
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
        
        # 2. IC Approved Budget Daily data (wide format)
        ic_approved_budget_daily_data = ICApprovedBudgetDailyData.objects.filter(
            asset_code__in=accessible_asset_numbers
        )
        
        ic_approved_budget_daily_wide = {}
        for record in ic_approved_budget_daily_data:
            date_key = record.date.isoformat() if record.date else "unknown"
            if date_key not in ic_approved_budget_daily_wide:
                ic_approved_budget_daily_wide[date_key] = {'Date': date_key}
            asset_key = record.asset_code if record.asset_code else "unknown"
            ic_approved_budget_daily_wide[date_key][asset_key] = safe_val(record.ic_approved_budget_kwh)
        
        ic_approved_budget_daily_list = list(ic_approved_budget_daily_wide.values())
        
        # 3. Actual Generation Daily data
        actual_gen_data = ActualGenerationDailyData.objects.filter(
            asset_code__in=accessible_asset_numbers
        )
        
        actual_gen_wide = {}
        for record in actual_gen_data:
            date_key = record.date.isoformat() if record.date else "unknown"
            if date_key not in actual_gen_wide:
                actual_gen_wide[date_key] = {'Date': date_key}
            asset_key = record.asset_code if record.asset_code else "unknown"
            actual_gen_wide[date_key][asset_key] = safe_val(record.generation_kwh)
        
        actual_gen_list = list(actual_gen_wide.values())
        
        # 4. Expected Budget Daily data
        expected_budget_data = ExpectedBudgetDailyData.objects.filter(
            asset_code__in=accessible_asset_numbers
        )
        
        expected_budget_wide = {}
        for record in expected_budget_data:
            date_key = record.date.isoformat() if record.date else "unknown"
            if date_key not in expected_budget_wide:
                expected_budget_wide[date_key] = {'Date': date_key}
            asset_key = record.asset_code if record.asset_code else "unknown"
            expected_budget_wide[date_key][asset_key] = safe_val(record.expected_budget_kwh)
        
        expected_budget_list = list(expected_budget_wide.values())
        
        # 5. Budget GII Daily data
        budget_gii_data = BudgetGIIDailyData.objects.filter(
            asset_code__in=accessible_asset_numbers
        )
        
        budget_gii_wide = {}
        for record in budget_gii_data:
            date_key = record.date.isoformat() if record.date else "unknown"
            if date_key not in budget_gii_wide:
                budget_gii_wide[date_key] = {'Date': date_key}
            asset_key = record.asset_code if record.asset_code else "unknown"
            budget_gii_wide[date_key][asset_key] = safe_val(record.budget_gii_kwh)
        
        budget_gii_list = list(budget_gii_wide.values())
        
        # 6. Actual GII Daily data
        actual_gii_data = ActualGIIDailyData.objects.filter(
            asset_code__in=accessible_asset_numbers
        )
        
        actual_gii_wide = {}
        for record in actual_gii_data:
            date_key = record.date.isoformat() if record.date else "unknown"
            if date_key not in actual_gii_wide:
                actual_gii_wide[date_key] = {'Date': date_key}
            asset_key = record.asset_code if record.asset_code else "unknown"
            actual_gii_wide[date_key][asset_key] = safe_val(record.actual_gii_kwh)
        
        actual_gii_list = list(actual_gii_wide.values())
        
        # 7. Map data for DC capacity
        map_data = MapData.objects.filter(
            asset_no__in=accessible_asset_numbers
        )
        
        map_data_list = []
        for record in map_data:
            map_data_list.append({
                'asset_no': safe_val(record.asset_no),
                'dc_capacity_mwp': safe_val(record.dc_capacity_mwp),
                'country': safe_val(record.country),
                'portfolio': safe_val(record.portfolio),
            })
        
        # Calculate latest report date (80% threshold)
        latest_report_date = _get_latest_report_date(actual_gen_list)
        
        # Get date range
        date_range = _get_date_range(actual_gen_list)
        
        response_data = {
            'icApprovedBudgetDaily': ic_approved_budget_daily_list,
            'expectedBudgetDaily': expected_budget_list,
            'actualGenerationDaily': actual_gen_list,
            'budgetGIIDaily': budget_gii_list,
            'actualGIIDaily': actual_gii_list,
            'yieldData': yield_data_list,
            'mapData': map_data_list,
            'latestReportDate': latest_report_date,
            'dateRange': date_range,
        }
        
        # Log response structure for debugging
        import logging
        logger = logging.getLogger(__name__)
        logger.info(f"[generation_report_data_view] Function-based view called")
        logger.info(f"Generation report response: {len(ic_approved_budget_daily_list)} IC budget, "
                   f"{len(expected_budget_list)} expected, {len(actual_gen_list)} actual, "
                   f"{len(yield_data_list)} yield, {len(map_data_list)} map records")
        logger.info(f"Response data keys: {list(response_data.keys())}")
        logger.info(f"Returning JsonResponse with {len(response_data)} top-level keys")
        
        # Return JsonResponse directly - bypasses DRF pagination completely
        response = JsonResponse(response_data, status=200)
        # Add cache control headers to prevent caching
        response['Cache-Control'] = 'no-cache, no-store, must-revalidate'
        response['Pragma'] = 'no-cache'
        response['Expires'] = '0'
        logger.info(f"JsonResponse created, Content-Type: {response.get('Content-Type', 'N/A')}")
        logger.info(f"[generation_report_data_view] Returning response with {len(response_data)} keys")
        logger.info(f"[generation_report_data_view] Response data sample keys: {list(response_data.keys())[:3]}")
        return response
        
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Generation report error: {str(e)}", exc_info=True)
        return JsonResponse({
            'error': f'An error occurred while loading the generation report: {str(e)}'
        }, status=500)


def _get_latest_report_date(actual_gen_list):
    """Get latest date where 80% of assets have data"""
    if not actual_gen_list:
        return ""
    
    # Get all asset columns (excluding Date)
    if not actual_gen_list[0]:
        return ""
    
    asset_cols = [k for k in actual_gen_list[0].keys() if k not in ['Date', 'date']]
    total_assets = len(asset_cols)
    if total_assets == 0:
        return ""
    
    threshold = math.ceil(total_assets * 0.8)
    
    # Sort by date descending
    sorted_rows = sorted(
        actual_gen_list,
        key=lambda r: r.get('Date') or r.get('date') or '',
        reverse=True
    )
    
    for row in sorted_rows:
        date_str = row.get('Date') or row.get('date')
        if not date_str:
            continue
        
        # Count assets with data
        filled_assets = 0
        for col in asset_cols:
            val = row.get(col)
            if val is not None and val != '':
                try:
                    num_val = float(val)
                    if num_val > 0:
                        filled_assets += 1
                except (ValueError, TypeError):
                    pass
        
        if filled_assets >= threshold:
            return date_str
    
    # Fallback: return most recent date
    if sorted_rows:
        return sorted_rows[0].get('Date') or sorted_rows[0].get('date') or ""
    
    return ""


def _get_date_range(actual_gen_list):
    """Get min/max date range from actual generation data"""
    if not actual_gen_list:
        return {'min': '2025-01-01', 'max': '2025-12-31'}
    
    dates = [r.get('Date') or r.get('date') for r in actual_gen_list if r.get('Date') or r.get('date')]
    if not dates:
        return {'min': '2025-01-01', 'max': '2025-12-31'}
    
    dates.sort()
    min_date = dates[0]
    max_date = dates[-1]
    
    # Always return full year range
    if min_date:
        year = int(min_date.split('-')[0])
        return {
            'min': f'{year}-01-01',
            'max': f'{year}-12-31'
        }
    
    return {'min': '2025-01-01', 'max': '2025-12-31'}
