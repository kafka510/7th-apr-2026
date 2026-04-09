"""
Minamata typhoon damage analysis views
"""
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from accounts.decorators import feature_required
from waffle.decorators import flag_is_active
from ..models import (
    MinamataStringLossData
)
import json, math


@feature_required('minamata_typhoon_damage')
@login_required
def minamata_typhoon_damage_view(request):
    """Minamata typhoon damage view with flag-based React/legacy switching"""
    if flag_is_active(request, 'react_minamata_typhoon_damage'):
        return render(request, 'main/Minamata_string_loss_react.html')
    
    try:
        # MinamataStringLossData doesn't have asset_no field, so return all data for now
        # TODO: Add asset_no field to MinamataStringLossData model if needed for filtering
        data = MinamataStringLossData.objects.all()
        
        minamata_data = []
        for record in data:
            def safe_val(val):
                return "" if val is None or (isinstance(val, float) and math.isnan(val)) else val
            minamata_data.append({
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
        
        return render(request, 'main/Minamata_string_loss.html', {
            'minamata_data_json': json.dumps(minamata_data)
        })
    except Exception as e:
        return render(request, 'main/Minamata_string_loss.html', {
            'minamata_data_json': json.dumps([]),
            'error_message': str(e)
        })
