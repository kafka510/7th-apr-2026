"""
Analytics views for device data visualization
"""
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse, HttpResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from main.decorators.cors_decorator import cors_allow_same_site
from django.db.models import Q
from datetime import datetime, timedelta
import pytz
import json
import logging
import csv

from accounts.decorators import feature_required
from ..models import (
    AssetList,
    device_list,
    device_mapping,
    timeseries_data,
)
from data_collection.models import AssetAdapterConfig
from .shared.utilities import get_user_accessible_sites
from main.permissions import user_has_capability

logger = logging.getLogger(__name__)


def _get_mapping_lookup_codes(asset_code: str) -> list[str]:
    """
    Resolve mapping scopes for analytics lookups.
    Supports both:
    - legacy asset-scoped rows: device_mapping.asset_code = <asset_code>
    - adapter-scoped rows: device_mapping.asset_code = <adapter_id> from AssetAdapterConfig
    """
    lookup_codes = [asset_code]
    try:
        adapter_ids = list(
            AssetAdapterConfig.objects.filter(asset_code=asset_code)
            .values_list("adapter_id", flat=True)
            .distinct()
        )
        for aid in adapter_ids:
            aid_s = (aid or "").strip()
            if aid_s:
                lookup_codes.append(aid_s)
    except Exception:
        pass
    return sorted(set(lookup_codes))


@feature_required('analytics')
@login_required
def analytics_view(request):
    """
    Analytics page view for device data visualization - supports both React and legacy templates
    """
    try:
        # Check if React version is enabled via waffle flag
        from waffle import flag_is_active
        use_react = flag_is_active(request, 'react_analytics')
        
        # Get user accessible sites
        accessible_sites = get_user_accessible_sites(request)
        
        # Get assets that user has access to
        if accessible_sites:
            assets = AssetList.objects.filter(asset_code__in=accessible_sites).values(
                'asset_code', 'asset_name', 'timezone', 'country', 'portfolio'
            ).order_by('asset_name')
        else:
            assets = []
        
        assets_list = list(assets)
        
        if use_react:
            # Render React version - pass assets as JSON
            import json
            return render(request, 'main/analytics_react.html', {
                'assets': json.dumps(assets_list),
                'page_title': 'Analytics Dashboard',
            })
        
        # Legacy template with data passed directly
        context = {
            'assets': assets_list,
            'page_title': 'Analytics Dashboard',
        }
        
        return render(request, 'main/analytics.html', context)
    
    except Exception as e:
        logger.error(f"Error in analytics_view: {str(e)}")
        return render(request, 'main/analytics.html', {
            'error_message': str(e),
            'assets': []
        })


#@csrf_exempt
@login_required
@require_http_methods(["GET"])
@cors_allow_same_site
def api_analytics_devices(request):
    """
    API endpoint to get devices for a selected site
    Query params:
        - asset_code: The asset code to filter devices
    """
    try:
        # Check if user is authenticated
        if not request.user.is_authenticated:
            logger.warning(f"Unauthenticated request to api_analytics_devices from IP: {request.META.get('REMOTE_ADDR')}")
            return JsonResponse({
                'success': False,
                'error': 'Authentication required'
            }, status=401)
        
        # Check if user has analytics permission
        if not user_has_capability(request.user, 'analytics.access'):
            user_role = getattr(getattr(request.user, 'userprofile', None), 'role', None)
            logger.warning(f"User {request.user.username} with role {user_role} denied access to api_analytics_devices")
            return JsonResponse({
                'success': False,
                'error': 'Access denied. You do not have permission to use analytics.'
            }, status=403)
        
        asset_code = request.GET.get('asset_code')
        
        if not asset_code:
            logger.warning("No asset_code provided")
            return JsonResponse({
                'success': False,
                'error': 'asset_code parameter is required'
            }, status=400)
        
        # Check if user has access to this site
        accessible_sites = get_user_accessible_sites(request)
        # Convert QuerySet to list of asset codes
        if accessible_sites:
            accessible_site_codes = list(accessible_sites.values_list('asset_code', flat=True))
        else:
            accessible_site_codes = []
        
        
        if accessible_site_codes and asset_code not in accessible_site_codes:
            logger.warning(f"User {request.user.username} does not have access to site {asset_code}")
            return JsonResponse({
                'success': False,
                'error': 'Access denied to this site'
            }, status=403)
        
        
        # Get devices for this site (parent_code links to asset)
        # The parent_code in device_list corresponds to asset_code in AssetList
        devices = device_list.objects.filter(
            parent_code=asset_code
        ).values(
            'device_id',
            'device_name',
            'device_code',
            'device_type',
            'device_type_id',
            'device_model',
            'device_make'
        ).order_by('device_name')
        
        devices_list = list(devices)
        
        return JsonResponse({
            'success': True,
            'data': devices_list,
            'count': len(devices_list)
        })
    
    except Exception as e:
        logger.error(f"Error in api_analytics_devices: {str(e)}")
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


def _analytics_device_type_filter_q(expanded_types: set) -> Q:
    """Case-insensitive OR across device_type values (device_list casing often differs from device_mapping)."""
    type_q = None
    for t in expanded_types:
        s = (t or "").strip()
        if not s:
            continue
        part = Q(device_type__iexact=s)
        type_q = part if type_q is None else (type_q | part)
    return type_q if type_q is not None else Q(pk__in=[])


def api_analytics_measurement_points(request):
    """
    API endpoint to get measurement points for selected site and devices
    Query params:
        - asset_code: The asset code
        - device_types: Comma-separated list of device types (optional)
    """
    try:
        if not request.user.is_authenticated:
            return JsonResponse({'success': False, 'error': 'Authentication required'}, status=401)

        # Check if user has analytics permission
        if not user_has_capability(request.user, 'analytics.access'):
            return JsonResponse({
                'success': False,
                'error': 'Access denied. You do not have permission to use analytics.'
            }, status=403)
        
        asset_code = request.GET.get('asset_code')
        device_types = request.GET.get('device_types', '')
        
        
        if not asset_code:
            logger.warning("No asset_code provided to api_analytics_measurement_points")
            return JsonResponse({
                'success': False,
                'error': 'asset_code parameter is required'
            }, status=400)
        
        # Check if user has access to this site
        accessible_sites = get_user_accessible_sites(request)
        accessible_site_codes = list(accessible_sites.values_list('asset_code', flat=True)) if accessible_sites else []
        if accessible_site_codes and asset_code not in accessible_site_codes:
            return JsonResponse({
                'success': False,
                'error': 'Access denied to this site'
            }, status=403)
        
        # Build query for device_mapping table.
        # Include BOTH adapter-scoped mappings (asset_code=adapter_id, e.g. "laplaceid")
        # and legacy asset-scoped mappings (asset_code=<asset_code>) so mixed setups keep working.
        lookup_codes = _get_mapping_lookup_codes(asset_code)

        query = Q(asset_code__in=lookup_codes)
        
        type_filtered = False
        raw_types = []
        expanded_types = set()
        used_device_type_fallback = False

        if device_types:
            raw_types = [dt.strip() for dt in device_types.split(',') if dt.strip()]
            if raw_types:
                # Normalize common adapter/UI device_type names to mapping-table variants.
                # Match case-insensitively against device_mapping.device_type.
                type_aliases = {
                    "pcs": ["pcs", "central_inv", "inverter", "string_inv"],
                    "central_inv": ["central_inv", "pcs", "inverter", "string_inv"],
                    "inverter": ["inverter", "pcs", "central_inv", "string_inv"],
                    "string": ["string", "string_inv"],
                    "string_inv": ["string_inv", "string"],
                    "gii": ["gii", "wst", "weather_station", "met_station", "gmt"],
                    "wst": ["wst", "gii", "weather_station", "met_station", "gmt"],
                    "weather_station": ["weather_station", "wst", "met_station", "gmt", "gii"],
                    "met_station": ["met_station", "weather_station", "wst", "gmt", "gii"],
                    "optimizer": ["optimizer", "opt"],
                    "electricity_meter": ["electricity_meter", "meter", "approvedmeter", "em"],
                    "battery": ["battery", "bess", "pcs"],
                }
                for dt in raw_types:
                    key = dt.lower()
                    expanded_types.add(dt)
                    expanded_types.add(key)
                    for alias in type_aliases.get(key, []):
                        expanded_types.add(alias)
                expanded_types = {x for x in expanded_types if (x or "").strip()}
                query &= _analytics_device_type_filter_q(expanded_types)
                type_filtered = True

        # Get measurement points from device_mapping
        measurement_points_qs = device_mapping.objects.filter(query).values(
            'id',
            'device_type',
            'oem_tag',
            'discription',  # Note: database has typo 'discription'
            'metric',
            'data_type',
            'units'
        ).order_by('device_type', 'metric')

        # Fallback: if strict device_type filtering yields nothing, retry without device_type filter
        # so adapter-scoped mappings still show up instead of empty UI.
        if type_filtered and not measurement_points_qs.exists():
            used_device_type_fallback = True
            base_query = Q(asset_code__in=lookup_codes)
            measurement_points_qs = device_mapping.objects.filter(base_query).values(
                'id',
                'device_type',
                'oem_tag',
                'discription',
                'metric',
                'data_type',
                'units'
            ).order_by('device_type', 'metric')

        measurement_points = list(measurement_points_qs)
        raw_row_count = len(measurement_points)
        nonempty_metric_count = sum(
            1 for mp in measurement_points if (mp.get('metric') or "").strip()
        )
        
        # Group by device_type and deduplicate metrics
        grouped_data = {}
        for mp in measurement_points:
            device_type = mp['device_type']
            if device_type not in grouped_data:
                grouped_data[device_type] = {}
            
            metric_key = mp['metric']
            
            # Skip empty metrics
            if not metric_key or metric_key.strip() == '':
                continue
            
            # If we haven't seen this metric before, or if this one has better info
            if (metric_key not in grouped_data[device_type] or 
                (mp['units'] and not grouped_data[device_type][metric_key].get('units')) or
                (mp['discription'] and not grouped_data[device_type][metric_key].get('description')) or
                (mp['oem_tag'] and not grouped_data[device_type][metric_key].get('oem_tag'))):
                grouped_data[device_type][metric_key] = {
                    'id': mp['id'],
                    'oem_tag': mp['oem_tag'],
                    'metric': mp['metric'],
                    'description': mp['discription'],  # Use correct spelling in response
                    'data_type': mp['data_type'],
                    'units': mp['units']
                }
        
        # Convert back to list format for frontend
        for device_type in grouped_data:
            grouped_data[device_type] = list(grouped_data[device_type].values())

        grouped_metric_count = sum(len(v) for v in grouped_data.values())
        hints = []
        if raw_row_count == 0:
            hints.append(
                f"No device_mapping rows for this scope. Searched asset_code in {lookup_codes!r}. "
                "Add rows with asset_code equal to this site code and/or the adapter_id from Data Collection "
                "(e.g. fusion_solar, solargis, laplaceid)."
            )
        elif nonempty_metric_count == 0:
            hints.append(
                "device_mapping rows exist but every metric field is empty. "
                "Set metric to the internal series name used in timeseries_data (not only oem_tag)."
            )
        elif grouped_metric_count == 0:
            hints.append(
                "Rows were found but none have a usable metric after filtering; check metric column values."
            )
        if used_device_type_fallback and grouped_metric_count > 0:
            hints.append(
                "device_list device_type values did not match any device_mapping.device_type; "
                "showing all metrics for this asset scope. Align device_type strings or extend mappings."
            )

        diagnostics = {
            'lookup_codes': lookup_codes,
            'device_types_requested': raw_types if raw_types else None,
            'expanded_device_types': sorted(expanded_types) if expanded_types else None,
            'used_device_type_fallback': used_device_type_fallback,
            'raw_mapping_row_count': raw_row_count,
            'rows_with_nonempty_metric': nonempty_metric_count,
            'grouped_metric_count': grouped_metric_count,
            'hints': hints,
        }

        return JsonResponse({
            'success': True,
            'data': grouped_data,
            'total_count': raw_row_count,
            'diagnostics': diagnostics,
        })
    
    except Exception as e:
        logger.error(f"Error in api_analytics_measurement_points: {str(e)}")
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


#@csrf_exempt
@login_required
@require_http_methods(["GET"])
def api_analytics_timeseries_data(request):
    """
    API endpoint to get time-series data for visualization
    Query params:
        - device_ids: Comma-separated list of device IDs
        - metrics: Comma-separated list of metric names
        - start_date: Start date (YYYY-MM-DD)
        - end_date: End date (YYYY-MM-DD)
        - asset_code: Asset code for timezone conversion
    """
    try:
        # Check if user has analytics permission
        if not user_has_capability(request.user, 'analytics.access'):
            return JsonResponse({
                'success': False,
                'error': 'Access denied. You do not have permission to use analytics.'
            }, status=403)
        
        # Get parameters
        device_ids = request.GET.get('device_ids', '')
        metrics = request.GET.get('metrics', '')
        start_date = request.GET.get('start_date')
        end_date = request.GET.get('end_date')
        asset_code = request.GET.get('asset_code')
        
        # Validate required parameters
        if not all([device_ids, metrics, start_date, end_date, asset_code]):
            return JsonResponse({
                'success': False,
                'error': 'Missing required parameters: device_ids, metrics, start_date, end_date, asset_code'
            }, status=400)
        
        # Check if user has access to this site
        accessible_sites = get_user_accessible_sites(request)
        accessible_site_codes = list(accessible_sites.values_list('asset_code', flat=True)) if accessible_sites else []
        if accessible_site_codes and asset_code not in accessible_site_codes:
            return JsonResponse({
                'success': False,
                'error': 'Access denied to this site'
            }, status=403)
        
        # Get asset timezone
        try:
            asset = AssetList.objects.get(asset_code=asset_code)
            # Parse timezone offset (e.g., '+05:30' or '-08:00')
            tz_offset = asset.timezone
            # Convert to pytz timezone (UTC offset)
            hours, minutes = map(int, tz_offset.replace('+', '').replace('-', '').split(':'))
            total_offset = hours * 60 + minutes
            if tz_offset.startswith('-'):
                total_offset = -total_offset
            
            # Create timezone-aware datetime objects
            # Note: We'll use UTC for database queries and convert to local time in response
            site_timezone = pytz.FixedOffset(total_offset)
        except AssetList.DoesNotExist:
            return JsonResponse({
                'success': False,
                'error': 'Asset not found'
            }, status=404)
        except Exception as e:
            logger.error(f"Error parsing timezone: {str(e)}")
            site_timezone = pytz.UTC
        
        # Parse device IDs and metrics
        device_id_list = [d.strip() for d in device_ids.split(',') if d.strip()]
        metric_list = [m.strip() for m in metrics.split(',') if m.strip()]
        
        # Parse dates
        try:
            # Create timezone-aware start and end dates
            # Start of day in site's local timezone
            start_dt_local = datetime.strptime(start_date, '%Y-%m-%d')
            start_dt_local = site_timezone.localize(start_dt_local.replace(hour=0, minute=0, second=0))
            
            # End of day in site's local timezone
            end_dt_local = datetime.strptime(end_date, '%Y-%m-%d')
            end_dt_local = site_timezone.localize(end_dt_local.replace(hour=23, minute=59, second=59))
            
            # Convert to UTC for database query
            start_dt_utc = start_dt_local.astimezone(pytz.UTC)
            end_dt_utc = end_dt_local.astimezone(pytz.UTC)
            
            
        except ValueError as e:
            return JsonResponse({
                'success': False,
                'error': f'Invalid date format. Use YYYY-MM-DD: {str(e)}'
            }, status=400)
        
        # Build query
        query = Q(device_id__in=device_id_list) & Q(metric__in=metric_list) & Q(ts__gte=start_dt_utc) & Q(ts__lte=end_dt_utc)
        
        # Get data from timeseries_data table
        # Note: Limit to 50,000 records to prevent performance issues
        # For longer date ranges, we may need to implement pagination
        timeseries_records = timeseries_data.objects.filter(query).values(
            'device_id',
            'ts',
            'metric',
            'oem_metric',
            'value'
        ).order_by('ts')[:50000]
        
        # Convert to list to avoid QuerySet issues
        timeseries_list = list(timeseries_records)
        
        # Check if we hit the limit
        if len(timeseries_list) == 50000:
            logger.warning(f"Query hit 50,000 record limit for date range {start_date} to {end_date}. Some data may be missing.")
        
        # Process data and convert timestamps to local timezone
        processed_data = []
        filtered_count = 0
        total_count = len(timeseries_list)
        
        for record in timeseries_list:
            # Handle timezone conversion properly
            ts_from_db = record['ts']
            
            # If timestamp has no timezone info, assume it's UTC
            if ts_from_db.tzinfo is None:
                ts_utc = pytz.UTC.localize(ts_from_db)
            else:
                # Timestamp already has timezone info, convert to UTC first
                ts_utc = ts_from_db.astimezone(pytz.UTC)
            
            # Convert from UTC to site's local timezone
            ts_local = ts_utc.astimezone(site_timezone)
            
            # Data validation and filtering
            value = record['value']
            
            # Skip null, empty, or invalid values
            if value is None or value == '' or value == 'null' or value == 'NULL':
                filtered_count += 1
                continue
            
            # Convert to float if possible, skip if not
            try:
                numeric_value = float(value)
            except (ValueError, TypeError):
                filtered_count += 1
                continue  # Skip non-numeric values
            
            # Basic outlier detection - skip extreme values that are likely errors
            # Skip negative values (for most metrics like power, energy, etc.)
            if numeric_value < 0:
                filtered_count += 1
                continue
            
            # Skip extremely large values (likely data errors)
            # Adjust threshold based on metric type if needed
            if numeric_value > 999999:
                filtered_count += 1
                continue
            
            processed_data.append({
                'device_id': record['device_id'],
                'timestamp': ts_local.isoformat(),
                'timestamp_utc': ts_utc.isoformat(),
                'metric': record['metric'],
                'oem_metric': record['oem_metric'],
                'value': numeric_value
            })
        
        # Sort data by timestamp to ensure chronological order
        processed_data.sort(key=lambda x: x['timestamp'])
        
        # Log data quality metrics
        if filtered_count > 0:
            logger.info(f"Filtered out {filtered_count} invalid data points out of {total_count} total records ({filtered_count/total_count*100:.1f}%)")
        
        # Look up device names for chart labels (device_list uses parent_code for asset)
        device_names = {}
        try:
            name_rows = device_list.objects.filter(
                parent_code=asset_code,
                device_id__in=device_id_list
            ).values('device_id', 'device_name')
            for row in name_rows:
                device_names[row['device_id']] = row['device_name'] or row['device_id']
        except Exception as e:
            logger.warning(f"Could not fetch device names: {e}")
        
        # Get units for each metric from device_mapping
        metric_units = {}
        try:
            mapping_lookup_codes = _get_mapping_lookup_codes(asset_code)
            device_mappings = device_mapping.objects.filter(
                asset_code__in=mapping_lookup_codes,
                metric__in=metric_list
            ).values('metric', 'units')
            
            for mapping in device_mappings:
                metric_units[mapping['metric']] = mapping['units'] or ''
        except Exception as e:
            logger.warning(f"Could not fetch metric units: {e}")
        
        # Organize data by device and metric for easier chart rendering
        organized_data = {}
        for record in processed_data:
            key = f"{record['device_id']}_{record['metric']}"
            if key not in organized_data:
                organized_data[key] = {
                    'device_id': record['device_id'],
                    'device_name': device_names.get(record['device_id'], ''),
                    'metric': record['metric'],
                    'oem_metric': record['oem_metric'],
                    'units': metric_units.get(record['metric'], ''),
                    'data_points': []
                }
            organized_data[key]['data_points'].append({
                'timestamp': record['timestamp'],
                'value': record['value']
            })
        
        response_data = {
            'success': True,
            'data': list(organized_data.values()),
            'timezone': str(site_timezone),
            'timezone_offset': asset.timezone,
            'record_count': len(processed_data),
            'date_range': {
                'start': start_dt_local.isoformat(),
                'end': end_dt_local.isoformat()
            }
        }
        
        # Add warnings and data quality information
        warnings = []
        
        if len(timeseries_list) == 50000:
            warnings.append('Data limit reached. Some data may be missing for longer date ranges.')
        
        if filtered_count > 0:
            filter_percentage = (filtered_count / total_count) * 100
            warnings.append(f'Filtered out {filtered_count} invalid data points ({filter_percentage:.1f}% of total data)')
        
        if warnings:
            response_data['warnings'] = warnings
        
        # Add data quality summary
        response_data['data_quality'] = {
            'total_records': total_count,
            'valid_records': len(processed_data),
            'filtered_records': filtered_count,
            'filter_percentage': (filtered_count / total_count * 100) if total_count > 0 else 0
        }
        
        return JsonResponse(response_data)
    
    except Exception as e:
        logger.error(f"Error in api_analytics_timeseries_data: {str(e)}")
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


#@csrf_exempt
@login_required
@require_http_methods(["GET"])
def api_analytics_device_types(request):
    """
    API endpoint to get unique device types for a site
    Query params:
        - asset_code: The asset code
    """
    try:
        # Check if user has analytics permission
        if not user_has_capability(request.user, 'analytics.access'):
            return JsonResponse({
                'success': False,
                'error': 'Access denied. You do not have permission to use analytics.'
            }, status=403)
        
        asset_code = request.GET.get('asset_code')
        
        if not asset_code:
            return JsonResponse({
                'success': False,
                'error': 'asset_code parameter is required'
            }, status=400)
        
        # Check if user has access to this site
        accessible_sites = get_user_accessible_sites(request)
        accessible_site_codes = list(accessible_sites.values_list('asset_code', flat=True)) if accessible_sites else []
        if accessible_site_codes and asset_code not in accessible_site_codes:
            return JsonResponse({
                'success': False,
                'error': 'Access denied to this site'
            }, status=403)
        
        # Get unique device types from device_list for this site
        device_types = device_list.objects.filter(
            parent_code=asset_code
        ).values_list('device_type', flat=True).distinct().order_by('device_type')
        
        return JsonResponse({
            'success': True,
            'data': list(device_types)
        })
    
    except Exception as e:
        logger.error(f"Error in api_analytics_device_types: {str(e)}")
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


#@csrf_exempt
@login_required
@require_http_methods(["GET"])
def api_analytics_download_csv(request):
    """
    API endpoint to download chart data as CSV
    Query params:
        - asset_code: The asset code
        - device_ids: Comma-separated device IDs
        - metrics: Comma-separated metrics
        - start_date: Start date (YYYY-MM-DD)
        - end_date: End date (YYYY-MM-DD)
    """
    try:
        # Check if user has analytics permission
        if not user_has_capability(request.user, 'analytics.access'):
            return JsonResponse({
                'success': False,
                'error': 'Access denied. You do not have permission to use analytics.'
            }, status=403)
        
        # Get parameters
        asset_code = request.GET.get('asset_code')
        device_ids = request.GET.get('device_ids')
        metrics = request.GET.get('metrics')
        start_date = request.GET.get('start_date')
        end_date = request.GET.get('end_date')
        
        # Validate required parameters
        if not all([asset_code, device_ids, metrics, start_date, end_date]):
            return JsonResponse({
                'success': False,
                'error': 'Missing required parameters: asset_code, device_ids, metrics, start_date, end_date'
            }, status=400)
        
        # Check if user has access to this asset
        accessible_sites = get_user_accessible_sites(request)
        accessible_site_codes = list(accessible_sites.values_list('asset_code', flat=True))
        
        if asset_code not in accessible_site_codes:
            logger.warning(f"User {request.user.username} does not have access to site {asset_code}")
            return JsonResponse({
                'success': False,
                'error': 'Access denied. You do not have permission to access this site.'
            }, status=403)
        
        # Get asset information
        try:
            asset = AssetList.objects.get(asset_code=asset_code)
        except AssetList.DoesNotExist:
            return JsonResponse({
                'success': False,
                'error': f'Asset {asset_code} not found'
            }, status=404)
        
        # Get timezone for this asset (same logic as main timeseries endpoint)
        try:
            # Parse timezone offset (e.g., '+05:30' or '-08:00')
            tz_offset = asset.timezone
            # Convert to pytz timezone (UTC offset)
            hours, minutes = map(int, tz_offset.replace('+', '').replace('-', '').split(':'))
            total_offset = hours * 60 + minutes
            if tz_offset.startswith('-'):
                total_offset = -total_offset
            
            # Create timezone-aware datetime objects
            site_timezone = pytz.FixedOffset(total_offset)
        except Exception as e:
            logger.error(f"Error parsing timezone: {str(e)}")
            site_timezone = pytz.UTC
        
        # Parse device IDs and metrics
        device_id_list = [d.strip() for d in device_ids.split(',') if d.strip()]
        metric_list = [m.strip() for m in metrics.split(',') if m.strip()]
        
        # Parse dates
        try:
            start_dt_local = datetime.strptime(start_date, '%Y-%m-%d')
            start_dt_local = site_timezone.localize(start_dt_local.replace(hour=0, minute=0, second=0))
            
            end_dt_local = datetime.strptime(end_date, '%Y-%m-%d')
            end_dt_local = site_timezone.localize(end_dt_local.replace(hour=23, minute=59, second=59))
            
            # Convert to UTC for database query
            start_dt_utc = start_dt_local.astimezone(pytz.UTC)
            end_dt_utc = end_dt_local.astimezone(pytz.UTC)
            
        except ValueError as e:
            return JsonResponse({
                'success': False,
                'error': f'Invalid date format. Use YYYY-MM-DD: {str(e)}'
            }, status=400)
        
        # Build query
        query = Q(device_id__in=device_id_list) & Q(metric__in=metric_list) & Q(ts__gte=start_dt_utc) & Q(ts__lte=end_dt_utc)
        
        # Get data from timeseries_data table
        timeseries_records = timeseries_data.objects.filter(query).values(
            'device_id', 'ts', 'metric', 'oem_metric', 'value'
        ).order_by('ts')[:50000]
        
        # Convert to list to avoid QuerySet issues
        timeseries_list = list(timeseries_records)
        
        # Process data and convert timestamps to local timezone
        processed_data = []
        filtered_count = 0
        total_count = len(timeseries_list)
        
        for record in timeseries_list:
            # Handle timezone conversion properly
            ts_from_db = record['ts']
            
            # If timestamp has no timezone info, assume it's UTC
            if ts_from_db.tzinfo is None:
                ts_utc = pytz.UTC.localize(ts_from_db)
            else:
                # Timestamp already has timezone info, convert to UTC first
                ts_utc = ts_from_db.astimezone(pytz.UTC)
            
            # Convert from UTC to site's local timezone
            ts_local = ts_utc.astimezone(site_timezone)
            
            # Data validation and filtering
            value = record['value']
            
            # Skip null, empty, or invalid values
            if value is None or value == '' or value == 'null' or value == 'NULL':
                filtered_count += 1
                continue
            
            # Convert to float if possible, skip if not
            try:
                numeric_value = float(value)
            except (ValueError, TypeError):
                filtered_count += 1
                continue
            
            # Basic outlier detection
            if numeric_value < 0 or numeric_value > 999999:
                filtered_count += 1
                continue
            
            processed_data.append({
                'device_id': record['device_id'],
                'timestamp': ts_local.isoformat(),
                'metric': record['metric'],
                'oem_metric': record['oem_metric'],
                'value': numeric_value
            })
        
        # Sort data by timestamp
        processed_data.sort(key=lambda x: x['timestamp'])
        
        # Get units for each metric
        metric_units = {}
        try:
            mapping_lookup_codes = _get_mapping_lookup_codes(asset_code)
            device_mappings = device_mapping.objects.filter(
                asset_code__in=mapping_lookup_codes,
                metric__in=metric_list
            ).values('metric', 'units')
            
            for mapping in device_mappings:
                metric_units[mapping['metric']] = mapping['units'] or ''
        except Exception as e:
            logger.warning(f"Could not fetch metric units: {e}")
        
        # Pivot data: Group by timestamp, then create columns for each device+metric combination
        # Structure: {timestamp: {device_id_metric: value, ...}}
        pivoted_data = {}
        column_keys = set()  # Track all unique device+metric combinations
        
        for record in processed_data:
            timestamp = record['timestamp']
            device_id = record['device_id']
            metric = record['metric']
            
            # Create column key: device_id + metric (e.g., "DEVICE_01.string_voltage")
            column_key = f"{device_id}.{metric}"
            column_keys.add(column_key)
            
            if timestamp not in pivoted_data:
                pivoted_data[timestamp] = {}
            
            pivoted_data[timestamp][column_key] = record['value']
        
        # Sort column keys for consistent ordering
        sorted_column_keys = sorted(column_keys)
        
        # Create CSV response
        filename = f'analytics_{asset.asset_name.replace(" ", "_").replace("/", "_")}_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv'
        response = HttpResponse(content_type='text/csv; charset=utf-8')
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        
        # Add UTF-8 BOM for better Excel compatibility
        response.write('\ufeff')
        
        # Create CSV writer
        writer = csv.writer(response)
        
        # Write metadata
        writer.writerow(['# Chart Data Export'])
        writer.writerow(['# Site:', asset.asset_name])
        writer.writerow(['# Timezone:', asset.timezone or 'UTC'])
        writer.writerow(['# Export Date:', datetime.now().isoformat()])
        writer.writerow(['# Data Points:', len(processed_data)])
        writer.writerow(['# Unique Timestamps:', len(pivoted_data)])
        if filtered_count > 0:
            filter_percentage = (filtered_count / total_count * 100) if total_count > 0 else 0
            writer.writerow(['# Filtered Points:', f'{filtered_count} ({filter_percentage:.1f}%)'])
        writer.writerow([])
        
        # Write header row: Timestamp + all device+metric columns
        header_row = ['Timestamp'] + sorted_column_keys
        writer.writerow(header_row)
        
        # Write data rows: one row per timestamp
        sorted_timestamps = sorted(pivoted_data.keys())
        for timestamp in sorted_timestamps:
            row = [timestamp]
            for column_key in sorted_column_keys:
                value = pivoted_data[timestamp].get(column_key, '')  # Empty string if no data
                row.append(value)
            writer.writerow(row)
        
        return response
    
    except Exception as e:
        logger.error(f"Error in api_analytics_download_csv: {str(e)}")
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)

