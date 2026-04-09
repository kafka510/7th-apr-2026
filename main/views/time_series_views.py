"""
Time Series Dashboard views
"""
from django.shortcuts import render
from django.contrib.auth.decorators import login_required

from accounts.decorators import feature_required

from ..models import (
    MapData
)

import json, math

from .shared.utilities import (
	get_user_accessible_sites
)


# Time Series Dashboard Views
@feature_required('time_series_dashboard')
@login_required
def time_series_dashboard_view(request):
    """Time series dashboard view with data passed directly to template"""
    try:
        # Get user accessible sites
        accessible_sites = get_user_accessible_sites(request)
        
        if accessible_sites:
            # Filter by accessible sites - MapData uses asset_no, AssetList uses asset_number
            data = MapData.objects.filter(asset_no__in=accessible_sites)
        else:
            # If no sites assigned, return empty queryset
            data = MapData.objects.none()
        
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
        
        return render(request, 'main/Energy_Monitoring.html', {
            'map_data_json': json.dumps(map_data)
        })
    except Exception as e:
        return render(request, 'main/Energy_Monitoring.html', {
            'map_data_json': json.dumps([]),
            'error_message': str(e)
        })
