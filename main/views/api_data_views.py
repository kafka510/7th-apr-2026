"""
Data API endpoints for various data sources
"""

import math, json
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.db.models import Q
from main.decorators.cors_decorator import cors_allow_same_site
from ..models import (
    YieldData, BESSData, BESSV1Data, AOCData, ICEData, MapData, MinamataStringLossData,
    ICApprovedBudgetDailyData, timeseries_data, AssetList, LossCalculationData, UserProfile,
    ActualGenerationDailyData, ExpectedBudgetDailyData, BudgetGIIDailyData, ActualGIIDailyData
)

from .shared.utilities import (
	get_user_accessible_asset_numbers, filter_data_by_user_sites, get_user_accessible_sites
)
from main.permissions import user_has_capability
from accounts.decorators import feature_required


@login_required
@cors_allow_same_site
def api_yield_data(request):
    """API endpoint for yield data"""
    try:        
        data = filter_data_by_user_sites(YieldData.objects.all(), 'assetno', request)        
        
        # If no data after filtering, show some sample data for debugging
        if data.count() == 0:
            
            sample_data = YieldData.objects.all()[:5]
            for record in sample_data:
                print(f"  - Asset: {record.assetno}, Month: {record.month}, Country: {record.country}")
        
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
                'unclassified_loss': safe_val(record.unclassified_loss),
                'actual_generation': safe_val(record.actual_generation),
                'string failure': safe_val(record.string_failure),
                'inverter failure': safe_val(record.inverter_failure),
                'mv_failure': safe_val(record.mv_failure),
                'hv_failure': safe_val(record.hv_failure),
                'ac_failure': safe_val(record.ac_failure),
                'scheduled_outage_loss': safe_val(record.scheduled_outage_loss),
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
                'remarks': '',
            })
        print(f"Yield API: Returning {len(yield_data)} records")
        return JsonResponse(yield_data, safe=False)
    except Exception as e:
        print(f"Yield API Error: {str(e)}")
        return JsonResponse({'error': str(e)}, status=500)

@login_required
def api_yield_data_sales(request):
    """API endpoint for yield data specifically for Sales page"""
    try:
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
                'unclassified_loss': safe_val(record.unclassified_loss),
                'actual_generation': safe_val(record.actual_generation),
                'string_failure': safe_val(record.string_failure),
                'inverter_failure': safe_val(record.inverter_failure),
                'mv_failure': safe_val(record.mv_failure),
                'hv_failure': safe_val(record.hv_failure),
                'ac_failure': safe_val(record.ac_failure),
                'scheduled_outage_loss': safe_val(record.scheduled_outage_loss),
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
                'remarks': '',
            })
        return JsonResponse({'data': yield_data})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)    

@login_required
@cors_allow_same_site
def api_bess_data(request):
    """API endpoint for BESS data (main_bessdata table).
    When ?month=YYYY-MM is provided, returns daily records for that month for Actual CUF(%) and Actual Cycles charts.
    Otherwise returns all daily records (legacy behavior)."""
    try:
        month_param = request.GET.get('month', '').strip()
        single_month = month_param and len(month_param) >= 6  # e.g. 2025-01 or 2025-1

        if single_month:
            # For single-month: filter main_bessdata by user-accessible sites (asset_no can match asset_number OR asset_code).
            # Month filtering is handled on the frontend (by selectedMonth + date-based grouping),
            # which avoids backend assumptions about how dates/months are stored in main_bessdata.
            accessible_sites = get_user_accessible_sites(request)
            if not accessible_sites or not accessible_sites.exists():
                return JsonResponse([], safe=False)
            asset_numbers = list(accessible_sites.values_list('asset_number', flat=True))
            asset_codes = list(accessible_sites.values_list('asset_code', flat=True))
            allowed_assets = list(set(asset_numbers + asset_codes))
            allowed_assets = [a for a in allowed_assets if a]
            if not allowed_assets:
                return JsonResponse([], safe=False)
            data = BESSData.objects.filter(asset_no__in=allowed_assets)
        else:
            # Legacy: use filter_data_by_user_sites and energy filters
            data = filter_data_by_user_sites(BESSData.objects.all(), 'asset_no', request)
            # Legacy: only show records with actual energy values
            data = data.filter(
                pv_energy_kwh__isnull=False,
                charge_energy_kwh__isnull=False,
                discharge_energy_kwh__isnull=False,
                export_energy_kwh__isnull=False,
            )

        bess_data = []
        for record in data:
            def safe_val(val):
                if val is None:
                    return None
                elif isinstance(val, float) and math.isnan(val):
                    return None
                else:
                    return val

            if single_month:
                # Return DailyBessRecord shape for BESS V1 dashboard single-month (Actual CUF % & Actual Cycles charts)
                bess_data.append({
                    'id': record.id,
                    'date': safe_val(record.date),
                    'month': safe_val(record.month),
                    'country': safe_val(record.country),
                    'portfolio': safe_val(record.portfolio),
                    'asset_no': safe_val(record.asset_no),
                    'actual_no_of_cycles': safe_val(record.actual_no_of_cycles),
                    'cuf': safe_val(record.cuf),
                    'charge_energy_kwh': safe_val(record.charge_energy_kwh),
                    'discharge_energy_kwh': safe_val(record.discharge_energy_kwh),
                    'battery_capacity_mw': safe_val(record.battery_capacity_mw),
                    'created_at': record.created_at.isoformat() if record.created_at else None,
                    'updated_at': record.updated_at.isoformat() if record.updated_at else None,
                })
            else:
                bess_data.append({
                    'id': record.id,
                    'asset_no': safe_val(record.asset_no),
                    'date': safe_val(record.date),
                    'month': safe_val(record.month),
                    'country': safe_val(record.country),
                    'portfolio': safe_val(record.portfolio),
                    'battery_capacity_mw': safe_val(record.battery_capacity_mw),
                    'export_energy_kwh': safe_val(record.export_energy_kwh),
                    'pv_energy_kwh': safe_val(record.pv_energy_kwh),
                    'charge_energy_kwh': safe_val(record.charge_energy_kwh),
                    'discharge_energy_kwh': safe_val(record.discharge_energy_kwh),
                    'min_soc': safe_val(record.min_soc),
                    'max_soc': safe_val(record.max_soc),
                    'min_ess_temperature': safe_val(record.min_ess_temperature),
                    'max_ess_temperature': safe_val(record.max_ess_temperature),
                    'min_ess_humidity': safe_val(record.min_ess_humidity),
                    'max_ess_humidity': safe_val(record.max_ess_humidity),
                    'rte': safe_val(record.rte),
                    'created_at': record.created_at.isoformat() if record.created_at else None,
                    'updated_at': record.updated_at.isoformat() if record.updated_at else None,
                })

        return JsonResponse(bess_data, safe=False)
    except Exception as e:
        print(f"BESS API Error: {str(e)}")
        return JsonResponse({'error': str(e)}, status=500)


@login_required
@cors_allow_same_site
def api_bess_v1_data(request):
    """API endpoint for BESS V1 dashboard data"""
    try:
        data = filter_data_by_user_sites(BESSV1Data.objects.all(), 'asset_no', request)

        bess_v1_data = []
        for record in data:
            def safe_val(val):
                if val is None:
                    return None
                if isinstance(val, float) and math.isnan(val):
                    return None
                return val

            bess_v1_data.append({
                'id': record.id,
                'month': safe_val(record.month),
                'country': safe_val(record.country),
                'portfolio': safe_val(record.portfolio),
                'asset_no': safe_val(record.asset_no),
                'battery_capacity_mwh': safe_val(record.battery_capacity_mwh),
                'actual_pv_energy_kwh': safe_val(record.actual_pv_energy_kwh),
                'actual_export_energy_kwh': safe_val(record.actual_export_energy_kwh),
                'actual_charge_energy_kwh': safe_val(record.actual_charge_energy_kwh),
                'actual_discharge_energy': safe_val(record.actual_discharge_energy),
                'actual_pv_grid_kwh': safe_val(record.actual_pv_grid_kwh),
                'actual_system_losses': safe_val(record.actual_system_losses),
                'min_soc': safe_val(record.min_soc),
                'max_soc': safe_val(record.max_soc),
                'min_ess_temp': safe_val(record.min_ess_temp),
                'max_ess_temp': safe_val(record.max_ess_temp),
                'actual_avg_rte': safe_val(record.actual_avg_rte),
                'actual_cuf': safe_val(record.actual_cuf),
                'actual_no_of_cycles': safe_val(record.actual_no_of_cycles),
                'budget_pv_energy_kwh': safe_val(record.budget_pv_energy_kwh),
                'budget_export_energy_kwh': safe_val(record.budget_export_energy_kwh),
                'budget_charge_energy_kwh': safe_val(record.budget_charge_energy_kwh),
                'budget_discharge_energy': safe_val(record.budget_discharge_energy),
                'budget_pv_grid_kwh': safe_val(record.budget_pv_grid_kwh),
                'budget_system_losses': safe_val(record.budget_system_losses),
                'budget_cuf': safe_val(record.budget_cuf),
                'budget_no_of_cycles': safe_val(record.budget_no_of_cycles),
                'budget_grid_import_kwh': safe_val(record.budget_grid_import_kwh),
                'actual_grid_import_kwh': safe_val(record.actual_grid_import_kwh),
                'budget_avg_rte': safe_val(record.budget_avg_rte),
                'created_at': record.created_at.isoformat() if record.created_at else None,
                'updated_at': record.updated_at.isoformat() if record.updated_at else None,
            })

        return JsonResponse(bess_v1_data, safe=False)
    except Exception as e:
        print(f"BESS V1 API Error: {str(e)}")
        return JsonResponse({'error': str(e)}, status=500)


@login_required
@cors_allow_same_site
def api_aoc_data(request):
    """API endpoint for Areas of Concern data"""
    try:
        # Use the filter_data_by_user_sites function for proper access control
        data = filter_data_by_user_sites(AOCData.objects.all(), 'asset_no', request)

        aoc_data = []
        for record in data:
            def safe_val(val):
                return "" if val is None or (isinstance(val, float) and math.isnan(val)) else val
            aoc_data.append({
                'id': record.id,
                's_no': safe_val(record.s_no),
                'month': safe_val(record.month),
                'asset_no': safe_val(record.asset_no),
                'country': safe_val(record.country),
                'portfolio': safe_val(record.portfolio),
                'remarks': safe_val(record.remarks),
                'created_at': record.created_at.isoformat() if record.created_at else None,
                'updated_at': record.updated_at.isoformat() if record.updated_at else None,
            })

        return JsonResponse(aoc_data, safe=False)
    except Exception as e:
        print(f"AOC API Error: {str(e)}")
        return JsonResponse({'error': str(e)}, status=500)


@login_required
def api_ice_data(request):
    """API endpoint for IC Budget vs Expected data"""
    try:
        # ICE data doesn't have asset-specific filtering, but we can filter by portfolio
        # Get user's accessible portfolios
        if user_has_capability(request.user, 'data_api.view_all'):
            data = ICEData.objects.all()
        else:
            try:
                user_profile = UserProfile.objects.get(user=request.user)
                accessible_portfolios = user_profile.get_accessible_portfolios()
                if accessible_portfolios:
                    data = ICEData.objects.filter(portfolio__in=accessible_portfolios)
                else:
                    data = ICEData.objects.none()
            except UserProfile.DoesNotExist:
                data = ICEData.objects.none()

        ice_data = []
        for record in data:
            try:
                def safe_val(val):
                    return "" if val is None or (isinstance(val, float) and math.isnan(val)) else val
                ice_data.append({
                    'month': safe_val(record.month),
                    'portfolio': safe_val(record.portfolio),
                    'ic_approved': safe_val(record.ic_approved),
                    'expected': safe_val(record.expected),
                    'created_at': record.created_at.isoformat() if record.created_at else None,
                    'updated_at': record.updated_at.isoformat() if record.updated_at else None,
                })
            except Exception as record_error:
                print(f"ICE API: Error processing record {record.id}: {str(record_error)}")
                continue
        
        
        return JsonResponse({'data': ice_data})
    except Exception as e:
        print(f"ICE API Error: {str(e)}")
        import traceback
        print(f"ICE API Error traceback: {traceback.format_exc()}")
        return JsonResponse({'error': str(e)}, status=500)


@login_required
def api_map_data(request):
    """API endpoint for map data"""
    try:

        accessible_sites = get_user_accessible_sites(request)

        
        # Check total map data count
        total_map_data = MapData.objects.all()

 
        
        # Use the filter_data_by_user_sites function for proper access control
        data = filter_data_by_user_sites(MapData.objects.all(), 'asset_no', request)

        
        map_data = []
        for record in data:
            def safe_val(val):
                return "" if val is None or (isinstance(val, float) and math.isnan(val)) else val
            map_data.append({
                'id': record.id,
                'asset_no': safe_val(record.asset_no),
                'country': safe_val(record.country),
                'site_name': safe_val(record.site_name),
                'portfolio': safe_val(record.portfolio),
                'installation_type': safe_val(record.installation_type),
                'dc_capacity_mwp': safe_val(record.dc_capacity_mwp),
                'pcs_capacity': safe_val(record.pcs_capacity),
                'battery_capacity_mw': safe_val(record.battery_capacity_mw),
                'plant_type': safe_val(record.plant_type),
                'offtaker': safe_val(record.offtaker),
                'cod': safe_val(record.cod),
                'latitude': safe_val(record.latitude),
                'longitude': safe_val(record.longitude),
                'created_at': record.created_at.isoformat() if record.created_at else None,
                'updated_at': record.updated_at.isoformat() if record.updated_at else None,
            })
  
        return JsonResponse({'data': map_data})
    except Exception as e:
        print(f"Map Data API Error: {str(e)}")
        return JsonResponse({'error': str(e)}, status=500)   


@login_required
@cors_allow_same_site
def api_minamata_string_loss_data(request):
    """API endpoint for Minamata string loss data"""
    try:
        # MinamataStringLossData doesn't have asset_no field, so return all data for now
        # TODO: Add asset_no field to MinamataStringLossData model if needed for filtering
        data = MinamataStringLossData.objects.all()

        string_loss_data = []
        for record in data:
            def safe_val(val):
                return "" if val is None or (isinstance(val, float) and math.isnan(val)) else val
            string_loss_data.append({
                'id': record.id,
                'month': safe_val(record.month),
                'no_of_strings_breakdown': safe_val(record.no_of_strings_breakdown),
                'no_of_strings_modules_damaged': safe_val(record.no_of_strings_modules_damaged),
                'designed_dc_capacity_mwh': safe_val(record.designed_dc_capacity_mwh),
                'breakdown_dc_capacity_mwh': safe_val(record.breakdown_dc_capacity_mwh),
                'operational_dc_capacity_mwh': safe_val(record.operational_dc_capacity_mwh),
                'budgeted_gen_mwh': safe_val(record.budgeted_gen_mwh),
                'actual_gen_mwh': safe_val(record.actual_gen_mwh),
                'loss_due_to_string_failure_mwh': safe_val(record.loss_due_to_string_failure_mwh),
                'loss_in_jpy': safe_val(record.loss_in_jpy),
                'loss_in_usd': safe_val(record.loss_in_usd),
                'created_at': record.created_at.isoformat() if record.created_at else None,
                'updated_at': record.updated_at.isoformat() if record.updated_at else None,
            })
        return JsonResponse(string_loss_data, safe=False)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@login_required
def api_ic_approved_budget_daily(request):
    """API endpoint for daily IC approved budget data"""
    try:
        # Use the filter_data_by_user_sites function for proper access control
        data = filter_data_by_user_sites(YieldData.objects.all(), 'assetno', request)

        
        daily_data = []
        for record in data:
            def safe_val(val):
                return "" if val is None or (isinstance(val, float) and math.isnan(val)) else val
            daily_data.append({
                'id': record.id,
                'date': record.month,  # YieldData uses month field
                'asset_code': safe_val(record.assetno),  # YieldData uses assetno field
                'ic_approved_budget_kwh': safe_val(record.ic_approved_budget),
                'created_at': record.created_at.isoformat() if record.created_at else "",
                'updated_at': record.updated_at.isoformat() if record.updated_at else "",
            })
        return JsonResponse(daily_data, safe=False)
    except Exception as e:
        print(f"IC Approved Budget Daily API Error: {str(e)}")
        return JsonResponse({'error': str(e)}, status=500)


@login_required
def api_time_series_data(request):
    """API endpoint for time series data"""
    try:
        accessible_asset_numbers = get_user_accessible_asset_numbers(request)
        
        if accessible_asset_numbers:
            data = timeseries_data.objects.filter(asset_number__in=accessible_asset_numbers)
        else:
            data = timeseries_data.objects.none()
        
        ts_data = []
        for record in data:
            def safe_val(val):
                return 0 if val is None or (isinstance(val, float) and math.isnan(val)) else val
            ts_data.append({
                'id': record.id,
                'asset_number': record.asset_number or "",
                'timestamp': record.timestamp.isoformat() if record.timestamp else "",
                'value': safe_val(record.value),
                'created_at': record.created_at.isoformat() if record.created_at else "",
                'updated_at': record.updated_at.isoformat() if record.updated_at else "",
            })
        
        return JsonResponse(ts_data, safe=False)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@login_required
def api_devices(request):
    """API endpoint for devices data"""
    return JsonResponse({'devices': [], 'message': 'Devices API endpoint'})


@login_required
def api_metrics(request):
    """API endpoint for metrics data"""
    return JsonResponse({'metrics': [], 'message': 'Metrics API endpoint'})


@login_required
def api_sites(request):
    """API endpoint for sites data"""
    try:
        accessible_asset_numbers = get_user_accessible_asset_numbers(request)
        
        if accessible_asset_numbers:
            sites = AssetList.objects.filter(asset_number__in=accessible_asset_numbers)
        else:
            sites = AssetList.objects.none()
        
        sites_data = []
        for site in sites:
            sites_data.append({
                'asset_code': site.asset_code,
                'asset_name': site.asset_name,
                'country': site.country,
                'portfolio': site.portfolio,
                'latitude': float(site.latitude) if site.latitude else None,
                'longitude': float(site.longitude) if site.longitude else None,
            })
        
        return JsonResponse(sites_data, safe=False)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@login_required
def api_actual_generation_daily(request):
    """API endpoint for actual generation daily data"""
    try:
        accessible_asset_numbers = get_user_accessible_asset_numbers(request)
        
        if accessible_asset_numbers:
            data = ActualGenerationDailyData.objects.filter(asset_number__in=accessible_asset_numbers)
        else:
            data = ActualGenerationDailyData.objects.none()
        
        gen_data = []
        for record in data:
            def safe_val(val):
                return 0 if val is None or (isinstance(val, float) and math.isnan(val)) else val
            gen_data.append({
                'id': record.id,
                'asset_number': record.asset_number or "",
                'date': record.date.isoformat() if record.date else "",
                'actual_generation': safe_val(record.actual_generation),
                'created_at': record.created_at.isoformat() if record.created_at else "",
                'updated_at': record.updated_at.isoformat() if record.updated_at else "",
            })
        
        return JsonResponse(gen_data, safe=False)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@login_required
def api_expected_budget_daily(request):
    """API endpoint for expected budget daily data"""
    try:
        accessible_asset_numbers = get_user_accessible_asset_numbers(request)
        
        if accessible_asset_numbers:
            data = ExpectedBudgetDailyData.objects.filter(asset_number__in=accessible_asset_numbers)
        else:
            data = ExpectedBudgetDailyData.objects.none()
        
        budget_data = []
        for record in data:
            def safe_val(val):
                return 0 if val is None or (isinstance(val, float) and math.isnan(val)) else val
            budget_data.append({
                'id': record.id,
                'asset_number': record.asset_number or "",
                'date': record.date.isoformat() if record.date else "",
                'expected_budget': safe_val(record.expected_budget),
                'created_at': record.created_at.isoformat() if record.created_at else "",
                'updated_at': record.updated_at.isoformat() if record.updated_at else "",
            })
        
        return JsonResponse(budget_data, safe=False)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@login_required
def api_budget_gii_daily(request):
    """API endpoint for budget GII daily data"""
    try:
        accessible_asset_numbers = get_user_accessible_asset_numbers(request)
        
        if accessible_asset_numbers:
            data = BudgetGIIDailyData.objects.filter(asset_number__in=accessible_asset_numbers)
        else:
            data = BudgetGIIDailyData.objects.none()
        
        gii_data = []
        for record in data:
            def safe_val(val):
                return 0 if val is None or (isinstance(val, float) and math.isnan(val)) else val
            gii_data.append({
                'id': record.id,
                'asset_number': record.asset_number or "",
                'date': record.date.isoformat() if record.date else "",
                'budget_gii': safe_val(record.budget_gii),
                'created_at': record.created_at.isoformat() if record.created_at else "",
                'updated_at': record.updated_at.isoformat() if record.updated_at else "",
            })
        
        return JsonResponse(gii_data, safe=False)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@login_required
def api_actual_gii_daily(request):
    """API endpoint for actual GII daily data"""
    try:
        accessible_asset_numbers = get_user_accessible_asset_numbers(request)
        
        if accessible_asset_numbers:
            data = ActualGIIDailyData.objects.filter(asset_number__in=accessible_asset_numbers)
        else:
            data = ActualGIIDailyData.objects.none()
        
        gii_data = []
        for record in data:
            def safe_val(val):
                return 0 if val is None or (isinstance(val, float) and math.isnan(val)) else val
            gii_data.append({
                'id': record.id,
                'asset_number': record.asset_number or "",
                'date': record.date.isoformat() if record.date else "",
                'actual_gii': safe_val(record.actual_gii),
                'created_at': record.created_at.isoformat() if record.created_at else "",
                'updated_at': record.updated_at.isoformat() if record.updated_at else "",
            })
        
        return JsonResponse(gii_data, safe=False)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@login_required
@cors_allow_same_site
def api_loss_calculation_data(request):
    """API endpoint for loss calculation data"""
    try:
           
        # Use the filter_data_by_user_sites function for proper access control
        data = filter_data_by_user_sites(LossCalculationData.objects.all(), 'asset_no', request)
        
        loss_data = []
        for record in data:
            def safe_val(val):
                if val is None or (isinstance(val, float) and math.isnan(val)):
                    return None  # Return None instead of empty string
                elif isinstance(val, float) and val == 0.0:
                    return 0.0  # Keep 0.0 as a number
                else:
                    return val
            loss_data.append({
                'id': record.id,
                'l': safe_val(record.l),
                'month': safe_val(record.month),
                'start_date': safe_val(record.start_date),
                'start_time': safe_val(record.start_time),
                'end_date': safe_val(record.end_date),
                'end_time': safe_val(record.end_time),
                'asset_no': safe_val(record.asset_no),
                'country': safe_val(record.country),
                'portfolio': safe_val(record.portfolio),
                'dc_capacity': safe_val(record.dc_capacity),
                'site_name': safe_val(record.site_name),
                'category': safe_val(record.category),
                'subcategory': safe_val(record.subcategory),
                'breakdown_equipment': safe_val(record.breakdown_equipment),
                'bd_description': safe_val(record.bd_description),
                'action_to_be_taken': safe_val(record.action_to_be_taken),
                'status_of_bd': safe_val(record.status_of_bd),
                'breakdown_dc_capacity_kw': safe_val(record.breakdown_dc_capacity_kw),
                'irradiation_during_breakdown_kwh_m2': safe_val(record.irradiation_during_breakdown_kwh_m2),
                'budget_pr_percent': safe_val(record.budget_pr_percent),
                'generation_loss_kwh': safe_val(record.generation_loss_kwh),
                'ppa_rate_usd': safe_val(record.ppa_rate_usd),
                'revenue_loss_usd': safe_val(record.revenue_loss_usd),
                'severity': safe_val(record.severity),
                'created_at': record.created_at.isoformat() if record.created_at else "",
                'updated_at': record.updated_at.isoformat() if record.updated_at else "",
            })
        
        
        return JsonResponse(loss_data, safe=False)
    except Exception as e:
        print(f"Loss Calculation API Error: {str(e)}")
        return JsonResponse({'error': str(e)}, status=500)


@login_required
@cors_allow_same_site
def api_asset_options(request):
    """API endpoint for asset options"""
    try:
        accessible_asset_numbers = get_user_accessible_asset_numbers(request)
        
        if accessible_asset_numbers:
            assets = AssetList.objects.filter(asset_number__in=accessible_asset_numbers)
        else:
            assets = AssetList.objects.none()
        
        asset_options = []
        for asset in assets:
            asset_options.append({
                'value': asset.asset_code,
                'label': f"{asset.asset_name} ({asset.asset_code})",
                'country': asset.country,
                'portfolio': asset.portfolio,
            })
        
        return JsonResponse(asset_options, safe=False)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@login_required
def api_kpi_v1_asset_options(request):
    """API endpoint for KPI v1 asset options"""
    return api_asset_options(request)


#@csrf_exempt
@login_required
@login_required
@feature_required('data_upload')
def api_upload_csv(request):
    """API endpoint for CSV upload (JSON response for React)"""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Method not allowed'}, status=405)
    
    try:
        if 'csv_file' not in request.FILES:
            return JsonResponse({
                'success': False,
                'error': 'No file uploaded'
            }, status=400)
        
        file = request.FILES['csv_file']
        data_type = request.POST.get('data_type', 'unknown')
        upload_mode = request.POST.get('upload_mode', 'append')
        
        # Get optional parameters
        start_date = request.POST.get('start_date')
        end_date = request.POST.get('end_date')
        skip_duplicates = request.POST.get('skip_duplicates', 'true').lower() == 'true'
        validate_data = request.POST.get('validate_data', 'true').lower() == 'true'
        batch_size = int(request.POST.get('batch_size', '1000'))
        
        # Import the process_csv_upload function
        from .data_upload_views import process_csv_upload
        
        # Process the upload
        result = process_csv_upload(
            csv_file=file,
            data_type=data_type,
            upload_mode=upload_mode,
            start_date=start_date,
            end_date=end_date,
            skip_duplicates=skip_duplicates,
            validate_data=validate_data,
            batch_size=batch_size,
            user=request.user
        )
        
        # Return JSON response
        if result.get('success', False):
            return JsonResponse({
                'success': True,
                'records_imported': result.get('records_imported', 0),
                'records_skipped': result.get('records_skipped', 0),
                'records_updated': result.get('records_updated', 0),
                'warnings': result.get('warnings', [])
            })
        else:
            return JsonResponse({
                'success': False,
                'error': result.get('error', 'Upload failed'),
                'validation_details': result.get('validation_details')
            }, status=400)
            
    except Exception as e:
        import traceback
        traceback.print_exc()
        return JsonResponse({
            'success': False,
            'error': f'Error during upload: {str(e)}'
        }, status=500)


@login_required
def api_analyze_file_encoding(request):
    """API endpoint for analyzing file encoding"""
    if request.method == 'POST':
        try:
            # File encoding analysis logic here
            return JsonResponse({
                'encoding': 'utf-8',
                'confidence': 0.99,
                'status': 'success'
            })
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)
    
    return JsonResponse({'error': 'Method not allowed'}, status=405)


@login_required
def api_data_preview(request, data_type):
    """API endpoint for data preview"""
    try:
        # Data preview logic here
        return JsonResponse({
            'data_type': data_type,
            'preview': [],
            'total_records': 0,
            'status': 'success'
        })
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)
