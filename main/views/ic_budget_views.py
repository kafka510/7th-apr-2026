"""
IC Budget vs Expected analysis views
"""
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
import math
import json
from accounts.decorators import feature_required

from ..models import (
    ICVSEXVSCURData, AssetList
)

import json, math


from .shared.utilities import (
    get_user_accessible_sites
)


@feature_required('ic_budget_vs_expected')
@login_required
def ic_budget_vs_expected_view(request):
    """IC Budget vs Expected view - supports both React and legacy templates"""
    try:
        # Check if React version is enabled via waffle flag
        from waffle import flag_is_active
        use_react = flag_is_active(request, 'react_ic_budget')
        
        if use_react:
            # Render React version - data will be fetched via API
            return render(request, 'main/ic_budget_react.html')
        
        # Legacy template with data passed directly
        # Get user accessible sites
        accessible_sites = get_user_accessible_sites(request)
        
        if accessible_sites:
            # Filter by accessible sites - ICVSEXVSCURData uses portfolio, we'll filter by portfolio
            # Get portfolios from accessible sites
            accessible_portfolios = []
            for site in accessible_sites:
                try:
                    asset = AssetList.objects.get(asset_number=site)
                    accessible_portfolios.append(asset.portfolio)
                except AssetList.DoesNotExist:
                    continue
            
            if accessible_portfolios:
                icvsexvscur_data = ICVSEXVSCURData.objects.filter(portfolio__in=accessible_portfolios)
            else:
                icvsexvscur_data = ICVSEXVSCURData.objects.all()
        else:
            # If no sites assigned, return all data
            icvsexvscur_data = ICVSEXVSCURData.objects.all()
        
        icvsexvscur_data_list = []
        for record in icvsexvscur_data:
            def safe_val(val):
                return "" if val is None or (isinstance(val, float) and math.isnan(val)) else val
            icvsexvscur_data_list.append({
                'id': record.id,
                'country': safe_val(record.country),
                'portfolio': safe_val(record.portfolio),
                'dc_capacity_mwp': safe_val(record.dc_capacity_mwp),
                'month': record.month.strftime('%b %Y') if record.month else "",  # Format as "Apr 2025"
                'month_sort': record.month.isoformat() if record.month else "",  # For sorting purposes
                'ic_approved_budget_mwh': safe_val(record.ic_approved_budget_mwh),
                'expected_budget_mwh': safe_val(record.expected_budget_mwh),
                'actual_generation_mwh': safe_val(record.actual_generation_mwh),
                'grid_curtailment_budget_mwh': safe_val(record.grid_curtailment_budget_mwh),
                'actual_curtailment_mwh': safe_val(record.actual_curtailment_mwh),
                'budget_irradiation_kwh_m2': safe_val(record.budget_irradiation_kwh_m2),
                'actual_irradiation_kwh_m2': safe_val(record.actual_irradiation_kwh_m2),
                'expected_pr_percent': safe_val(record.expected_pr_percent),
                'actual_pr_percent': safe_val(record.actual_pr_percent),
                'created_at': record.created_at.isoformat() if record.created_at else None,
                'updated_at': record.updated_at.isoformat() if record.updated_at else None,
            })
        
        print(f"IC Budget vs Expected - ICVSEXVSCUR data: {len(icvsexvscur_data_list)} records")
        
        return render(request, 'main/IC Budget Vs Expected.html', {
            'icvsexvscur_data_json': json.dumps(icvsexvscur_data_list)
        })
    except Exception as e:
        print(f"Error in ic_budget_vs_expected_view: {str(e)}")
        import traceback
        traceback.print_exc()
        return render(request, 'main/IC Budget Vs Expected.html', {
            'icvsexvscur_data_json': json.dumps([]),
            'error_message': str(e)
        })