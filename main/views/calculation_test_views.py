"""
Test page views for loss calculations

Provides a UI for testing calculations without Celery.
"""
import json
import time
from datetime import datetime, timezone as dt_timezone
import re

from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.db.models import Q
from django.utils import timezone as django_timezone

from accounts.decorators import role_required
from main.decorators.cors_decorator import cors_allow_same_site
from main.models import device_list, AssetList, timeseries_data
from loss_analytics.calculations import (
    ghi_to_gii,
    gii_device_id,
    TimeseriesWriter,
    compute_and_persist_inverter_expected_power,
    upload_satellite_ghi_temp_csv,
)
from loss_analytics.pipeline.config_resolver import get_configured_string_devices_for_asset
from .shared.utilities import get_user_accessible_sites

import logging

logger = logging.getLogger(__name__)


@role_required(allowed_roles=['admin'])
@login_required
def calculation_test_view(request):
    """
    Test page for loss calculations.
    """
    try:
        # Get user accessible sites
        accessible_sites = get_user_accessible_sites(request)
        
        # Get assets that user has access to
        if accessible_sites:
            assets = AssetList.objects.filter(asset_code__in=accessible_sites).values(
                'asset_code', 'asset_name', 'timezone', 'country', 'portfolio'
            ).order_by('asset_name')
        else:
            assets = []
        
        context = {
            'assets': json.dumps(list(assets)),
            'page_title': 'Loss Calculation Test',
        }
        
        return render(request, 'main/calculation_test.html', context)
    
    except Exception as e:
        logger.error(f"Error in calculation_test_view: {str(e)}")
        return render(request, 'main/calculation_test.html', {
            'error_message': str(e),
            'assets': []
        })


@login_required
@role_required(allowed_roles=['admin'])
@require_http_methods(["GET"])
@cors_allow_same_site
def api_calculation_test_devices(request):
    """
    Get list of devices for calculation testing or transposition (irradiance sensor).
    
    Query params:
        - asset_code: Asset code to filter devices
        - device_type: Optional. 'string' = string devices with PV config (default).
                       'wst' = weather station type devices (for transposition irradiance sensor).
    """
    try:
        asset_code = request.GET.get('asset_code')
        device_type_filter = (request.GET.get('device_type') or 'string').strip().lower()
        
        if not asset_code:
            return JsonResponse({
                'success': False,
                'error': 'asset_code is required'
            }, status=400)
        
        # For weather / irradiance sensor (transposition test), return devices with type containing 'wst'
        if device_type_filter == 'wst':
            devices = list(
                device_list.objects.filter(
                    parent_code=asset_code,
                    device_type__icontains='wst'
                ).values(
                    'device_id',
                    'device_name',
                    'device_type',
                    'module_datasheet_id',
                    'modules_in_series'
                ).order_by('device_name')
            )
            return JsonResponse({
                'success': True,
                'count': len(devices),
                'devices': devices
            })
        
        # Default: string devices with PV configuration AND loss_calculation_enabled (or null = enabled)
        qs = get_configured_string_devices_for_asset(asset_code)
        configured_devices = list(
            qs.values(
                'device_id',
                'device_name',
                'device_type',
                'module_datasheet_id',
                'modules_in_series',
            ).order_by('device_name')
        )

        return JsonResponse({
            'success': True,
            'count': len(configured_devices),
            'devices': configured_devices
        })
        
    except Exception as e:
        logger.error(f"Error in api_calculation_test_devices: {e}", exc_info=True)
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@login_required
@role_required(allowed_roles=['admin'])
@require_http_methods(["POST"])
@cors_allow_same_site
def api_calculation_test_transpose(request):
    """
    Run GHI→GII transposition for selected asset, irradiance sensor, metric and date range.
    Writes GII to timeseries_data with synthetic device_id = asset_code_gii_tilt_azimuth.
    Admin only.
    """
    try:
        body = json.loads(request.body) if request.body else {}
        asset_code = body.get('asset_code')
        irradiance_device_id = body.get('irradiance_device_id')
        metric = body.get('metric', 'ghi').strip() or 'ghi'
        start_date_str = body.get('start_date')
        end_date_str = body.get('end_date')

        if not asset_code:
            return JsonResponse({'success': False, 'error': 'asset_code is required'}, status=400)
        if not irradiance_device_id:
            return JsonResponse({'success': False, 'error': 'irradiance_device_id is required'}, status=400)
        if not start_date_str or not end_date_str:
            return JsonResponse({'success': False, 'error': 'start_date and end_date are required'}, status=400)

        asset = AssetList.objects.filter(asset_code=asset_code).first()
        if not asset:
            return JsonResponse({'success': False, 'error': f'Asset {asset_code} not found'}, status=404)

        def _asset_fixed_tz():
            """
            AssetList.timezone is typically stored like '+08:00'.
            Interpret naive datetime-local start/end values using this fixed offset.
            """
            tz_str = (getattr(asset, 'timezone', '') or '').strip()
            m = re.match(r'^([+-])(\d{2}):?(\d{2})$', tz_str)
            if not m:
                return django_timezone.get_current_timezone()
            sign, hh, mm = m.groups()
            offset_min = int(hh) * 60 + int(mm)
            if sign == '-':
                offset_min = -offset_min
            return django_timezone.get_fixed_timezone(offset_min)

        def _parse_dt(dt_str: str):
            """
            Accepts multiple common formats:
            - naive 'YYYY-MM-DDTHH:MM' from <input type="datetime-local"> (treated as asset local time)
            - ISO strings with offsets, e.g. '2026-02-04T00:56+08:00' or '2026-02-04T00:56Z'
            - 'DD-MM-YYYY HH:MM' or 'DD-MM-YYYY' (treated as asset local time)

            Returns an aware UTC datetime for querying timeseries_data.ts.
            """
            s = (dt_str or '').strip()
            if not s:
                raise ValueError('empty datetime')

            # Normalize explicit UTC suffix
            if s.endswith('Z'):
                s = s[:-1] + '+00:00'

            dt = None

            # First try strict ISO8601 (covers 'YYYY-MM-DDTHH:MM' and with offsets)
            try:
                dt = datetime.fromisoformat(s)
            except ValueError:
                # Try a small set of explicit patterns
                for fmt in ("%d-%m-%Y %H:%M", "%d-%m-%Y %H:%M:%S", "%d-%m-%Y"):
                    try:
                        dt = datetime.strptime(s, fmt)
                        break
                    except ValueError:
                        continue
                if dt is None:
                    raise

            # If still naive, interpret in asset timezone and convert to UTC
            if django_timezone.is_naive(dt):
                dt = django_timezone.make_aware(dt, _asset_fixed_tz())
            return dt.astimezone(dt_timezone.utc)

        try:
            start_date = _parse_dt(start_date_str)
        except Exception as e:
            logger.error(f"api_calculation_test_transpose: invalid start_date '{start_date_str}': {e}", exc_info=True)
            return JsonResponse(
                {
                    'success': False,
                    'error': f"Invalid start_date format: '{start_date_str}'",
                },
                status=400,
            )
        try:
            end_date = _parse_dt(end_date_str)
        except Exception as e:
            logger.error(f"api_calculation_test_transpose: invalid end_date '{end_date_str}': {e}", exc_info=True)
            return JsonResponse(
                {
                    'success': False,
                    'error': f"Invalid end_date format: '{end_date_str}'",
                },
                status=400,
            )

        if start_date >= end_date:
            return JsonResponse({'success': False, 'error': 'start_date must be before end_date'}, status=400)

        # Debug logging: show parsed start/end in asset local time and UTC
        asset_tz = _asset_fixed_tz()
        logger.info(
            "api_calculation_test_transpose: asset=%s tz=%s, "
            "start_local=%s, end_local=%s, start_utc=%s, end_utc=%s",
            asset.asset_code,
            getattr(asset, 'timezone', ''),
            start_date.astimezone(asset_tz).isoformat(),
            end_date.astimezone(asset_tz).isoformat(),
            start_date.isoformat(),
            end_date.isoformat(),
        )

        tilt_configs = getattr(asset, 'tilt_configs', None)
        if not tilt_configs or not isinstance(tilt_configs, list) or len(tilt_configs) == 0:
            return JsonResponse({
                'success': False,
                'error': 'Asset has no tilt_configs. Add tilt/azimuth/panel_count in site onboarding.'
            }, status=400)

        lat_deg = float(asset.latitude)
        lon_deg = float(asset.longitude)
        # Altitude (m): from asset_list.altitude_m, default 0. Used for pressure-corrected beam.
        altitude_m = float(asset.altitude_m) if getattr(asset, 'altitude_m', None) is not None else 0.0
        # Albedo ρ: from asset_list.albedo, default 0.2. Used for ground-reflected component.
        albedo = float(asset.albedo) if getattr(asset, 'albedo', None) is not None else 0.2
        albedo = max(0.0, min(1.0, albedo))

        # Fetch GHI from timeseries_data (metric or oem_metric)
        ghi_rows = list(
            timeseries_data.objects.filter(
                device_id=irradiance_device_id,
                ts__gte=start_date,
                ts__lte=end_date
            ).filter(Q(metric=metric) | Q(oem_metric=metric)).values('ts', 'value').order_by('ts')
        )

        if not ghi_rows:
            return JsonResponse({
                'success': False,
                'error': f'No GHI data found for device {irradiance_device_id}, metric "{metric}" in date range.'
            }, status=400)

        # Debug logging: first/last GHI timestamps actually found
        first_ts = ghi_rows[0]['ts']
        last_ts = ghi_rows[-1]['ts']
        logger.info(
            "api_calculation_test_transpose: GHI rows for device=%s metric=%s -> "
            "count=%d, first_ts_utc=%s, last_ts_utc=%s, first_ts_local=%s, last_ts_local=%s",
            irradiance_device_id,
            metric,
            len(ghi_rows),
            first_ts.isoformat(),
            last_ts.isoformat(),
            first_ts.astimezone(asset_tz).isoformat(),
            last_ts.astimezone(asset_tz).isoformat(),
        )

        ghi_by_ts = {}
        for row in ghi_rows:
            try:
                ghi_by_ts[row['ts']] = float(row['value'])
            except (ValueError, TypeError):
                continue

        if not ghi_by_ts:
            return JsonResponse({
                'success': False,
                'error': 'No valid numeric GHI values in the selected data.'
            }, status=400)

        # Delete existing GII for this asset in date range (re-run cleanup)
        gii_prefix = f"{asset_code}_gii_"
        deleted_count, _ = timeseries_data.objects.filter(
            device_id__startswith=gii_prefix,
            ts__gte=start_date,
            ts__lte=end_date,
            metric='gii'
        ).delete()

        # Run transposition and write GII
        writer = TimeseriesWriter()
        device_ids_used = set()
        records_written = 0
        t0 = time.perf_counter()

        for ts, ghi in ghi_by_ts.items():
            for cfg in tilt_configs:
                try:
                    tilt_deg = float(cfg.get('tilt_deg', 0))
                    azimuth_deg = float(cfg.get('azimuth_deg', 0))
                except (TypeError, ValueError):
                    continue
                gii_val = ghi_to_gii(
                    ghi,
                    ts,
                    lat_deg,
                    lon_deg,
                    tilt_deg,
                    azimuth_deg,
                    altitude_m=altitude_m,
                    rho=albedo,
                    local_tz=asset_tz,
                )
                dev_id = gii_device_id(asset_code, tilt_deg, azimuth_deg)
                device_ids_used.add(dev_id)
                res = writer.write_batch(
                    device_id=dev_id,
                    metrics={'gii': gii_val},
                    timestamp=ts,
                    device_type='weather',
                )
                if res.get('gii'):
                    records_written += 1

        time_taken_seconds = time.perf_counter() - t0

        return JsonResponse({
            'success': True,
            'time_taken_seconds': round(time_taken_seconds, 2),
            'device_ids_used': sorted(device_ids_used),
            'records_written': records_written,
            'ghi_points': len(ghi_by_ts),
            'tilt_configs_count': len(tilt_configs),
        })
    except json.JSONDecodeError as e:
        return JsonResponse({'success': False, 'error': f'Invalid JSON: {e}'}, status=400)
    except Exception as e:
        logger.error(f"Error in api_calculation_test_transpose: {e}", exc_info=True)
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@login_required
@role_required(allowed_roles=['admin'])
@require_http_methods(["POST"])
@cors_allow_same_site
def api_calculation_test_inverter_expected_power(request):
    """
    Compute inverter-level expected power for a date range using:
    - inverter tilt_configs (SDM groups)
    - transposed GII (metric='gii') for each group tilt/azimuth
    Writes expected power back to timeseries_data with:
    - device_id = inverter_id
    - metric = 'expected_power'
    - ts = same timestamps as the GII series used
    """
    try:
        body = json.loads(request.body) if request.body else {}
        asset_code = body.get('asset_code')
        inverter_id = body.get('inverter_id')
        start_date_str = body.get('start_date')
        end_date_str = body.get('end_date')
        inverter_efficiency = body.get('inverter_efficiency', 0.97)

        if not asset_code:
            return JsonResponse({'success': False, 'error': 'asset_code is required'}, status=400)
        if not inverter_id:
            return JsonResponse({'success': False, 'error': 'inverter_id is required'}, status=400)
        if not start_date_str or not end_date_str:
            return JsonResponse({'success': False, 'error': 'start_date and end_date are required'}, status=400)

        asset = AssetList.objects.filter(asset_code=asset_code).first()
        if not asset:
            return JsonResponse({'success': False, 'error': f'Asset {asset_code} not found'}, status=404)

        # Reuse the same robust datetime parsing approach as transpose
        def _asset_fixed_tz():
            tz_str = (getattr(asset, 'timezone', '') or '').strip()
            m = re.match(r'^([+-])(\d{2}):?(\d{2})$', tz_str)
            if not m:
                return django_timezone.get_current_timezone()
            sign, hh, mm = m.groups()
            offset_min = int(hh) * 60 + int(mm)
            if sign == '-':
                offset_min = -offset_min
            return django_timezone.get_fixed_timezone(offset_min)

        def _parse_dt(dt_str: str):
            s = (dt_str or '').strip()
            if not s:
                raise ValueError('empty datetime')
            if s.endswith('Z'):
                s = s[:-1] + '+00:00'
            dt = None
            try:
                dt = datetime.fromisoformat(s)
            except ValueError:
                for fmt in ("%d-%m-%Y %H:%M", "%d-%m-%Y %H:%M:%S", "%d-%m-%Y"):
                    try:
                        dt = datetime.strptime(s, fmt)
                        break
                    except ValueError:
                        continue
                if dt is None:
                    raise
            if django_timezone.is_naive(dt):
                dt = django_timezone.make_aware(dt, _asset_fixed_tz())
            return dt.astimezone(dt_timezone.utc)

        start_date = _parse_dt(start_date_str)
        end_date = _parse_dt(end_date_str)

        if start_date >= end_date:
            return JsonResponse({'success': False, 'error': 'start_date must be before end_date'}, status=400)

        result = compute_and_persist_inverter_expected_power(
            asset_code=asset_code,
            inverter_id=inverter_id,
            start_ts=start_date,
            end_ts=end_date,
            inverter_efficiency=float(inverter_efficiency),
        )

        return JsonResponse({
            'success': True,
            'inverter_id': result.inverter_id,
            'start_ts': result.start_ts.isoformat(),
            'end_ts': result.end_ts.isoformat(),
            'groups_count': result.groups_count,
            'group_device_ids': result.group_device_ids,
            'deleted_existing_points': result.deleted_existing_points,
            'points_written': result.points_written,
            'points_skipped_missing_inputs': result.points_skipped_missing_gii,
            'groups_summary': result.groups_summary,
            'warnings': result.warnings,
            'dc_cap_used_kw': result.dc_cap_used_kw,
            'pr_used': result.pr_used,
            'power_model_used': result.power_model_used,
        })

    except Exception as e:
        logger.error(f"Error in api_calculation_test_inverter_expected_power: {e}", exc_info=True)
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@login_required
@role_required(allowed_roles=['admin'])
@require_http_methods(["POST"])
@cors_allow_same_site
def api_calculation_test_upload_satellite_csv(request):
    """
    Upload a satellite GHI/TEMP CSV to timeseries_data.

    POST multipart/form-data:
        - csv_file: CSV file with columns time, GHI, TEMP
        - asset_code: Site/asset code (device_id will be {asset_code}_sat)

    Writes metric sat_ghi from GHI and sat_amb_temp from TEMP.
    For the time range in the file, any existing data for that device is
    deleted before inserting (replace-by-duration).
    """
    try:
        asset_code = (request.POST.get('asset_code') or '').strip()
        if not asset_code:
            return JsonResponse({'success': False, 'error': 'asset_code is required'}, status=400)

        if 'csv_file' not in request.FILES:
            return JsonResponse({'success': False, 'error': 'csv_file is required'}, status=400)

        csv_file = request.FILES['csv_file']
        if not csv_file.name or not csv_file.name.lower().endswith(('.csv', '.txt')):
            return JsonResponse({'success': False, 'error': 'File must be a CSV'}, status=400)

        # Verify asset exists
        if not AssetList.objects.filter(asset_code=asset_code).exists():
            return JsonResponse({'success': False, 'error': f'Asset "{asset_code}" not found'}, status=404)

        file_content = csv_file.read()
        success, error_msg, deleted_count, rows_written, start_ts, end_ts = upload_satellite_ghi_temp_csv(
            file_content, asset_code, filename=csv_file.name
        )

        if not success:
            return JsonResponse({'success': False, 'error': error_msg or 'Upload failed'}, status=400)

        return JsonResponse({
            'success': True,
            'asset_code': asset_code,
            'device_id': f'{asset_code}_sat',
            'deleted_count': deleted_count,
            'rows_written': rows_written,
            'start_ts': start_ts.isoformat() if start_ts else None,
            'end_ts': end_ts.isoformat() if end_ts else None,
        })
    except Exception as e:
        logger.error(f"Error in api_calculation_test_upload_satellite_csv: {e}", exc_info=True)
        return JsonResponse({'success': False, 'error': str(e)}, status=500)

