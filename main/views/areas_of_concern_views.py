"""
Areas of Concern views
"""
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from waffle.decorators import flag_is_active
from accounts.decorators import feature_required
from ..models import (
    AOCData
)
from .shared.utilities import *
import json, math


@feature_required('areas_of_concern')
@login_required
def areas_of_concern_view(request):
    """Areas of concern view - data is loaded via API endpoints"""
    if flag_is_active(request, 'react_areas_of_concern'):
        return render(request, 'main/AOC_react.html')
    try:
        # Debug: Check total AOC data available
        total_aoc_data = AOCData.objects.count()
        
        
        # Debug: Check what asset numbers are in AOCData
        aoc_asset_numbers = AOCData.objects.values_list('asset_no', flat=True).distinct()
        
        
        # Debug: Check user accessible sites
        accessible_sites = get_user_accessible_sites(request)
        
        if accessible_sites and accessible_sites.exists():
            accessible_asset_numbers = list(accessible_sites.values_list('asset_number', flat=True))
            
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
        
        
        
        # Check if the JSON is being created correctly
        json_data = json.dumps(aoc_data)
        
        
        return render(request, 'main/AOC.html', {
            'aoc_data_json': json_data
        })
    except Exception as e:
        print(f"DEBUG: AOC - Error: {str(e)}")
        return render(request, 'main/AOC.html', {
            'aoc_data_json': json.dumps([]),
            'error_message': str(e)
        })