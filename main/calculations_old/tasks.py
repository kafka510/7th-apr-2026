"""
Celery tasks for loss calculations

These tasks calculate expected power, fetch actual power, and write results
to timeseries_data table. Heavy work runs in workers to avoid HTTP request timeouts.
"""
from typing import Optional, Dict, List, Tuple
import logging
from datetime import datetime, timedelta
from django.utils import timezone
from celery import shared_task

from main.models import (
    device_list,
    AssetList,
    get_configured_loss_string_devices_for_asset,
    log_loss_task_started,
    log_loss_task_completed,
)
from .power_calculation_service import PowerCalculationService
from .timeseries_writer import TimeseriesWriter
from .timeseries_reader import TimeseriesReader
from .metric_mapping_service import MetricMappingService
from .transposition_runner import run_transpose_asset_ghi_to_gii

logger = logging.getLogger(__name__)


def _parse_iso_dt(dt_str: str) -> datetime:
    """Parse ISO-like date/datetime string to timezone-aware datetime (UTC)."""
    s = (dt_str or "").strip()
    if not s:
        raise ValueError("empty datetime")
    if s.endswith("Z"):
        s = s[:-1] + "+00:00"
    dt = datetime.fromisoformat(s)
    if timezone.is_naive(dt):
        dt = timezone.make_aware(dt)
    return dt


@shared_task(bind=True, max_retries=3)
def calculate_string_loss(
    self,
    device_id: str,
    timestamp: Optional[datetime] = None,
    asset_code: Optional[str] = None
) -> Dict:
    """
    Calculate loss for a single string device.
    
    Logs task start/completion to LossCalculationTask.
    """
    task_id = getattr(getattr(self, "request", None), "id", None)
    if task_id:
        log_loss_task_started(task_id)

    try:
        if timestamp is None:
            timestamp = timezone.now()
        
        # Get device
        try:
            device = device_list.objects.get(device_id=device_id)
        except device_list.DoesNotExist:
            error_msg = f"Device {device_id} not found"
            logger.error(error_msg)
            if task_id:
                log_loss_task_completed(task_id, success=False, error_message=error_msg)
            return {
                'success': False,
                'device_id': device_id,
                'error': error_msg
            }
        
        # Get asset_code from device if not provided
        if asset_code is None:
            asset_code = device.parent_code
        
        # Initialize services
        power_service = PowerCalculationService()
        timeseries_writer = TimeseriesWriter()
        timeseries_reader = TimeseriesReader()
        
        # Get weather data (use device's weather_device_config if available)
        weather_config = getattr(device, 'weather_device_config', None)
        weather = timeseries_reader.get_weather_data(
            asset_code, 
            timestamp, 
            weather_device_config=weather_config
        )
        
        if not weather.get('irradiance'):
            error_msg = f"No irradiance data found for asset {asset_code} at {timestamp}"
            logger.warning(error_msg)
            if task_id:
                log_loss_task_completed(task_id, success=False, error_message=error_msg)
            return {
                'success': False,
                'device_id': device_id,
                'error': error_msg
            }
        
        # Calculate expected power
        try:
            result = power_service.calculate_expected_power(
                device=device,
                irradiance=weather['irradiance'],
                module_temp=weather.get('module_temp') or weather.get('temperature'),
                ambient_temp=weather.get('ambient_temp'),
                timestamp=timestamp
            )
            
            expected_power = result.expected_power
            
        except Exception as e:
            error_msg = f"Power calculation failed: {str(e)}"
            logger.error(f"Device {device_id}: {error_msg}", exc_info=True)
            if task_id:
                log_loss_task_completed(task_id, success=False, error_message=error_msg)
            return {
                'success': False,
                'device_id': device_id,
                'error': error_msg
            }
        
        # Get actual power
        actual_power = timeseries_reader.get_actual_power(
            device_id, timestamp, device_type='string'
        )
        
        # Write results to timeseries_data
        write_success = timeseries_writer.write_loss_calculation(
            device_id=device_id,
            expected_power=expected_power,
            actual_power=actual_power,
            timestamp=timestamp,
            device_type='string'
        )
        
        if not write_success:
            logger.warning(f"Failed to write results for {device_id}")
        
        # Calculate loss metrics
        power_loss = None
        loss_percentage = None
        
        if actual_power is not None:
            power_loss = expected_power - actual_power
            if expected_power > 0:
                loss_percentage = (power_loss / expected_power) * 100

        if task_id:
            log_loss_task_completed(task_id, success=True)
        
        return {
            'success': True,
            'device_id': device_id,
            'expected_power': expected_power,
            'actual_power': actual_power,
            'power_loss': power_loss,
            'loss_percentage': loss_percentage,
            'irradiance': weather['irradiance'],
            'temperature': weather.get('temperature'),
            'model_code': result.model_code,
            'error': None
        }
        
    except Exception as e:
        error_msg = f"Unexpected error in calculate_string_loss: {str(e)}"
        logger.error(f"Device {device_id}: {error_msg}", exc_info=True)

        if task_id:
            log_loss_task_completed(task_id, success=False, error_message=error_msg)
        
        # Retry on certain errors
        if self.request.retries < self.max_retries:
            raise self.retry(exc=e, countdown=60 * (self.request.retries + 1))
        
        return {
            'success': False,
            'device_id': device_id,
            'error': error_msg
        }


@shared_task
def calculate_strings_batch(
    device_ids: List[str],
    timestamp: Optional[datetime] = None,
    asset_code: Optional[str] = None
) -> Dict:
    """
    Calculate loss for multiple string devices in parallel.
    
    Args:
        device_ids: List of string device IDs
        timestamp: Calculation timestamp (defaults to now)
        asset_code: Asset code (for weather data lookup)
        
    Returns:
        Dictionary with batch results:
        {
            'total': 10,
            'successful': 8,
            'failed': 2,
            'results': [...]
        }
    """
    if timestamp is None:
        timestamp = timezone.now()
    
    # Create subtasks for each device
    tasks = []
    for device_id in device_ids:
        task = calculate_string_loss.delay(device_id, timestamp, asset_code)
        tasks.append(task)
    
    # Wait for all tasks to complete (with timeout)
    results = []
    successful = 0
    failed = 0
    
    for task in tasks:
        try:
            result = task.get(timeout=300)  # 5 minute timeout per device
            results.append(result)
            if result.get('success'):
                successful += 1
            else:
                failed += 1
        except Exception as e:
            logger.error(f"Task failed: {e}", exc_info=True)
            failed += 1
            results.append({
                'success': False,
                'error': str(e)
            })
    
    return {
        'total': len(device_ids),
        'successful': successful,
        'failed': failed,
        'results': results
    }


@shared_task(bind=True)
def transpose_asset_ghi_to_gii(
    self,
    asset_code: str,
    irradiance_device_id: str,
    start_date_str: str,
    end_date_str: str,
    metric: str = "ghi",
) -> Dict:
    """
    Run GHI→GII transposition for an asset and date range (Celery worker).
    Used by the loss calculation test page and APIs to avoid request timeouts.
    """
    try:
        start_date = _parse_iso_dt(start_date_str)
        end_date = _parse_iso_dt(end_date_str)
    except Exception as e:
        logger.warning("transpose_asset_ghi_to_gii: invalid dates: %s", e)
        return {"success": False, "error": f"Invalid date format: {e}"}
    if start_date >= end_date:
        return {"success": False, "error": "start_date must be before end_date"}
    return run_transpose_asset_ghi_to_gii(
        asset_code=asset_code,
        irradiance_device_id=irradiance_device_id,
        metric=metric,
        start_date=start_date,
        end_date=end_date,
    )


@shared_task(bind=True)
def run_string_loss_for_date_range(
    self,
    device_id: str,
    start_date_str: str,
    end_date_str: str,
    time_interval_minutes: int = 15,
) -> Dict:
    """
    Run loss calculation for a single string device over a date range (Celery worker).
    One task per device to avoid long-running requests and allow finer progress/retries.
    """
    from main.calculations.calculation_service import CalculationService

    task_id = getattr(getattr(self, "request", None), "id", None)
    if task_id:
        log_loss_task_started(task_id)

    try:
        start_dt = _parse_iso_dt(start_date_str)
        end_dt = _parse_iso_dt(end_date_str)
    except Exception as e:
        err = f"Invalid date format: {e}"
        if task_id:
            log_loss_task_completed(task_id, success=False, error_message=err)
        return {"success": False, "device_id": device_id, "error": err}

    try:
        calc_service = CalculationService()
        result = calc_service.calculate_string_loss_sync(
            device_id=device_id,
            start_date=start_dt,
            end_date=end_dt,
            time_interval_minutes=time_interval_minutes,
        )
        if task_id:
            log_loss_task_completed(task_id, success=result.get("success", False))
        return result
    except Exception as e:
        logger.exception("run_string_loss_for_date_range failed for %s: %s", device_id, e)
        if task_id:
            log_loss_task_completed(task_id, success=False, error_message=str(e))
        return {"success": False, "device_id": device_id, "error": str(e)}


@shared_task
def calculate_jb_loss(
    jb_device_id: str,
    timestamp: Optional[datetime] = None
) -> Dict:
    """
    Calculate loss for a junction box (JB) by aggregating string results.
    
    Args:
        jb_device_id: JB device ID
        timestamp: Calculation timestamp (defaults to now)
        
    Returns:
        Dictionary with JB-level results
    """
    try:
        if timestamp is None:
            timestamp = timezone.now()
        
        # Get JB device
        try:
            jb_device = device_list.objects.get(device_id=jb_device_id)
        except device_list.DoesNotExist:
            return {
                'success': False,
                'device_id': jb_device_id,
                'error': f"JB device {jb_device_id} not found"
            }
        
        # Find all strings under this JB
        strings = device_list.objects.filter(
            device_sub_group=jb_device_id,
            device_type__icontains='string'
        )
        
        if not strings.exists():
            return {
                'success': False,
                'device_id': jb_device_id,
                'error': f"No strings found for JB {jb_device_id}"
            }
        
        # Aggregate expected and actual power from strings
        timeseries_reader = TimeseriesReader()
        timeseries_writer = TimeseriesWriter()
        
        total_expected = 0.0
        total_actual = 0.0
        string_count = 0
        
        for string in strings:
            # Get latest expected power for this string
            expected_data = timeseries_reader.get_latest_data(
                string.device_id,
                ['string_expected_power'],
                device_type='string',
                hours_back=1
            )
            
            if expected_data.get('string_expected_power'):
                total_expected += expected_data['string_expected_power']
            
            # Get latest actual power
            actual_power = timeseries_reader.get_actual_power(
                string.device_id, timestamp, device_type='string'
            )
            
            if actual_power is not None:
                total_actual += actual_power
            
            string_count += 1
        
        # Get JB actual power (if measured at JB level)
        jb_actual = timeseries_reader.get_actual_power(
            jb_device_id, timestamp, device_type='jb'
        )
        
        # Use JB actual if available, otherwise use sum of strings
        if jb_actual is not None:
            total_actual = jb_actual
        
        # Write JB-level results
        write_success = timeseries_writer.write_loss_calculation(
            device_id=jb_device_id,
            expected_power=total_expected,
            actual_power=total_actual,
            timestamp=timestamp,
            device_type='jb'
        )
        
        # Calculate loss
        power_loss = None
        loss_percentage = None
        
        if total_actual is not None:
            power_loss = total_expected - total_actual
            if total_expected > 0:
                loss_percentage = (power_loss / total_expected) * 100
        
        return {
            'success': True,
            'device_id': jb_device_id,
            'expected_power': total_expected,
            'actual_power': total_actual,
            'power_loss': power_loss,
            'loss_percentage': loss_percentage,
            'string_count': string_count,
            'error': None
        }
        
    except Exception as e:
        logger.error(f"Error calculating JB loss for {jb_device_id}: {e}", exc_info=True)
        return {
            'success': False,
            'device_id': jb_device_id,
            'error': str(e)
        }


@shared_task
def calculate_inverter_loss(
    inverter_device_id: str,
    timestamp: Optional[datetime] = None
) -> Dict:
    """
    Calculate loss for an inverter by aggregating JB or string results.
    
    Args:
        inverter_device_id: Inverter device ID
        timestamp: Calculation timestamp (defaults to now)
        
    Returns:
        Dictionary with inverter-level results
    """
    try:
        if timestamp is None:
            timestamp = timezone.now()
        
        # Get inverter device
        try:
            inverter = device_list.objects.get(device_id=inverter_device_id)
        except device_list.DoesNotExist:
            return {
                'success': False,
                'device_id': inverter_device_id,
                'error': f"Inverter {inverter_device_id} not found"
            }
        
        timeseries_reader = TimeseriesReader()
        timeseries_writer = TimeseriesWriter()
        
        # Find JBs under this inverter
        jbs = device_list.objects.filter(
            device_sub_group=inverter_device_id,
            device_type='jb'
        )
        
        total_expected = 0.0
        total_actual = 0.0
        
        if jbs.exists():
            # Aggregate from JBs
            for jb in jbs:
                jb_data = timeseries_reader.get_latest_data(
                    jb.device_id,
                    ['jb_expected_power', 'jb_actual_power'],
                    device_type='jb',
                    hours_back=1
                )
                
                if jb_data.get('jb_expected_power'):
                    total_expected += jb_data['jb_expected_power']
                
                if jb_data.get('jb_actual_power'):
                    total_actual += jb_data['jb_actual_power']
        else:
            # No JBs, aggregate directly from strings
            strings = device_list.objects.filter(
                device_sub_group=inverter_device_id,
                device_type__icontains='string'
            )
            
            for string in strings:
                string_data = timeseries_reader.get_latest_data(
                    string.device_id,
                    ['string_expected_power', 'string_actual_power'],
                    device_type='string',
                    hours_back=1
                )
                
                if string_data.get('string_expected_power'):
                    total_expected += string_data['string_expected_power']
                
                if string_data.get('string_actual_power'):
                    total_actual += string_data['string_actual_power']
        
        # Get inverter DC input (if measured)
        inverter_dc = timeseries_reader.get_actual_power(
            inverter_device_id, timestamp, device_type='inverter'
        )
        
        # Get inverter AC output
        inverter_ac_tag = timeseries_reader.metric_mapper.get_oem_tag(
            'inverter', 'ac_output', timeseries_reader.mappings
        )
        inverter_ac = None
        if inverter_ac_tag:
            inverter_ac_data = timeseries_reader.get_latest_data(
                inverter_device_id,
                ['ac_output'],
                device_type='inverter',
                hours_back=1
            )
            inverter_ac = inverter_ac_data.get('ac_output')
        
        # Use inverter DC if available, otherwise use aggregated
        if inverter_dc is not None:
            total_actual = inverter_dc
        
        # Write inverter-level results
        additional_metrics = {}
        if inverter_ac is not None:
            additional_metrics['inverter_ac_output'] = inverter_ac
            if total_actual is not None:
                additional_metrics['inverter_conversion_loss'] = total_actual - inverter_ac
        
        write_success = timeseries_writer.write_loss_calculation(
            device_id=inverter_device_id,
            expected_power=total_expected,
            actual_power=total_actual,
            timestamp=timestamp,
            device_type='inverter',
            additional_metrics=additional_metrics if additional_metrics else None
        )
        
        # Calculate loss
        power_loss = None
        loss_percentage = None
        
        if total_actual is not None:
            power_loss = total_expected - total_actual
            if total_expected > 0:
                loss_percentage = (power_loss / total_expected) * 100
        
        return {
            'success': True,
            'device_id': inverter_device_id,
            'expected_power': total_expected,
            'actual_power': total_actual,
            'ac_output': inverter_ac,
            'power_loss': power_loss,
            'loss_percentage': loss_percentage,
            'error': None
        }
        
    except Exception as e:
        logger.error(f"Error calculating inverter loss for {inverter_device_id}: {e}", exc_info=True)
        return {
            'success': False,
            'device_id': inverter_device_id,
            'error': str(e)
        }


@shared_task
def calculate_asset_losses(
    asset_code: str,
    timestamp: Optional[datetime] = None,
    device_types: Optional[List[str]] = None
) -> Dict:
    """
    Calculate losses for all devices in an asset.
    
    Args:
        asset_code: Asset code
        timestamp: Calculation timestamp (defaults to now)
        device_types: List of device types to calculate ('string', 'jb', 'inverter')
                     If None, calculates all
        
    Returns:
        Dictionary with asset-level summary
    """
    if timestamp is None:
        timestamp = timezone.now()
    
    if device_types is None:
        device_types = ['string', 'jb', 'inverter']
    
    # Get all devices for this asset
    devices = device_list.objects.filter(parent_code=asset_code)
    
    results = {
        'asset_code': asset_code,
        'timestamp': timestamp.isoformat(),
        'strings': {'total': 0, 'successful': 0, 'failed': 0},
        'jbs': {'total': 0, 'successful': 0, 'failed': 0},
        'inverters': {'total': 0, 'successful': 0, 'failed': 0}
    }
    
    # Calculate string losses
    if 'string' in device_types:
        strings = devices.filter(device_type__icontains='string')
        results['strings']['total'] = strings.count()
        
        for string in strings:
            result = calculate_string_loss.delay(
                string.device_id, timestamp, asset_code
            )
            # Note: In production, you might want to wait for results or use a callback
            # For now, we just trigger the tasks
    
    # Calculate JB losses (after strings)
    if 'jb' in device_types:
        jbs = devices.filter(device_type='jb')
        results['jbs']['total'] = jbs.count()
        
        for jb in jbs:
            calculate_jb_loss.delay(jb.device_id, timestamp)
    
    # Calculate inverter losses (after JBs)
    if 'inverter' in device_types:
        inverters = devices.filter(device_type__icontains='_inv')
        results['inverters']['total'] = inverters.count()
        
        for inverter in inverters:
            calculate_inverter_loss.delay(inverter.device_id, timestamp)
    
    return results


@shared_task(bind=True)
def run_asset_loss_for_date_range(
    self,
    asset_code: str,
    start_date: str,
    end_date: str,
    time_interval_minutes: int = 15,
) -> Dict:
    """
    Orchestrator: enqueue one Celery task per configured+enabled string device and return immediately.
    Prevents long-running single tasks and request timeouts. Actual work runs in run_string_loss_for_date_range.

    Returns:
        { "success": True, "asset_code", "asset_name", "device_count", "task_ids": [...] }
        Client can poll each task_id for per-device status.
    """
    task_id = getattr(getattr(self, "request", None), "id", None)
    if task_id:
        log_loss_task_started(task_id)

    if not asset_code:
        error_msg = "asset_code is required"
        if task_id:
            log_loss_task_completed(task_id, success=False, error_message=error_msg)
        return {"success": False, "asset_code": asset_code, "error": error_msg}
    if not start_date or not end_date:
        error_msg = "start_date and end_date are required"
        if task_id:
            log_loss_task_completed(task_id, success=False, error_message=error_msg)
        return {"success": False, "asset_code": asset_code, "error": error_msg}

    try:
        start_dt = _parse_iso_dt(start_date)
        end_dt = _parse_iso_dt(end_date)
    except Exception as e:
        error_msg = f"Invalid date format: {e}"
        if task_id:
            log_loss_task_completed(task_id, success=False, error_message=error_msg)
        return {"success": False, "asset_code": asset_code, "error": error_msg}

    try:
        try:
            asset = AssetList.objects.get(asset_code=asset_code)
            asset_name = getattr(asset, "asset_name", None)
        except AssetList.DoesNotExist:
            error_msg = f"Asset {asset_code} not found"
            if task_id:
                log_loss_task_completed(task_id, success=False, error_message=error_msg)
            return {"success": False, "asset_code": asset_code, "error": error_msg}

        strings_qs = get_configured_loss_string_devices_for_asset(asset_code)
        device_ids = list(strings_qs.values_list("device_id", flat=True))

        if not device_ids:
            if task_id:
                log_loss_task_completed(task_id, success=True, processed_devices=0, failed_devices=0)
            return {
                "success": True,
                "asset_code": asset_code,
                "asset_name": asset_name,
                "device_count": 0,
                "task_ids": [],
                "message": "No configured string devices for asset",
            }

        task_ids = []
        for dev_id in device_ids:
            t = run_string_loss_for_date_range.delay(
                device_id=dev_id,
                start_date_str=start_date,
                end_date_str=end_date,
                time_interval_minutes=time_interval_minutes,
            )
            task_ids.append(t.id)

        if task_id:
            log_loss_task_completed(
                task_id,
                success=True,
                processed_devices=len(task_ids),
                failed_devices=0,
            )

        return {
            "success": True,
            "asset_code": asset_code,
            "asset_name": asset_name,
            "device_count": len(device_ids),
            "task_ids": task_ids,
            "message": "One task per device queued; poll each task_id for status.",
        }
    except Exception as e:
        logger.exception("run_asset_loss_for_date_range failed for asset %s: %s", asset_code, e)
        error_msg = str(e)
        if task_id:
            log_loss_task_completed(task_id, success=False, error_message=error_msg)
        return {"success": False, "asset_code": asset_code, "error": error_msg}

