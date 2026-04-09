"""
Synchronous calculation service for testing and development

This service provides synchronous calculation functions that can be called
directly without Celery, optimized for database performance.
"""
from typing import Optional, Dict, List, Tuple
import logging
from datetime import datetime, timedelta
from django.utils import timezone
from django.db.models import Q
from django.db import connection

from main.models import device_list, timeseries_data, AssetList
import pytz
from .power_calculation_service import PowerCalculationService
from .timeseries_writer import TimeseriesWriter
from .timeseries_reader import TimeseriesReader
from .metric_mapping_service import MetricMappingService

logger = logging.getLogger(__name__)


class CalculationService:
    """
    Synchronous calculation service with optimized database queries.
    
    This service:
    - Calculates expected and actual power synchronously
    - Optimizes database queries (bulk reads, select_related, etc.)
    - Calculates actual_power from voltage * current
    - Writes results with timestamps from source data
    """
    
    def __init__(self):
        self.power_service = PowerCalculationService()
        self.timeseries_writer = TimeseriesWriter()
        self.timeseries_reader = TimeseriesReader()
        self.metric_mapper = MetricMappingService()
        self.mappings = self.metric_mapper.get_metric_mappings()
    
    def calculate_string_loss_sync(
        self,
        device_id: str,
        start_date: datetime,
        end_date: datetime,
        time_interval_minutes: int = 15
    ) -> Dict:
        """
        Calculate loss for a string device over a date range (synchronous).
        
        This method:
        1. Gets all timestamps with measured data (voltage/current) in the range
        2. For each timestamp, calculates expected and actual power
        3. Writes results to timeseries_data with the same timestamp
        
        Args:
            device_id: String device ID
            start_date: Start of date range
            end_date: End of date range
            time_interval_minutes: Minimum interval between calculations (default 15 min)
            
        Returns:
            Dictionary with calculation summary:
            {
                'success': True/False,
                'device_id': '...',
                'total_calculations': 100,
                'successful': 95,
                'failed': 5,
                'errors': [...],
                'results': [...]
            }
        """
        try:
            # Ensure dates are timezone-aware (handle naive datetimes from frontend)
            if timezone.is_naive(start_date):
                start_date = timezone.make_aware(start_date)
            if timezone.is_naive(end_date):
                end_date = timezone.make_aware(end_date)
            
            # Get device (unmanaged model, can't use select_related)
            try:
                device = device_list.objects.get(device_id=device_id)
            except device_list.DoesNotExist:
                return {
                    'success': False,
                    'device_id': device_id,
                    'error': f'Device {device_id} not found'
                }
            
            asset_code = device.parent_code
            
            # CRITICAL: Get asset timezone and convert date range from local time to UTC
            # The dates might be in UTC, but we need to ensure we're querying for the full day in local time
            try:
                asset = AssetList.objects.get(asset_code=asset_code)
                # Parse timezone offset (e.g., '+09:00' or '-08:00')
                tz_offset = asset.timezone
                # Convert to pytz timezone (UTC offset)
                hours, minutes = map(int, tz_offset.replace('+', '').replace('-', '').split(':'))
                total_offset = hours * 60 + minutes
                if tz_offset.startswith('-'):
                    total_offset = -total_offset
                
                # Create timezone-aware datetime objects
                site_timezone = pytz.FixedOffset(total_offset)
                
                # CRITICAL: Convert date range from local time to UTC
                # The dates coming in likely represent the full day in local timezone
                # Extract just the date part and create local timezone datetime
                # Then convert to UTC for database queries
                local_start = site_timezone.localize(
                    datetime(start_date.year, start_date.month, start_date.day, 0, 0, 0)
                )
                local_end = site_timezone.localize(
                    datetime(end_date.year, end_date.month, end_date.day, 23, 59, 59, 999999)
                )
                # Convert to UTC for database queries
                start_date_utc = local_start.astimezone(pytz.UTC)
                end_date_utc = local_end.astimezone(pytz.UTC)
                
                    # Timezone conversion completed
                
                # Update the date variables to use UTC
                start_date = start_date_utc
                end_date = end_date_utc
            except AssetList.DoesNotExist:
                logger.warning(f"Asset {asset_code} not found in AssetList, using dates as-is (assuming UTC)")
            except Exception as e:
                logger.warning(f"Error parsing timezone for asset {asset_code}: {e}, using dates as-is")
            
            weather_config = getattr(device, 'weather_device_config', None)
            
            # Get metric names for voltage and current
            voltage_metric = self._get_string_metric_name('voltage')
            current_metric = self._get_string_metric_name('current')
            
            if not voltage_metric or not current_metric:
                return {
                    'success': False,
                    'device_id': device_id,
                    'error': 'Voltage or current metric not configured in device_mapping'
                }
            
            # NEW APPROACH: Process both irradiance timestamps AND voltage/current timestamps
            # 1. Calculate expected power for ALL irradiance timestamps
            # 2. Calculate actual power for ALL voltage/current pairs
            
            # Get all timestamps where irradiance is available
            # NOTE: This is just for logging - we'll fetch ALL irradiance data separately
            irradiance_timestamps = self._get_irradiance_timestamps(
                asset_code,
                weather_config,
                start_date,
                end_date
            )
            
            # Found irradiance timestamps (for reference only, we fetch all data separately)
            
            # Get voltage and current timestamps for the string device
            voltage_timestamps = set(
                timeseries_data.objects.filter(
                    device_id=device_id,
                    metric=voltage_metric,
                    ts__gte=start_date,
                    ts__lte=end_date
                ).values_list('ts', flat=True).distinct()
            )
            
            current_timestamps = set(
                timeseries_data.objects.filter(
                    device_id=device_id,
                    metric=current_metric,
                    ts__gte=start_date,
                    ts__lte=end_date
                ).values_list('ts', flat=True).distinct()
            )
            
            # Get timestamps that have both voltage and current (for actual power calculation)
            # CRITICAL: Only use timestamps where BOTH voltage AND current exist at the exact same timestamp
            voltage_current_timestamps = sorted(voltage_timestamps & current_timestamps)
            
            # Combine all timestamps: irradiance timestamps + voltage/current timestamps
            # This allows us to calculate expected power for irradiance timestamps
            # and actual power for voltage/current timestamps
            all_timestamps_set = set(irradiance_timestamps) | set(voltage_current_timestamps)
            all_timestamps = sorted(all_timestamps_set)
            
            if not all_timestamps:
                return {
                    'success': False,
                    'device_id': device_id,
                    'error': f'No timestamps with irradiance or voltage/current data found in range'
                }
            
            # CRITICAL: Calculate expected power for ALL irradiance timestamps (no interval filtering)
            # This ensures expected_power is calculated for every available irradiance data point
            # Use all irradiance timestamps directly - no filtering
            filtered_irradiance_timestamps = sorted(irradiance_timestamps)
            filtered_irradiance_timestamps_set = set(filtered_irradiance_timestamps)  # For fast lookup
            
            # CRITICAL: Process ALL timestamps where both voltage AND current exist
            # Do NOT filter by interval for actual power - we want to calculate it for every available data point
            # This ensures actual_power is calculated whenever voltage and current are both available
            
            # CRITICAL: Process ALL irradiance timestamps for expected power calculation
            # AND ALL voltage/current timestamps for actual power calculation
            # These are independent - expected_power should be calculated for ALL irradiance data
            all_filtered_timestamps = sorted(set(filtered_irradiance_timestamps) | set(voltage_current_timestamps))
            
            # Bulk fetch voltage and current data
            # CRITICAL: Only fetch data for timestamps where BOTH voltage AND current exist
            # This ensures we only calculate actual_power when both are available at the exact same timestamp
            voltage_data = {}
            current_data = {}
            
            # Only fetch voltage/current data for timestamps where BOTH exist
            # This prevents calculating actual_power when only one is available
            if voltage_current_timestamps:
                voltage_data = self._bulk_fetch_metric(
                    device_id, voltage_metric, sorted(voltage_current_timestamps)
                )
                current_data = self._bulk_fetch_metric(
                    device_id, current_metric, sorted(voltage_current_timestamps)
                )
            
            # CRITICAL: Fetch ALL irradiance data in the date range, not just specific timestamps
            # This ensures we don't miss any irradiance values due to query mismatches
            # We'll check for irradiance at every timestamp we process
            irradiance_data = {}
            if weather_config and weather_config.get('irradiance_devices'):
                # Fetch all irradiance data in the entire date range
                irradiance_data = self._bulk_fetch_all_irradiance_data(
                    asset_code,
                    weather_config,
                    start_date,
                    end_date
                )
            
            # CRITICAL: Process ALL timestamps that have either irradiance OR voltage/current data
            # Expected power should be calculated for ALL irradiance timestamps
            # Actual power should be calculated for ALL voltage/current timestamps
            # These are independent calculations
            
            # Include ALL timestamps that have irradiance data (from the fetched data)
            # This ensures we process every timestamp with irradiance, even if it wasn't in the initial query
            all_irradiance_timestamps = set(irradiance_data.keys())
            all_processing_timestamps = sorted(set(all_irradiance_timestamps) | set(voltage_current_timestamps))
            
            # Processing timestamps with irradiance and/or voltage/current data
            
            results = []
            rows_for_db = []
            successful = 0
            failed = 0
            errors = []
            expected_power_calculated = 0
            expected_power_skipped = 0
            # Aggregate per-step timing (ms) across all expected-power calculations
            timing_totals_ms = {}
            timing_keys = (
                'get_module_ds_ms', 'get_fitted_parameters_ms',
                'param_cache_ms', 'param_db_read_ms', 'param_fit_sdm_ms', 'param_db_write_ms',
                'estimate_power_vmpp_ms', 'total_ms'
            )
            for k in timing_keys:
                timing_totals_ms[k] = 0.0
            
            # Process each timestamp that has either irradiance or voltage/current data
            # NOTE: This processes timestamps one-by-one in a loop, but data fetching is done in bulk above
            total_timestamps = len(all_processing_timestamps)
            logger.debug(f"Processing {total_timestamps} timestamps for device {device_id} (bulk data fetched, processing sequentially)")
            for timestamp in all_processing_timestamps:
                try:
                    # Get voltage and current for this timestamp (if available)
                    # CRITICAL: Only use EXACT timestamp matches - no tolerance
                    # This ensures actual_power is only written when voltage AND current exist at the exact same timestamp
                    # Simple calculation: actual_power = voltage * current
                    voltage_at_exact = voltage_data.get(timestamp)
                    current_at_exact = current_data.get(timestamp)
                    
                    # Calculate actual power ONLY if both voltage and current exist at this exact timestamp
                    # IMPORTANT: Check that both are not None (0.0 is a valid value, but None means missing)
                    actual_power = None
                    if voltage_at_exact is not None and current_at_exact is not None:
                        # Both exist at exact timestamp - calculate actual power
                        # Simple formula: actual_power = voltage * current
                        # This will calculate even if result is 0.0 (which is valid when current=0 or voltage=0)
                        actual_power = float(voltage_at_exact) * float(current_at_exact)
                    
                    # Initialize metrics to write
                    metrics_to_write = {}
                    
                    # Initialize weather variable (may be used later for result entry)
                    weather = {}
                    
                    # Calculate expected power for ALL timestamps where irradiance data exists
                    # CRITICAL: expected_power timestamps must match irradiance timestamps exactly
                    # Check if irradiance data exists at this exact timestamp
                    # We've already fetched ALL irradiance data in the date range, so this check will work for all timestamps
                    expected_power = None
                    irradiance_at_exact = irradiance_data.get(timestamp)
                    
                    if irradiance_at_exact is not None:
                        # We have irradiance at this exact timestamp - calculate expected power
                        expected_power_calculated += 1
                        # Get temperature data for this timestamp (with tolerance for temperature since it's less critical)
                        weather = self.timeseries_reader.get_weather_data(
                            asset_code,
                            timestamp,
                            weather_device_config=weather_config,
                            tolerance_minutes=15
                        )
                        # Store irradiance in weather dict for result entry
                        weather['irradiance'] = irradiance_at_exact
                        
                        # Get temperature (module_temp, ambient_temp, or fallback to temperature)
                        module_temp = weather.get('module_temp')
                        ambient_temp = weather.get('ambient_temp')
                        temperature = weather.get('temperature')
                        
                        # If no module_temp or ambient_temp, try to use temperature as ambient_temp
                        # and estimate module_temp from irradiance
                        if not module_temp and not ambient_temp:
                            if temperature:
                                ambient_temp = temperature
                                # Estimate module_temp from ambient_temp and irradiance
                                # Simple estimation: module_temp ≈ ambient_temp + (irradiance / 1000) * 25
                                # This is a rough approximation
                                module_temp = temperature + (irradiance_at_exact / 1000) * 25
                            else:
                                # No temperature data at all - use default estimation
                                # Estimate ambient_temp from irradiance (rough approximation)
                                ambient_temp = 25 + (irradiance_at_exact / 1000) * 10
                                module_temp = ambient_temp + (irradiance_at_exact / 1000) * 25
                                # Using estimated temperature values
                        elif not module_temp and ambient_temp:
                            # Have ambient_temp but not module_temp - estimate module_temp
                            module_temp = ambient_temp + (irradiance_at_exact / 1000) * 25
                        elif module_temp and not ambient_temp:
                            # Have module_temp but not ambient_temp - estimate ambient_temp
                            ambient_temp = module_temp - (irradiance_at_exact / 1000) * 25
                        
                        # Calculate expected power using exact irradiance value
                        # CRITICAL: Always calculate expected_power when irradiance exists, even for low values
                        try:
                            power_result = self.power_service.calculate_expected_power(
                                device=device,
                                irradiance=irradiance_at_exact,
                                module_temp=module_temp,
                                ambient_temp=ambient_temp,
                                timestamp=timestamp
                            )
                            expected_power = power_result.expected_power
                            # Aggregate per-step timing for display in loss calculation result
                            breakdown = (power_result.details or {}).get('timing_breakdown_ms') or {}
                            if isinstance(breakdown, dict):
                                for k in timing_keys:
                                    if k in breakdown and breakdown[k] is not None:
                                        timing_totals_ms[k] = timing_totals_ms.get(k, 0) + float(breakdown[k])
                            
                            # CRITICAL: Always write expected_power when irradiance exists, even if result is 0 or very small
                            # This ensures we have expected_power values for all irradiance timestamps
                            # Note: 0.0 is a valid value (means no power generation at low irradiance)
                            if expected_power is not None:
                                metrics_to_write['string_expected_power'] = float(expected_power)
                                # Expected power calculated successfully
                            else:
                                logger.warning(
                                    f"Power calculation returned None for irradiance={irradiance_at_exact:.2f}W/m² at {timestamp}"
                                )
                                # Still write 0 if calculation returns None (shouldn't happen, but handle it)
                                metrics_to_write['string_expected_power'] = 0.0
                                expected_power = 0.0
                        except Exception as e:
                            logger.error(
                                f"Power calculation failed for {timestamp} with irradiance={irradiance_at_exact:.2f}W/m²: {e}",
                                exc_info=True
                            )
                            errors.append(f"{timestamp}: Power calculation failed - {str(e)}")
                            # CRITICAL: Even if calculation fails, write 0 to ensure we have a value for this timestamp
                            # This ensures expected_power exists for all irradiance timestamps
                            metrics_to_write['string_expected_power'] = 0.0
                            expected_power = 0.0
                    else:
                        # No irradiance data at this timestamp
                        if timestamp in all_irradiance_timestamps:
                            # This shouldn't happen - timestamp is in set but data not found
                            logger.warning(f"Timestamp {timestamp} in irradiance set but data not found in irradiance_data dict")
                            expected_power_skipped += 1
                    
                    # Write actual power if available (regardless of irradiance)
                    # Only write when both voltage and current exist at the exact same timestamp
                    if actual_power is not None:
                        metrics_to_write['string_actual_power'] = actual_power
                        
                        # Calculate loss metrics only if both expected and actual power are available
                        if expected_power is not None:
                            power_loss = expected_power - actual_power
                            loss_percentage = (power_loss / expected_power * 100) if expected_power > 0 else 0
                            metrics_to_write.update({
                                'string_power_loss': power_loss,
                                'string_loss_percentage': loss_percentage,
                            })
                    
                    # Only persist if we have at least one metric to write
                    if not metrics_to_write:
                        continue

                    # Accumulate rows for a single staging-based write at the end
                    rows_for_db.append((timestamp, dict(metrics_to_write)))

                    result_entry = {
                        'timestamp': timestamp.isoformat(),
                    }
                    if expected_power is not None:
                        result_entry['expected_power'] = expected_power
                    if actual_power is not None:
                        result_entry['actual_power'] = actual_power
                    if expected_power is not None and actual_power is not None:
                        result_entry.update({
                            'power_loss': metrics_to_write.get('string_power_loss'),
                            'loss_percentage': metrics_to_write.get('string_loss_percentage'),
                        })
                    if weather.get('irradiance'):
                        result_entry['irradiance'] = weather['irradiance']
                    if weather.get('temperature'):
                        result_entry['temperature'] = weather.get('temperature')
                    results.append(result_entry)
                    successful += 1
                        
                except Exception as e:
                    logger.error(f"Error processing {timestamp}: {e}", exc_info=True)
                    failed += 1
                    errors.append(f"{timestamp}: {str(e)}")
            
            # Persist all accumulated rows in one staging-based operation
            if rows_for_db:
                write_ok = self.timeseries_writer.write_loss_range_with_staging(
                    device_id=device_id,
                    rows=rows_for_db,
                    start_ts=start_date,
                    end_ts=end_date,
                    device_type='string',
                )
                if not write_ok:
                    errors.append("Failed to persist loss results for range")
                    failed += len(rows_for_db)

            # Calculation complete — add per-step timing (total and average per expected-power calc)
            n_calc = max(expected_power_calculated, 1)
            timing_breakdown_ms_avg = {k: round(timing_totals_ms[k] / n_calc, 2) for k in timing_keys}
            timing_breakdown_ms_total_rounded = {k: round(timing_totals_ms[k], 2) for k in timing_keys}
            
            return {
                'success': True,
                'device_id': device_id,
                'total_calculations': len(all_processing_timestamps),
                'successful': successful,
                'failed': failed,
                'expected_power_calculated': expected_power_calculated,
                'expected_power_skipped': expected_power_skipped,
                'errors': errors[:10],  # Limit errors to first 10
                'results': results[:100],  # Limit results to first 100 for response
                'timing_breakdown_ms_total': timing_breakdown_ms_total_rounded,
                'timing_breakdown_ms_avg_per_calc': timing_breakdown_ms_avg,
            }
            
        except Exception as e:
            logger.error(f"Error in calculate_string_loss_sync: {e}", exc_info=True)
            return {
                'success': False,
                'device_id': device_id,
                'error': str(e)
            }

    def get_loss_summary(
        self,
        device_id: Optional[str] = None,
        asset_code: Optional[str] = None,
        hours: int = 24,
    ) -> Dict:
        """
        Compute latest expected/actual power and loss metrics for a device or asset.

        This mirrors the logic previously implemented in api_get_loss_summary view
        but is reusable from non-view contexts.
        """
        if not device_id and not asset_code:
            raise ValueError("device_id or asset_code is required")

        cutoff_time = timezone.now() - timedelta(hours=hours)

        if device_id:
            query = Q(
                device_id=device_id,
                ts__gte=cutoff_time,
            )
        else:
            devices = device_list.objects.filter(parent_code=asset_code).values_list(
                "device_id", flat=True
            )
            query = Q(
                device_id__in=list(devices),
                ts__gte=cutoff_time,
            )

        query_expected = query & Q(metric__icontains="expected_power")
        query_actual = query & Q(metric__icontains="actual_power")

        expected_data = timeseries_data.objects.filter(query_expected).order_by("-ts").first()
        actual_data = timeseries_data.objects.filter(query_actual).order_by("-ts").first()

        summary = {
            "device_id": device_id,
            "asset_code": asset_code,
            "hours": hours,
            "latest_timestamp": None,
            "expected_power": None,
            "actual_power": None,
            "power_loss": None,
            "loss_percentage": None,
        }

        if expected_data:
            try:
                summary["expected_power"] = float(expected_data.value)
                summary["latest_timestamp"] = expected_data.ts.isoformat()
            except (ValueError, TypeError):
                pass

        if actual_data:
            try:
                summary["actual_power"] = float(actual_data.value)
                if summary["latest_timestamp"] is None:
                    summary["latest_timestamp"] = actual_data.ts.isoformat()
            except (ValueError, TypeError):
                pass

        if summary["expected_power"] is not None and summary["actual_power"] is not None:
            summary["power_loss"] = summary["expected_power"] - summary["actual_power"]
            if summary["expected_power"] > 0:
                summary["loss_percentage"] = (
                    summary["power_loss"] / summary["expected_power"]
                ) * 100

        return summary
    
    def _get_string_metric_name(self, metric_type: str) -> Optional[str]:
        """
        Get metric name for string voltage or current to query timeseries_data.
        
        This method:
        1. First checks device_mapping table for configured metric names
        2. Falls back to standard metric names used in timeseries_data table
        
        The returned metric name is used directly to query timeseries_data table.
        
        Args:
            metric_type: 'voltage' or 'current'
            
        Returns:
            Metric name to use when querying timeseries_data (e.g., 'string_voltage', 'string_current')
        """
        # Try to get from device_mapping first (for configurability)
        # The mapping's 'metric' field should contain the metric name used in timeseries_data
        possible_names = [
            f'string_{metric_type}',  # e.g., 'string_voltage', 'string_current'
            f'{metric_type}',  # e.g., 'voltage', 'current'
            f'string_{metric_type}_measured',
        ]
        
        for name in possible_names:
            mapping = self.metric_mapper.get_metric_for_device_type(
                'string', name, self.mappings
            )
            if mapping:
                # The 'metric' field from device_mapping contains the actual metric name in timeseries_data
                metric_name = mapping.get('metric')
                if metric_name:
                    return metric_name
        
        # If not found in mappings, use standard metric names from timeseries_data
        # These are the actual metric column values used in the timeseries_data table
        standard_metrics = {
            'voltage': 'string_voltage',  # Direct metric name in timeseries_data
            'current': 'string_current'   # Direct metric name in timeseries_data
        }
        
        if metric_type in standard_metrics:
            metric_name = standard_metrics[metric_type]
            return metric_name
        
        logger.warning(f"Could not determine metric name for string/{metric_type}")
        return None
    
    def _get_irradiance_timestamps(
        self,
        asset_code: str,
        weather_config: Optional[Dict],
        start_date: datetime,
        end_date: datetime
    ) -> List[datetime]:
        """
        Get all timestamps where irradiance data is available.
        
        Args:
            asset_code: Asset code
            weather_config: Weather device configuration
            start_date: Start of date range
            end_date: End of date range
            
        Returns:
            Sorted list of timestamps with irradiance data
        """
        if not weather_config or not weather_config.get('irradiance_devices'):
            return []
        
        irradiance_devices = weather_config['irradiance_devices']
        if not isinstance(irradiance_devices, list) or len(irradiance_devices) == 0:
            return []
        
        # Collect all timestamps from all irradiance devices
        all_timestamps = set()
        
        # Support both old format (device IDs) and new format (device+metric pairs)
        if isinstance(irradiance_devices[0], dict):
            # New format: list of {device_id, metric}
            for device_config in irradiance_devices:
                device_id = device_config.get('device_id')
                metric = device_config.get('metric')
                if device_id and metric:
                    # Try both metric and oem_metric fields (data might be stored in either)
                    timestamps = timeseries_data.objects.filter(
                        Q(device_id=device_id) &
                        (Q(metric=metric) | Q(oem_metric=metric)) &
                        Q(ts__gte=start_date) &
                        Q(ts__lte=end_date)
                    ).values_list('ts', flat=True).distinct()
                    all_timestamps.update(timestamps)
        else:
            # Old format: list of device IDs, use mapped metric
            # Get irradiance metric tag from mappings
            irradiance_tag = self.metric_mapper.get_oem_tag('weather', 'irradiance', self.mappings)
            if not irradiance_tag:
                # Try using standard metric name
                irradiance_tag = 'irradiance'
            
            for device_id in irradiance_devices:
                # Try both oem_metric and metric fields
                timestamps = timeseries_data.objects.filter(
                    Q(device_id=device_id) &
                    (Q(oem_metric=irradiance_tag) | Q(metric=irradiance_tag)) &
                    Q(ts__gte=start_date) &
                    Q(ts__lte=end_date)
                ).values_list('ts', flat=True).distinct()
                all_timestamps.update(timestamps)
        
        return sorted(all_timestamps)
    
    def _bulk_fetch_metric(
        self,
        device_id: str,
        metric_name: str,
        timestamps: List[datetime]
    ) -> Dict[datetime, float]:
        """
        Bulk fetch metric values for multiple timestamps (optimized).
        
        Args:
            device_id: Device ID
            metric_name: Metric name
            timestamps: List of timestamps (should be exact timestamps from database)
            
        Returns:
            Dictionary mapping timestamp to value (exact timestamp matches only)
        """
        if not timestamps:
            return {}
        
        # CRITICAL: Use exact timestamp matching - no tolerance
        # This ensures we only get data for the exact timestamps we're looking for
        # Convert timestamps to a set for fast lookup
        timestamp_set = set(timestamps)
        
        # Optimized: Fetch all data in one query using exact timestamp matching
        # Use __in for exact matching
        data = list(
            timeseries_data.objects.filter(
                device_id=device_id,
                metric=metric_name,
                ts__in=timestamp_set
            ).values('ts', 'value')
        )
        
        # Map exact timestamps to values
        result = {}
        for record in data:
            record_ts = record['ts']
            # Only include if it's in our timestamp set (exact match)
            if record_ts in timestamp_set:
                try:
                    result[record_ts] = float(record['value'])
                except (ValueError, TypeError):
                    continue
        
        return result
    
    def _bulk_fetch_irradiance_data(
        self,
        asset_code: str,
        weather_config: Dict,
        timestamps: List[datetime]
    ) -> Dict[datetime, float]:
        """
        Bulk fetch irradiance data for multiple timestamps using exact timestamp matching.
        
        Args:
            asset_code: Asset code
            weather_config: Weather device configuration
            timestamps: List of timestamps (should be exact timestamps from database)
            
        Returns:
            Dictionary mapping timestamp to irradiance value (exact timestamp matches only)
        """
        if not timestamps or not weather_config or not weather_config.get('irradiance_devices'):
            return {}
        
        # Convert timestamps to a set for fast lookup
        timestamp_set = set(timestamps)
        
        irradiance_devices = weather_config['irradiance_devices']
        if not isinstance(irradiance_devices, list) or len(irradiance_devices) == 0:
            return {}
        
        result = {}
        
        # Support both old format (device IDs) and new format (device+metric pairs)
        if isinstance(irradiance_devices[0], dict):
            # New format: list of {device_id, metric}
            for device_config in irradiance_devices:
                device_id = device_config.get('device_id')
                metric = device_config.get('metric')
                if device_id and metric:
                    # Fetch data using exact timestamp matching
                    data = list(
                        timeseries_data.objects.filter(
                            device_id=device_id,
                            metric=metric,
                            ts__in=timestamp_set
                        ).values('ts', 'value')
                    )
                    
                    # Map exact timestamps to values
                    for record in data:
                        record_ts = record['ts']
                        if record_ts in timestamp_set and record_ts not in result:
                            try:
                                result[record_ts] = float(record['value'])
                            except (ValueError, TypeError):
                                continue
        else:
            # Old format: list of device IDs, use mapped metric
            # Get irradiance metric tag from mappings
            irradiance_tag = self.metric_mapper.get_oem_tag('weather', 'irradiance', self.mappings)
            if not irradiance_tag:
                # Try using standard metric name
                irradiance_tag = 'irradiance'
            
            for device_id in irradiance_devices:
                # Try both oem_metric and metric fields with exact timestamp matching
                data = list(
                    timeseries_data.objects.filter(
                        Q(device_id=device_id) &
                        (Q(oem_metric=irradiance_tag) | Q(metric=irradiance_tag)) &
                        Q(ts__in=timestamp_set)
                    ).values('ts', 'value')
                )
                
                # Map exact timestamps to values (only if not already found)
                for record in data:
                    record_ts = record['ts']
                    if record_ts in timestamp_set and record_ts not in result:
                        try:
                            result[record_ts] = float(record['value'])
                        except (ValueError, TypeError):
                            continue
        
        return result
    
    def _bulk_fetch_all_irradiance_data(
        self,
        asset_code: str,
        weather_config: Dict,
        start_date: datetime,
        end_date: datetime
    ) -> Dict[datetime, float]:
        """
        Fetch ALL irradiance data in the date range (not just specific timestamps).
        This ensures we don't miss any irradiance values.
        
        Args:
            asset_code: Asset code
            weather_config: Weather device configuration
            start_date: Start of date range
            end_date: End of date range
            
        Returns:
            Dictionary mapping timestamp to irradiance value
        """
        if not weather_config or not weather_config.get('irradiance_devices'):
            return {}
        
        irradiance_devices = weather_config['irradiance_devices']
        if not isinstance(irradiance_devices, list) or len(irradiance_devices) == 0:
            return {}
        
        result = {}
        
        # Support both old format (device IDs) and new format (device+metric pairs)
        if isinstance(irradiance_devices[0], dict):
            # New format: list of {device_id, metric}
            # Using new format for irradiance devices
            for device_config in irradiance_devices:
                device_id = device_config.get('device_id')
                metric = device_config.get('metric')
                if device_id and metric:
                    # First, check what metrics exist for this device in the date range
                    all_metrics = timeseries_data.objects.filter(
                        device_id=device_id,
                        ts__gte=start_date,
                        ts__lte=end_date
                    ).values_list('metric', 'oem_metric').distinct()
                    
                    # Check if there are other irradiance-related metrics (for warning only)
                    all_metrics = timeseries_data.objects.filter(
                        device_id=device_id,
                        ts__gte=start_date,
                        ts__lte=end_date
                    ).values_list('metric', 'oem_metric').distinct()
                    
                    irradiance_metrics = [m for m in all_metrics if m[0] in ['gii', 'ghi', 'irradiance'] or (m[1] and 'irrad' in m[1].lower())]
                    if len(irradiance_metrics) > 1:
                        logger.warning(
                            f"Found {len(irradiance_metrics)} irradiance-related metrics: {[m[0] or '(empty)' for m in irradiance_metrics]}. "
                            f"Currently only using '{metric}'. CSV export might include other metrics."
                        )
                    
                    # Fetch ALL data in date range
                    # CRITICAL: Query for ALL records with this metric, not just unique timestamps
                    # The CSV export shows 243 values, so we need to ensure we get all records
                    # Query separately for metric and oem_metric to ensure we get all records
                    # Then combine and deduplicate by timestamp (for expected power, we only need one value per timestamp)
                    # But first, let's check if there are multiple records per timestamp
                    
                    # Get all records (not just unique timestamps) to see if there are duplicates
                    all_records_metric = list(
                        timeseries_data.objects.filter(
                            device_id=device_id,
                            metric=metric,
                            ts__gte=start_date,
                            ts__lte=end_date
                        ).values('ts', 'value', 'id').order_by('ts', 'id')
                    )
                    
                    # Check for duplicate timestamps
                    timestamp_counts = {}
                    for record in all_records_metric:
                        ts = record['ts']
                        timestamp_counts[ts] = timestamp_counts.get(ts, 0) + 1
                    
                    duplicates = {ts: count for ts, count in timestamp_counts.items() if count > 1}
                    if duplicates:
                        logger.warning(
                            f"Found {len(duplicates)} timestamps with multiple records for metric '{metric}'. "
                            f"Total records: {len(all_records_metric)}, Unique timestamps: {len(timestamp_counts)}"
                        )
                    
                    # For expected power calculation, we only need one value per timestamp
                    # Use the data, deduplicating by timestamp (keep first occurrence)
                    data_by_metric = []
                    seen_timestamps = set()
                    for record in all_records_metric:
                        ts = record['ts']
                        if ts not in seen_timestamps:
                            data_by_metric.append({'ts': ts, 'value': record['value']})
                            seen_timestamps.add(ts)
                    
                    data_by_oem = list(
                        timeseries_data.objects.filter(
                            device_id=device_id,
                            oem_metric=metric,
                            ts__gte=start_date,
                            ts__lte=end_date
                        ).values('ts', 'value').order_by('ts')
                    )
                    
                    # Combine and deduplicate by timestamp
                    # CRITICAL: If there are multiple records per timestamp, we need to handle them
                    # For expected power calculation, we only need one value per timestamp
                    # Strategy: Use the most recent value if duplicates exist (order by ts desc, then take first)
                    all_data_dict = {}
                    
                    # Process oem_metric records first
                    for record in data_by_oem:
                        record_ts = record['ts']
                        if record_ts not in all_data_dict:
                            all_data_dict[record_ts] = record
                    
                    # Process metric records (will overwrite oem_metric if same timestamp)
                    for record in data_by_metric:
                        record_ts = record['ts']
                        if record_ts not in all_data_dict:
                            all_data_dict[record_ts] = record
                        else:
                            # If duplicate timestamp, keep the metric value (prefer metric over oem_metric)
                            all_data_dict[record_ts] = record
                    
                    data = list(all_data_dict.values())
                    
                    # Check for duplicate timestamps in the raw data
                    metric_timestamps = [r['ts'] for r in data_by_metric]
                    oem_timestamps = [r['ts'] for r in data_by_oem]
                    all_timestamps = metric_timestamps + oem_timestamps
                    unique_timestamps_count = len(set(all_timestamps))
                    duplicate_count = len(all_timestamps) - unique_timestamps_count
                    
                    # Fetched and deduplicated irradiance data
                    
                    # Map timestamps to values (only if not already found from another device)
                    # CRITICAL: Include ALL values, even 0.0, as they are valid irradiance measurements
                    for record in data:
                        record_ts = record['ts']
                        if record_ts not in result:
                            try:
                                value = float(record['value'])
                                # Include all values, including 0.0 (valid for nighttime/low irradiance)
                                result[record_ts] = value
                            except (ValueError, TypeError):
                                logger.warning(f"Could not convert irradiance value to float for timestamp {record_ts}: {record.get('value')}")
                                continue
        else:
            # Old format: list of device IDs, use mapped metric
            # Get irradiance metric tag from mappings
            irradiance_tag = self.metric_mapper.get_oem_tag('weather', 'irradiance', self.mappings)
            if not irradiance_tag:
                # Try using standard metric name
                irradiance_tag = 'irradiance'
            
            for device_id in irradiance_devices:
                # Fetch ALL data in date range using both oem_metric and metric fields
                data = list(
                    timeseries_data.objects.filter(
                        Q(device_id=device_id) &
                        (Q(oem_metric=irradiance_tag) | Q(metric=irradiance_tag)) &
                        Q(ts__gte=start_date) &
                        Q(ts__lte=end_date)
                    ).values('ts', 'value')
                )
                
                # Fetched irradiance records
                
                # Map timestamps to values (only if not already found from another device)
                # CRITICAL: Include ALL values, even 0.0, as they are valid irradiance measurements
                for record in data:
                    record_ts = record['ts']
                    if record_ts not in result:
                        try:
                            value = float(record['value'])
                            # Include all values, including 0.0 (valid for nighttime/low irradiance)
                            result[record_ts] = value
                        except (ValueError, TypeError):
                            logger.warning(f"Could not convert irradiance value to float for timestamp {record_ts}: {record.get('value')}")
                            continue
        
        return result
    
    def _filter_by_interval(
        self,
        timestamps: List[datetime],
        interval_minutes: int
    ) -> List[datetime]:
        """
        Filter timestamps to respect minimum interval.
        
        Args:
            timestamps: Sorted list of timestamps
            interval_minutes: Minimum interval between timestamps
            
        Returns:
            Filtered list of timestamps
        """
        if not timestamps or interval_minutes <= 0:
            return timestamps
        
        filtered = [timestamps[0]]
        interval = timedelta(minutes=interval_minutes)
        
        for ts in timestamps[1:]:
            if ts - filtered[-1] >= interval:
                filtered.append(ts)
        
        return filtered
    
    def _get_value_with_tolerance(
        self,
        data_dict: Dict[datetime, float],
        target_timestamp: datetime,
        tolerance_minutes: float = 5
    ) -> Optional[float]:
        """
        Get value from dictionary using tolerance matching.
        This is needed because voltage/current timestamps might not match exactly.
        
        Args:
            data_dict: Dictionary mapping timestamp to value
            target_timestamp: Target timestamp to find
            tolerance_minutes: Tolerance in minutes
            
        Returns:
            Value if found within tolerance, None otherwise
        """
        if not data_dict:
            return None
        
        # First try exact match (fastest)
        if target_timestamp in data_dict:
            return data_dict[target_timestamp]
        
        # If no exact match, use tolerance matching
        tolerance = timedelta(minutes=tolerance_minutes)
        closest_value = None
        min_diff = float('inf')
        
        for ts, value in data_dict.items():
            diff = abs((ts - target_timestamp).total_seconds())
            if diff <= tolerance.total_seconds() and diff < min_diff:
                min_diff = diff
                closest_value = value
        
        return closest_value

