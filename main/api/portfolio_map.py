"""
Portfolio Map API endpoints
"""
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from accounts.decorators import feature_required
import math
from datetime import datetime
from ..models import YieldData, MapData, budget_values, AssetList
from ..views.shared.utilities import filter_data_by_user_sites


@login_required
@feature_required('portfolio_map')
def portfolio_map_data_view(request):
    """
    API endpoint to fetch portfolio map data
    Returns map data and yield data for the portfolio map page
    Uses function-based view with JsonResponse to bypass DRF pagination
    """
    try:
        # Use the filter_data_by_user_sites function for proper access control
        map_data_queryset = filter_data_by_user_sites(MapData.objects.all(), 'asset_no', request)
        yield_data_queryset = filter_data_by_user_sites(YieldData.objects.all(), 'assetno', request)
        
        # Helper function to safely convert value
        def safe_val(val):
            if val is None or (isinstance(val, float) and math.isnan(val)):
                return ""
            return val
        
        # Helper function to safely convert numeric coordinates
        def safe_coord(val):
            if val is None:
                return None
            if isinstance(val, float) and math.isnan(val):
                return None
            # Convert Decimal to float for JSON serialization
            if hasattr(val, '__float__'):
                try:
                    return float(val)
                except (ValueError, TypeError):
                    return None
            try:
                return float(val)
            except (ValueError, TypeError):
                return None
        
        # Process map data
        map_data = []
        countries_found = set()
        for record in map_data_queryset:
            country_val = safe_val(record.country)
            countries_found.add(country_val)
            map_data.append({
                'id': record.id,
                'asset_no': safe_val(record.asset_no),
                'country': country_val,
                'site_name': safe_val(record.site_name),
                'portfolio': safe_val(record.portfolio),
                'installation_type': safe_val(record.installation_type),
                'dc_capacity_mwp': safe_val(record.dc_capacity_mwp),
                'pcs_capacity': safe_val(record.pcs_capacity),
                'battery_capacity_mw': safe_val(record.battery_capacity_mw),
                'plant_type': safe_val(record.plant_type),
                'offtaker': safe_val(record.offtaker),
                'cod': safe_val(record.cod),
                'latitude': safe_coord(record.latitude),
                'longitude': safe_coord(record.longitude),
                'created_at': record.created_at.isoformat() if record.created_at else None,
                'updated_at': record.updated_at.isoformat() if record.updated_at else None,
            })
        
        # Process yield data for performance calculations
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
                'actual_generation': safe_val(record.actual_generation),
                'created_at': record.created_at.isoformat() if record.created_at else "",
                'updated_at': record.updated_at.isoformat() if record.updated_at else "",
            })
        
        # Get asset numbers from map data (MapData.asset_no)
        # Field mappings:
        # - MapData.asset_no -> budget_values.asset_number
        # - MapData.asset_no -> asset_list.asset_number
        asset_numbers_from_map = [safe_val(record.asset_no) for record in map_data_queryset if safe_val(record.asset_no)]
        
        # Fetch budget values and asset details for budget calculation
        budget_data = []
        asset_details = {}
        
        if asset_numbers_from_map:
            # 1. Get budget values (Y0 monthly budgets)
            # MapData.asset_no matches budget_values.asset_number
            budget_queryset = budget_values.objects.filter(
                asset_number__in=asset_numbers_from_map
            )
            
            for budget_record in budget_queryset:
                budget_data.append({
                    'asset_code': safe_val(budget_record.asset_code),
                    'asset_number': safe_val(budget_record.asset_number),
                    'month_str': safe_val(budget_record.month_str),
                    'month_date': budget_record.month_date.isoformat() if budget_record.month_date else None,
                    'bd_production': float(budget_record.bd_production) if budget_record.bd_production is not None else None,
                    'bd_ghi': float(budget_record.bd_ghi) if budget_record.bd_ghi is not None else None,
                    'bd_gti': float(budget_record.bd_gti) if budget_record.bd_gti is not None else None,
                })
            
            # 2. Get asset details (COD, degradation values) for budget calculation
            # MapData.asset_no matches AssetList.asset_number
            asset_list_queryset = AssetList.objects.filter(
                asset_number__in=asset_numbers_from_map
            )
            
            for asset in asset_list_queryset:
                asset_code_key = safe_val(asset.asset_code)
                asset_number_key = safe_val(asset.asset_number)
                
                # Create entry data
                entry_data = {
                    'asset_code': asset_code_key,
                    'asset_number': asset_number_key,
                    'cod': asset.cod.isoformat() if asset.cod else None,
                    'y1_degradation': float(asset.y1_degradation) if asset.y1_degradation is not None else None,
                    'anual_degradation': float(asset.anual_degradation) if asset.anual_degradation is not None else None,
                    'capacity': float(asset.capacity) if asset.capacity is not None else None,
                }
                
                # Key by asset_number (MapData.asset_no matches AssetList.asset_number)
                if asset_number_key:
                    asset_details[asset_number_key] = entry_data
                
                # Also key by asset_code for potential lookup
                if asset_code_key:
                    asset_details[asset_code_key] = entry_data
        
        response_data = {
            'mapData': map_data,
            'yieldData': yield_data,
            'budgetData': budget_data,
            'assetDetails': asset_details,
        }
        
        # Return JsonResponse directly - bypasses DRF pagination completely
        response = JsonResponse(response_data, status=200)
        # Add cache control headers to prevent caching
        response['Cache-Control'] = 'no-cache, no-store, must-revalidate'
        response['Pragma'] = 'no-cache'
        response['Expires'] = '0'
        return response
        
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Portfolio map error: {str(e)}", exc_info=True)
        return JsonResponse({
            'error': f'An error occurred while loading the portfolio map: {str(e)}'
        }, status=500)

