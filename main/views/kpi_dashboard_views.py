"""
KPI Dashboard views and API endpoints
"""
import json

from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import render

from accounts.decorators import feature_required
from main.decorators.cors_decorator import cors_allow_same_site
from main.services.kpi_service import KPIService
from waffle import flag_is_active


@feature_required('kpi_dashboard')
@login_required
def kpi_dashboard_view(request):
    """Render the legacy KPI dashboard while sourcing data via the shared service layer."""
    # Check if React version should be used
    if flag_is_active(request, 'react_kpi_beta'):
        # React version fetches its own data via API, no need for server-side payload
        return render(request, 'main/KPI_react.html', {})
    
    # Legacy version requires server-side data
    try:
        service = KPIService(request)
        payload = service.get_dashboard_payload()
        return render(
            request,
            'main/KPI.html',
            {
                'kpi_data_json': json.dumps(payload['realtime']),
                'yield_data_json': json.dumps(payload['yield']),
            },
        )
    except Exception as exc:
        return render(
            request,
            'main/KPI.html',
            {
                'kpi_data_json': json.dumps([]),
                'yield_data_json': json.dumps([]),
                'error_message': str(exc),
            },
        )



@feature_required('kpi_dashboard')
@login_required
@cors_allow_same_site
def api_real_time_kpi_data(request):
    """API endpoint to get real-time KPI data"""
    try:
        filters = {
            'date': request.GET.get('date'),
            'asset_codes': [code for code in request.GET.get('asset_codes', '').split(',') if code],
            'countries': [country for country in request.GET.get('countries', '').split(',') if country],
            'portfolios': [portfolio for portfolio in request.GET.get('portfolios', '').split(',') if portfolio],
        }
        service = KPIService(request)
        kpi_data = service.get_realtime_entries(filters)
        return JsonResponse({
            'success': True,
            'data': kpi_data,
            'count': len(kpi_data)
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@feature_required('kpi_dashboard') 
@login_required
def api_kpi_summary_stats(request):
    """API endpoint to get KPI summary statistics"""
    try:
        service = KPIService(request)
        summary = service.get_summary()
        return JsonResponse({
            'success': True,
            'data': summary,
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)