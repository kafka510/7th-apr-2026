"""
Portfolio map views and related functionality
"""
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from accounts.decorators import feature_required
from waffle.decorators import flag_is_active
from ..models import (
    YieldData, MapData
)
import json, math
from .shared.utilities import (
	filter_data_by_user_sites
)



@feature_required('portfolio_map')
@login_required
def portfolio_map_view(request):
    """Portfolio map view with data passed directly to template"""
    # Check if React version should be used
    if flag_is_active(request, 'react_portfolio_map'):
        return render(request, 'main/portfolio_map_react.html')
    
    try:
        # Use the filter_data_by_user_sites function for proper access control
        map_data_queryset = filter_data_by_user_sites(MapData.objects.all(), 'asset_no', request)
        yield_data_queryset = filter_data_by_user_sites(YieldData.objects.all(), 'assetno', request)
       
        
       
        map_data = []
        for record in map_data_queryset:
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
       
        # Process yield data for performance calculations
        yield_data = []
        for record in yield_data_queryset:
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
                'actual_generation': safe_val(record.actual_generation),
                'created_at': record.created_at.isoformat() if record.created_at else "",
                'updated_at': record.updated_at.isoformat() if record.updated_at else "",
            })
       
        return render(request, 'main/map portfolio_v2.html', {
            'map_data_json': json.dumps(map_data),
            'yield_data_json': json.dumps(yield_data)
        })
    except Exception as e:
        return render(request, 'main/map portfolio_v2.html', {
            'map_data_json': json.dumps([]),
            'yield_data_json': json.dumps([]),
            'error_message': str(e)
        })
