"""
BESS Performance views
"""
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from accounts.decorators import feature_required
from waffle.decorators import flag_is_active

from django.contrib.auth.decorators import login_required
from django.http import JsonResponse

import math
import json

from accounts.decorators import role_required, feature_required
import logging
from functools import wraps

from ..models import (
    BESSData,
    BESSV1Data,
)

import json, math
from .shared.utilities import *
from main.permissions import user_has_capability
from datetime import datetime

logger = logging.getLogger(__name__)


@feature_required('bess_performance')
@login_required
def bess_performance_view(request):
    """BESS performance view with flag-based React/legacy switching"""
    if flag_is_active(request, 'react_bess_performance'):
        return render(request, 'main/bess_v2_react.html')
    
    """BESS performance view with data passed directly to template"""
    try:
        # Users with global data access can view all BESS records
        if user_has_capability(request.user, 'data_api.view_all'):
            # For admin users, show all BESS data (including records without energy data)
            data = BESSData.objects.all()
            
        else:
            # For non-admin users, filter by accessible sites
            accessible_asset_numbers = get_user_accessible_asset_numbers(request)
            
            
            if accessible_asset_numbers:
                # Filter by accessible sites - BESSData uses asset_no, AssetList uses asset_number
                # Include all records, even those without energy data
                data = BESSData.objects.filter(
                    asset_no__in=accessible_asset_numbers
                )
                
            else:
                # If no sites assigned, return empty queryset
                data = BESSData.objects.none()
      
        
        bess_data = []
        for record in data:
            def safe_val(val):
                if val is None:
                    return None
                elif isinstance(val, float) and math.isnan(val):
                    return None
                else:
                    return val  # Return the original value
            
                        
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
                'actual_no_of_cycles': safe_val(record.actual_no_of_cycles),
                'cuf': safe_val(record.cuf),
                'created_at': record.created_at.isoformat() if record.created_at else None,
                'updated_at': record.updated_at.isoformat() if record.updated_at else None,
            })
        
        return render(request, 'main/bess_v2.html', {
            'bess_data_json': json.dumps(bess_data)
        })
    except Exception as e:
        print(f"BESS API Error: {str(e)}")
        return render(request, 'main/bess_v2.html', {
            'bess_data_json': json.dumps([]),
            'error_message': str(e)
        })


@feature_required('bess_v1_performance')
@login_required
def bess_v1_performance_view(request):
    """Render the enhanced BESS dashboard with server-side data."""
    if flag_is_active(request, 'react_bess_v1_dashboard'):
        return render(request, 'main/bess_v1_dashboard_react.html')

    try:
        if user_has_capability(request.user, 'data_api.view_all'):
            data_qs = BESSV1Data.objects.all()
        else:
            accessible_asset_numbers = get_user_accessible_asset_numbers(request)
            if accessible_asset_numbers:
                data_qs = BESSV1Data.objects.filter(asset_no__in=accessible_asset_numbers)
            else:
                data_qs = BESSV1Data.objects.none()

        fields = [
            'month',
            'country',
            'portfolio',
            'asset_no',
            'battery_capacity_mwh',
            'actual_pv_energy_kwh',
            'actual_export_energy_kwh',
            'actual_charge_energy_kwh',
            'actual_discharge_energy',
            'actual_pv_grid_kwh',
            'actual_system_losses',
            'min_soc',
            'max_soc',
            'min_ess_temp',
            'max_ess_temp',
            'actual_avg_rte',
            'actual_cuf',
            'actual_no_of_cycles',
            'budget_pv_energy_kwh',
            'budget_export_energy_kwh',
            'budget_charge_energy_kwh',
            'budget_discharge_energy',
            'budget_pv_grid_kwh',
            'budget_system_losses',
            'budget_cuf',
            'budget_no_of_cycles',
            'budget_grid_import_kwh',
            'actual_grid_import_kwh',
            'budget_avg_rte',
        ]

        records = list(data_qs.values(*fields))

        record_count = len(records)
        asset_count = len({row['asset_no'] for row in records if row.get('asset_no')})
        months = sorted({row['month'] for row in records if row.get('month')})

        def format_month(month_str):
            try:
                return datetime.strptime(month_str, '%Y-%m').strftime('%b %Y')
            except Exception:
                return month_str

        dataset_range = None
        if months:
            first_month = months[0]
            last_month = months[-1]
            if first_month == last_month:
                dataset_range = format_month(first_month)
            else:
                dataset_range = f"{format_month(first_month)} – {format_month(last_month)}"

        return render(
            request,
            'main/bess_v1_dashboard.html',
            {
                'bess_v1_data_json': json.dumps(records, default=str),
                'dataset_range': dataset_range,
                'record_count': record_count,
                'asset_count': asset_count,
            },
        )
    except Exception as exc:
        logger.error("Error rendering BESS dashboard: %s", exc, exc_info=True)
        return render(
            request,
            'main/bess_v1_dashboard.html',
            {
                'bess_v1_data_json': json.dumps([]),
                'dataset_range': None,
                'record_count': 0,
                'asset_count': 0,
                'error_message': str(exc),
            },
        )
