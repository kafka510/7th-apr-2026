"""
API views for loss calculations

Endpoints for triggering loss calculations and viewing results.
"""
import json
import logging
from datetime import datetime, timedelta
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from django.db.models import Q

from main.models import device_list, AssetList, timeseries_data
from main.calculations.tasks import (
    calculate_string_loss,
    calculate_strings_batch,
    calculate_jb_loss,
    calculate_inverter_loss,
    calculate_asset_losses,
    run_asset_loss_for_date_range,
)
from main.calculations.calculation_service import CalculationService
from main.calculations.metric_mapping_service import MetricMappingService
from main.calculations.timeseries_reader import TimeseriesReader
from accounts.decorators import role_required

logger = logging.getLogger(__name__)


@login_required
@role_required(allowed_roles=['admin'])
@require_http_methods(["POST"])
def api_trigger_string_calculation(request):
    """
    Trigger loss calculation for a single string device (synchronous for testing).
    
    POST /api/loss-calculation/string/
    {
        "device_id": "IJ_SUB_02.PV.P1-1-L02.JB_02_string_1",
        "start_date": "2025-12-07T00:00:00Z",
        "end_date": "2025-12-07T23:59:59Z",
        "time_interval_minutes": 15  // optional, default 15
    }
    """
    try:
        data = json.loads(request.body)
        device_id = data.get('device_id')
        start_date_str = data.get('start_date')
        end_date_str = data.get('end_date')
        time_interval_minutes = int(data.get('time_interval_minutes', 15))
        
        if not device_id:
            return JsonResponse({'error': 'device_id is required'}, status=400)
        
        if not start_date_str or not end_date_str:
            return JsonResponse({
                'error': 'start_date and end_date are required'
            }, status=400)
        
        # Parse dates and ensure they're timezone-aware
        try:
            # Try parsing with timezone first
            if 'Z' in start_date_str or '+' in start_date_str or start_date_str.count('-') > 2:
                start_date = datetime.fromisoformat(start_date_str.replace('Z', '+00:00'))
            else:
                # Naive datetime from datetime-local input - make it timezone-aware
                start_date = datetime.fromisoformat(start_date_str)
                if timezone.is_naive(start_date):
                    start_date = timezone.make_aware(start_date)
            
            if 'Z' in end_date_str or '+' in end_date_str or end_date_str.count('-') > 2:
                end_date = datetime.fromisoformat(end_date_str.replace('Z', '+00:00'))
            else:
                # Naive datetime from datetime-local input - make it timezone-aware
                end_date = datetime.fromisoformat(end_date_str)
                if timezone.is_naive(end_date):
                    end_date = timezone.make_aware(end_date)
        except ValueError:
            return JsonResponse({'error': 'Invalid date format'}, status=400)
        
        # Run synchronous calculation
        calc_service = CalculationService()
        result = calc_service.calculate_string_loss_sync(
            device_id=device_id,
            start_date=start_date,
            end_date=end_date,
            time_interval_minutes=time_interval_minutes
        )
        
        return JsonResponse(result)
        
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)
    except Exception as e:
        logger.error(f"Error in string calculation: {e}", exc_info=True)
        return JsonResponse({'error': str(e)}, status=500)


@login_required
@role_required(allowed_roles=['admin'])
@require_http_methods(["POST"])
def api_trigger_strings_batch(request):
    """
    Trigger loss calculations for multiple string devices.
    
    POST /api/loss-calculation/strings/batch/
    {
        "device_ids": ["string_1", "string_2", ...],
        "timestamp": "2025-12-05T14:30:00Z"  // optional
    }
    """
    try:
        data = json.loads(request.body)
        device_ids = data.get('device_ids', [])
        timestamp_str = data.get('timestamp')
        
        if not device_ids:
            return JsonResponse({'error': 'device_ids is required'}, status=400)
        
        # Parse timestamp if provided
        timestamp = None
        if timestamp_str:
            try:
                timestamp = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
            except ValueError:
                return JsonResponse({'error': 'Invalid timestamp format'}, status=400)
        
        # Trigger batch task
        task = calculate_strings_batch.delay(device_ids, timestamp)
        
        return JsonResponse({
            'success': True,
            'task_id': task.id,
            'device_count': len(device_ids),
            'message': 'Batch calculation task queued'
        })
        
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)
    except Exception as e:
        logger.error(f"Error triggering batch calculation: {e}", exc_info=True)
        return JsonResponse({'error': str(e)}, status=500)


@login_required
@role_required(allowed_roles=['admin'])
@require_http_methods(["POST"])
def api_trigger_asset_calculation(request):
    """
    Trigger loss calculations for all devices in an asset.
    
    POST /api/loss-calculation/asset/
    {
        "asset_code": "ASSET_KR_49",
        "timestamp": "2025-12-05T14:30:00Z",  // optional
        "device_types": ["string", "jb", "inverter"]  // optional
    }
    """
    try:
        data = json.loads(request.body)
        asset_code = data.get('asset_code')
        timestamp_str = data.get('timestamp')
        device_types = data.get('device_types')
        
        if not asset_code:
            return JsonResponse({'error': 'asset_code is required'}, status=400)
        
        # Verify asset exists
        try:
            asset = AssetList.objects.get(asset_code=asset_code)
        except AssetList.DoesNotExist:
            return JsonResponse({'error': f'Asset {asset_code} not found'}, status=404)
        
        # Parse timestamp if provided
        timestamp = None
        if timestamp_str:
            try:
                timestamp = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
            except ValueError:
                return JsonResponse({'error': 'Invalid timestamp format'}, status=400)
        
        # Trigger asset calculation task
        task = calculate_asset_losses.delay(asset_code, timestamp, device_types)
        
        return JsonResponse({
            'success': True,
            'task_id': task.id,
            'asset_code': asset_code,
            'asset_name': asset.asset_name,
            'message': 'Asset calculation task queued'
        })
        
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)
    except Exception as e:
        logger.error(f"Error triggering asset calculation: {e}", exc_info=True)
        return JsonResponse({'error': str(e)}, status=500)


@login_required
@role_required(allowed_roles=['admin'])
@require_http_methods(["POST"])
def api_trigger_asset_range_calculation(request):
    """
    Trigger loss calculation for all configured+enabled string devices in an asset over a date range.

    POST /api/loss-calculation/asset/range/
    {
        "asset_code": "ASSET_KR_49",
        "start_date": "2025-12-01",          // or full ISO datetime
        "end_date": "2025-12-07",
        "time_interval_minutes": 15          // optional, default 15
    }

    This endpoint enqueues a Celery task (run_asset_loss_for_date_range) and returns task_id.
    It does not run calculations synchronously.
    """
    try:
        data = json.loads(request.body)
        asset_code = data.get("asset_code")
        start_date = data.get("start_date")
        end_date = data.get("end_date")
        time_interval_minutes = int(data.get("time_interval_minutes", 15))

        if not asset_code:
            return JsonResponse({"error": "asset_code is required"}, status=400)
        if not start_date or not end_date:
            return JsonResponse(
                {"error": "start_date and end_date are required"},
                status=400,
            )

        # Verify asset exists (for friendlier response)
        try:
            asset = AssetList.objects.get(asset_code=asset_code)
        except AssetList.DoesNotExist:
            return JsonResponse(
                {"error": f"Asset {asset_code} not found"}, status=404
            )

        task = run_asset_loss_for_date_range.delay(
            asset_code=asset_code,
            start_date=start_date,
            end_date=end_date,
            time_interval_minutes=time_interval_minutes,
        )

        return JsonResponse(
            {
                "success": True,
                "task_id": task.id,
                "asset_code": asset_code,
                "asset_name": asset.asset_name,
                "start_date": start_date,
                "end_date": end_date,
                "message": "Asset range loss calculation task queued",
            }
        )

    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON"}, status=400)
    except Exception as e:
        logger.error(
            f"Error triggering asset range calculation: {e}", exc_info=True
        )
        return JsonResponse({"error": str(e)}, status=500)


@login_required
@role_required(allowed_roles=['admin'])
@require_http_methods(["GET"])
def api_get_loss_results(request):
    """
    Get loss calculation results for a device.
    
    GET /api/loss-calculation/results/?device_id=...&start_time=...&end_time=...
    """
    try:
        device_id = request.GET.get('device_id')
        start_time_str = request.GET.get('start_time')
        end_time_str = request.GET.get('end_time')
        metric = request.GET.get('metric')  # e.g., 'string_expected_power', 'string_actual_power'
        
        if not device_id:
            return JsonResponse({'error': 'device_id is required'}, status=400)
        
        # Parse time range
        end_time = timezone.now()
        if end_time_str:
            try:
                end_time = datetime.fromisoformat(end_time_str.replace('Z', '+00:00'))
            except ValueError:
                return JsonResponse({'error': 'Invalid end_time format'}, status=400)
        
        start_time = end_time - timedelta(days=7)  # Default: last 7 days
        if start_time_str:
            try:
                start_time = datetime.fromisoformat(start_time_str.replace('Z', '+00:00'))
            except ValueError:
                return JsonResponse({'error': 'Invalid start_time format'}, status=400)
        
        # Build query
        query = Q(
            device_id=device_id,
            ts__gte=start_time,
            ts__lte=end_time
        )
        
        # Filter by metric if provided
        if metric:
            query &= Q(metric=metric)
        else:
            # Default: get all loss-related metrics
            query &= (
                Q(metric__icontains='expected_power') |
                Q(metric__icontains='actual_power') |
                Q(metric__icontains='power_loss') |
                Q(metric__icontains='loss_percentage')
            )
        
        # Query timeseries_data
        data = timeseries_data.objects.filter(query).order_by('ts')
        
        results = []
        for row in data:
            try:
                value = float(row.value)
            except (ValueError, TypeError):
                continue
            
            results.append({
                'timestamp': row.ts.isoformat(),
                'metric': row.metric,
                'oem_metric': row.oem_metric,
                'value': value
            })
        
        return JsonResponse({
            'success': True,
            'device_id': device_id,
            'start_time': start_time.isoformat(),
            'end_time': end_time.isoformat(),
            'count': len(results),
            'data': results
        })
        
    except Exception as e:
        logger.error(f"Error getting loss results: {e}", exc_info=True)
        return JsonResponse({'error': str(e)}, status=500)


@login_required
@role_required(allowed_roles=['admin'])
@require_http_methods(["GET"])
def api_get_loss_summary(request):
    """
    Get loss calculation summary for a device or asset.
    
    GET /api/loss-calculation/summary/?device_id=...&hours=24
    GET /api/loss-calculation/summary/?asset_code=...&hours=24
    """
    try:
        device_id = request.GET.get('device_id')
        asset_code = request.GET.get('asset_code')
        hours = int(request.GET.get('hours', 24))

        if not device_id and not asset_code:
            return JsonResponse({'error': 'device_id or asset_code is required'}, status=400)

        calc_service = CalculationService()
        summary = calc_service.get_loss_summary(
            device_id=device_id,
            asset_code=asset_code,
            hours=hours,
        )

        return JsonResponse(
            {
                'success': True,
                'summary': summary,
            }
        )
        
    except Exception as e:
        logger.error(f"Error getting loss summary: {e}", exc_info=True)
        return JsonResponse({'error': str(e)}, status=500)


@login_required
@role_required(allowed_roles=['admin'])
@require_http_methods(["GET"])
def api_get_metric_mappings(request):
    """
    Get current metric mappings from device_mapping.
    
    GET /api/loss-calculation/metric-mappings/
    """
    try:
        from main.models import device_mapping
        
        # Debug: Check what's actually in the database
        total_count = device_mapping.objects.filter(asset_code='loss_metrics').count()
        sample_rows = list(device_mapping.objects.filter(
            asset_code='loss_metrics'
        ).values('device_type', 'metric', 'oem_tag', 'asset_code')[:10])
        
        # Get all unique asset_codes to help debug
        all_asset_codes = list(device_mapping.objects.values_list('asset_code', flat=True).distinct()[:20])
        
        mapper = MetricMappingService()
        mappings = mapper.get_metric_mappings(force_refresh=True)
        
        # Format for API response
        formatted = {}
        for device_type, metrics in mappings.items():
            formatted[device_type] = {
                metric_name: {
                    'oem_tag': info['oem_tag'],
                    'units': info['units'],
                    'description': info['description']
                }
                for metric_name, info in metrics.items()
            }
        
        # Also return validation status
        validation = mapper.validate_mappings()
        
        return JsonResponse({
            'success': True,
            'debug': {
                'total_rows_with_loss_metrics': total_count,
                'sample_rows': sample_rows,
                'all_asset_codes_sample': all_asset_codes
            },
            'mappings': formatted,
            'validation': validation
        })
        
    except Exception as e:
        logger.error(f"Error getting metric mappings: {e}", exc_info=True)
        return JsonResponse({'error': str(e)}, status=500)

