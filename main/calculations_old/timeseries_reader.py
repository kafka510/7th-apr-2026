"""
Timeseries Reader Utility

Reads actual power and weather data from timeseries_data table for loss calculations.
"""
from typing import Optional, Dict, List, Tuple
import logging
from datetime import datetime, timedelta
from django.db import connection
from django.utils import timezone
from django.db.models import Q

from main.models import timeseries_data
from .metric_mapping_service import MetricMappingService

logger = logging.getLogger(__name__)


class TimeseriesReader:
    """
    Utility class for reading timeseries data for loss calculations.
    
    Uses metric mappings from device_mapping to find correct metric names.
    """
    
    def __init__(self):
        self.metric_mapper = MetricMappingService()
        self.mappings = self.metric_mapper.get_metric_mappings()
    
    def get_actual_power(
        self,
        device_id: str,
        timestamp: Optional[datetime] = None,
        device_type: Optional[str] = None,
        tolerance_minutes: int = 5
    ) -> Optional[float]:
        """
        Get actual power for a device at a specific timestamp.
        
        Args:
            device_id: Device ID
            timestamp: Target timestamp (defaults to now)
            device_type: Device type ('string', 'jb', 'inverter')
            tolerance_minutes: Time window to search for data (default 5 minutes)
            
        Returns:
            Actual power value (W) or None if not found
        """
        try:
            # Auto-detect device_type if not provided
            if device_type is None:
                device_type = self._detect_device_type(device_id)
            
            # Get metric name for actual_power (use standardized metric name)
            # The metric field from device_mapping is what's stored in timeseries_data.metric
            mapping = self.metric_mapper.get_metric_for_device_type(
                device_type, 'actual_power', self.mappings
            )
            
            if not mapping:
                logger.warning(
                    f"No mapping found for {device_type}/actual_power, "
                    f"cannot fetch actual power for {device_id}"
                )
                return None
            
            # Use the metric field (standardized name) to query timeseries_data
            metric_name = mapping.get('metric')
            if not metric_name:
                # Fallback: try to construct metric name
                metric_name = f'{device_type}_actual_power'
            
            # Use current time if timestamp not provided
            if timestamp is None:
                timestamp = timezone.now()
            
            # Calculate time window
            start_time = timestamp - timedelta(minutes=tolerance_minutes)
            end_time = timestamp + timedelta(minutes=tolerance_minutes)
            
            # Query timeseries_data using metric field
            data = timeseries_data.objects.filter(
                device_id=device_id,
                metric=metric_name,  # Use metric field (standardized name)
                ts__gte=start_time,
                ts__lte=end_time
            ).order_by('-ts').first()
            
            if data:
                try:
                    return float(data.value)
                except (ValueError, TypeError):
                    logger.warning(
                        f"Invalid value format for {device_id} at {timestamp}: {data.value}"
                    )
                    return None
            
            return None
            
        except Exception as e:
            logger.error(
                f"Error fetching actual power for {device_id}: {e}",
                exc_info=True
            )
            return None
    
    def get_weather_data(
        self,
        asset_code: str,
        timestamp: Optional[datetime] = None,
        tolerance_minutes: int = 15,
        weather_device_id: Optional[str] = None,
        weather_device_config: Optional[Dict] = None
    ) -> Dict[str, Optional[float]]:
        """
        Get weather data (irradiance, temperature, wind) for an asset with fallback support.
        
        Args:
            asset_code: Asset code (used to find weather station device_id if not provided)
            timestamp: Target timestamp (defaults to now)
            tolerance_minutes: Time window to search (default 15 minutes)
            weather_device_id: Optional specific weather device ID to use (deprecated, use weather_device_config)
            weather_device_config: Optional weather device configuration dict:
                {
                    'irradiance_devices': ['device1', 'device2'],  # Fallback order
                    'temperature_devices': ['device1', 'device2'],
                    'wind_devices': ['device1', 'device2']
                }
            
        Returns:
            Dictionary with 'irradiance', 'temperature', 'wind' values
            {
                'irradiance': 850.5,  # W/m²
                'temperature': 45.2,  # °C
                'module_temp': 48.5,  # °C (if available)
                'ambient_temp': 35.0,  # °C (if available)
                'wind_speed': 2.5  # m/s (if available)
            }
        """
        try:
            # Use current time if timestamp not provided
            if timestamp is None:
                timestamp = timezone.now()
            
            # Calculate time window
            start_time = timestamp - timedelta(minutes=tolerance_minutes)
            end_time = timestamp + timedelta(minutes=tolerance_minutes)
            
            # Use weather_device_config if provided, otherwise fallback to old method
            if weather_device_config:
                return self._get_weather_data_with_config(
                    weather_device_config, timestamp, start_time, end_time
                )
            
            # Legacy: Find weather device if not provided
            if weather_device_id is None:
                weather_device_id = self._find_weather_device(asset_code)
                if not weather_device_id:
                    logger.warning(
                        f"No weather device found for asset {asset_code}. "
                        f"Trying fallback search in timeseries_data..."
                    )
            
            # Get OEM tags for weather metrics
            irradiance_tag = self.metric_mapper.get_oem_tag(
                'weather', 'irradiance', self.mappings
            )
            temp_tag = self.metric_mapper.get_oem_tag(
                'weather', 'temperature', self.mappings
            )
            module_temp_tag = self.metric_mapper.get_oem_tag(
                'weather', 'module_temp', self.mappings
            )
            ambient_temp_tag = self.metric_mapper.get_oem_tag(
                'weather', 'ambient_temp', self.mappings
            )
            
            result = {
                'irradiance': None,
                'temperature': None,
                'module_temp': None,
                'ambient_temp': None
            }
            
            # Build device filter
            if weather_device_id:
                # Use specific weather device
                device_filter = Q(device_id=weather_device_id)
            else:
                # Fallback: search by asset_code and weather keywords
                device_filter = Q(device_id__icontains=asset_code) & (
                    Q(device_id__icontains='weather') | 
                    Q(device_id__icontains='meteo') |
                    Q(device_id__icontains='meteorological')
                )
            
            # Query for irradiance
            # Use oem_metric since irradiance_tag is the OEM tag (e.g., "gii")
            if irradiance_tag:
                irradiance_data = timeseries_data.objects.filter(
                    device_filter,
                    oem_metric=irradiance_tag,
                    ts__gte=start_time,
                    ts__lte=end_time
                ).order_by('-ts').first()
                
                if irradiance_data:
                    try:
                        result['irradiance'] = float(irradiance_data.value)
                    except (ValueError, TypeError):
                        pass
            
            # Query for temperature (module or ambient)
            # Use oem_metric since temp_tag is the OEM tag
            if temp_tag:
                temp_data = timeseries_data.objects.filter(
                    device_filter,
                    oem_metric=temp_tag,
                    ts__gte=start_time,
                    ts__lte=end_time
                ).order_by('-ts').first()
                
                if temp_data:
                    try:
                        result['temperature'] = float(temp_data.value)
                    except (ValueError, TypeError):
                        pass
            
            # Try module_temp if available
            # Use oem_metric since module_temp_tag is the OEM tag
            if module_temp_tag:
                module_temp_data = timeseries_data.objects.filter(
                    device_filter,
                    oem_metric=module_temp_tag,
                    ts__gte=start_time,
                    ts__lte=end_time
                ).order_by('-ts').first()
                
                if module_temp_data:
                    try:
                        result['module_temp'] = float(module_temp_data.value)
                    except (ValueError, TypeError):
                        pass
            
            # Try ambient_temp if available
            # Use oem_metric since ambient_temp_tag is the OEM tag
            if ambient_temp_tag:
                ambient_temp_data = timeseries_data.objects.filter(
                    device_filter,
                    oem_metric=ambient_temp_tag,
                    ts__gte=start_time,
                    ts__lte=end_time
                ).order_by('-ts').first()
                
                if ambient_temp_data:
                    try:
                        result['ambient_temp'] = float(ambient_temp_data.value)
                    except (ValueError, TypeError):
                        pass
            
            
            return result
            
        except Exception as e:
            logger.error(
                f"Error fetching weather data for {asset_code}: {e}",
                exc_info=True
            )
            return {
                'irradiance': None,
                'temperature': None,
                'module_temp': None,
                'ambient_temp': None,
                'wind_speed': None
            }
    
    def _get_weather_data_with_config(
        self,
        weather_device_config: Dict,
        timestamp: datetime,
        start_time: datetime,
        end_time: datetime
    ) -> Dict[str, Optional[float]]:
        """
        Get weather data using weather_device_config with fallback support.
        
        Args:
            weather_device_config: Dict with device lists for each metric type
            timestamp: Target timestamp
            start_time: Start of time window
            end_time: End of time window
            
        Returns:
            Dictionary with weather data values
        """
        result = {
            'irradiance': None,
            'temperature': None,
            'module_temp': None,
            'ambient_temp': None,
            'wind_speed': None
        }
        
        # Get OEM tags
        irradiance_tag = self.metric_mapper.get_oem_tag('weather', 'irradiance', self.mappings)
        temp_tag = self.metric_mapper.get_oem_tag('weather', 'temperature', self.mappings)
        module_temp_tag = self.metric_mapper.get_oem_tag('weather', 'module_temp', self.mappings)
        ambient_temp_tag = self.metric_mapper.get_oem_tag('weather', 'ambient_temp', self.mappings)
        wind_tag = self.metric_mapper.get_oem_tag('weather', 'wind_speed', self.mappings)
        
        # Get irradiance with fallback
        # Support both old format (device IDs) and new format (device+metric pairs)
        if weather_device_config.get('irradiance_devices'):
            irradiance_devices = weather_device_config['irradiance_devices']
            if isinstance(irradiance_devices, list) and len(irradiance_devices) > 0:
                # Check if new format (list of dicts with device_id and metric)
                if isinstance(irradiance_devices[0], dict):
                    result['irradiance'] = self._get_metric_with_fallback_new_format(
                        irradiance_devices,
                        start_time,
                        end_time
                    )
                else:
                    # Old format (list of device IDs) - use mapped metric tag
                    if irradiance_tag:
                        result['irradiance'] = self._get_metric_with_fallback(
                            irradiance_devices,
                            irradiance_tag,
                            start_time,
                            end_time
                        )
        
        # Get temperature with fallback
        # Support both old format (device IDs) and new format (device+metric pairs)
        if weather_device_config.get('temperature_devices'):
            temp_devices = weather_device_config['temperature_devices']
            if isinstance(temp_devices, list) and len(temp_devices) > 0:
                if isinstance(temp_devices[0], dict):
                    result['temperature'] = self._get_metric_with_fallback_new_format(
                        temp_devices,
                        start_time,
                        end_time
                    )
                else:
                    if temp_tag:
                        result['temperature'] = self._get_metric_with_fallback(
                            temp_devices,
                            temp_tag,
                            start_time,
                            end_time
                        )
        
        # Get module_temp with fallback
        if weather_device_config.get('temperature_devices'):
            temp_devices = weather_device_config['temperature_devices']
            if isinstance(temp_devices, list) and len(temp_devices) > 0:
                if isinstance(temp_devices[0], dict):
                    # For module_temp, we need to find a metric that represents module temperature
                    # This will be handled by the metric selection in the UI
                    result['module_temp'] = self._get_metric_with_fallback_new_format(
                        temp_devices,
                        start_time,
                        end_time
                    )
                else:
                    if module_temp_tag:
                        result['module_temp'] = self._get_metric_with_fallback(
                            temp_devices,
                            module_temp_tag,
                            start_time,
                            end_time
                        )
        
        # Get ambient_temp with fallback
        if weather_device_config.get('temperature_devices'):
            temp_devices = weather_device_config['temperature_devices']
            if isinstance(temp_devices, list) and len(temp_devices) > 0:
                if isinstance(temp_devices[0], dict):
                    result['ambient_temp'] = self._get_metric_with_fallback_new_format(
                        temp_devices,
                        start_time,
                        end_time
                    )
                else:
                    if ambient_temp_tag:
                        result['ambient_temp'] = self._get_metric_with_fallback(
                            temp_devices,
                            ambient_temp_tag,
                            start_time,
                            end_time
                        )
        
        # Get wind_speed with fallback
        if weather_device_config.get('wind_devices'):
            wind_devices = weather_device_config['wind_devices']
            if isinstance(wind_devices, list) and len(wind_devices) > 0:
                if isinstance(wind_devices[0], dict):
                    result['wind_speed'] = self._get_metric_with_fallback_new_format(
                        wind_devices,
                        start_time,
                        end_time
                    )
                else:
                    if wind_tag:
                        result['wind_speed'] = self._get_metric_with_fallback(
                            wind_devices,
                            wind_tag,
                            start_time,
                            end_time
                        )
        
        
        return result
    
    def _get_metric_with_fallback(
        self,
        device_ids: List[str],
        metric_tag: str,
        start_time: datetime,
        end_time: datetime
    ) -> Optional[float]:
        """
        Get metric value from multiple devices with fallback.
        
        Args:
            device_ids: List of device IDs to try in order
            metric_tag: OEM metric tag to search for
            start_time: Start of time window
            end_time: End of time window
            
        Returns:
            First available metric value or None
        """
        for device_id in device_ids:
            if not device_id:
                continue
            
            try:
                # Query by oem_metric since metric_tag is the OEM tag (e.g., "gii")
                # timeseries_data stores both 'metric' (standardized) and 'oem_metric' (original)
                data = timeseries_data.objects.filter(
                    device_id=device_id,
                    oem_metric=metric_tag,
                    ts__gte=start_time,
                    ts__lte=end_time
                ).order_by('-ts').first()
                
                if data:
                    try:
                        value = float(data.value)
                        return value
                    except (ValueError, TypeError):
                        continue
            except Exception as e:
                logger.warning(f"Error fetching {metric_tag} from {device_id}: {e}")
                continue
        
        return None
    
    def _get_metric_with_fallback_new_format(
        self,
        device_metrics: List[Dict],
        start_time: datetime,
        end_time: datetime
    ) -> Optional[float]:
        """
        Get metric value from multiple device+metric pairs with fallback.
        
        Args:
            device_metrics: List of dicts with 'device_id' and 'metric' keys
            start_time: Start of time window
            end_time: End of time window
            
        Returns:
            First available metric value or None
        """
        for device_metric in device_metrics:
            device_id = device_metric.get('device_id')
            metric_name = device_metric.get('metric')
            
            if not device_id or not metric_name:
                continue
            
            try:
                # Query timeseries_data using the metric field directly
                # The metric field from device_mapping is what's stored in timeseries_data.metric
                data = timeseries_data.objects.filter(
                    device_id=device_id,
                    metric=metric_name,  # Use metric field directly
                    ts__gte=start_time,
                    ts__lte=end_time
                ).order_by('-ts').first()
                
                if data:
                    try:
                        value = float(data.value)
                        return value
                    except (ValueError, TypeError):
                        continue
            except Exception as e:
                logger.warning(f"Error fetching {metric_name} from {device_id}: {e}")
                continue
        
        return None
    
    def _find_weather_device(self, asset_code: str) -> Optional[str]:
        """
        Find weather device ID for an asset by looking in device_list.
        
        Args:
            asset_code: Asset code
            
        Returns:
            Weather device ID or None if not found
        """
        try:
            from main.models import device_list
            
            # Look for weather devices under this asset
            # Try common weather device types
            weather_types = ['weather', 'meteo', 'meteorological', 'pyranometer', 'irradiance']
            
            for weather_type in weather_types:
                weather_devices = device_list.objects.filter(
                    parent_code=asset_code,
                    device_type__icontains=weather_type
                )
                
                if weather_devices.exists():
                    # Return first weather device found
                    return weather_devices.first().device_id
            
            # If not found by device_type, try by device_id pattern
            weather_devices = device_list.objects.filter(
                parent_code=asset_code
            ).filter(
                Q(device_id__icontains='weather') |
                Q(device_id__icontains='meteo') |
                Q(device_id__icontains='meteorological')
            )
            
            if weather_devices.exists():
                return weather_devices.first().device_id
            
            return None
            
        except Exception as e:
            logger.warning(f"Error finding weather device for {asset_code}: {e}")
            return None
    
    def get_latest_data(
        self,
        device_id: str,
        metric_names: List[str],
        device_type: Optional[str] = None,
        hours_back: int = 24
    ) -> Dict[str, Optional[float]]:
        """
        Get latest values for multiple metrics for a device.
        
        Args:
            device_id: Device ID
            metric_names: List of standardized metric names
            device_type: Device type
            hours_back: How many hours back to search
            
        Returns:
            Dictionary of {metric_name: value}
        """
        try:
            if device_type is None:
                device_type = self._detect_device_type(device_id)
            
            cutoff_time = timezone.now() - timedelta(hours=hours_back)
            
            result = {}
            for metric_name in metric_names:
                oem_tag = self.metric_mapper.get_oem_tag(
                    device_type, metric_name, self.mappings
                )
                
                if not oem_tag:
                    result[metric_name] = None
                    continue
                
                data = timeseries_data.objects.filter(
                    device_id=device_id,
                    metric=oem_tag,
                    ts__gte=cutoff_time
                ).order_by('-ts').first()
                
                if data:
                    try:
                        result[metric_name] = float(data.value)
                    except (ValueError, TypeError):
                        result[metric_name] = None
                else:
                    result[metric_name] = None
            
            return result
            
        except Exception as e:
            logger.error(
                f"Error fetching latest data for {device_id}: {e}",
                exc_info=True
            )
            return {metric: None for metric in metric_names}
    
    def _detect_device_type(self, device_id: str) -> str:
        """Auto-detect device type from device_id."""
        device_id_lower = device_id.lower()
        
        if 'string' in device_id_lower:
            return 'string'
        elif 'jb' in device_id_lower or 'junction' in device_id_lower:
            return 'jb'
        elif 'inv' in device_id_lower or 'inverter' in device_id_lower:
            return 'inverter'
        elif 'weather' in device_id_lower or 'meteo' in device_id_lower:
            return 'weather'
        else:
            return 'string'  # Default

