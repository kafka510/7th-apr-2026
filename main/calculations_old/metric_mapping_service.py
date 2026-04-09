"""
Metric Mapping Service

Reads metric configuration from device_mapping table where asset_code='loss_metrics'.
This allows flexible configuration of metric names for loss calculations.
"""
from typing import Dict, Optional, List
import logging
from django.core.cache import cache
from main.models import device_mapping

logger = logging.getLogger(__name__)

# Cache key for metric mappings
METRIC_MAPPING_CACHE_KEY = 'loss_metrics_mapping'
CACHE_TIMEOUT = 3600  # 1 hour


class MetricMappingService:
    """
    Service to read and cache metric mappings from device_mapping table.
    
    Expected structure in device_mapping:
    - asset_code = 'loss_metrics'
    - device_type = 'string', 'jb', 'inverter', 'weather', etc.
    - metric = standardized metric name (e.g., 'string_actual_power')
    - oem_tag = original metric name in timeseries_data (e.g., 'active_power')
    - units = unit of measurement (e.g., 'W', 'W/m²', '°C')
    """
    
    @staticmethod
    def get_metric_mappings(force_refresh: bool = False) -> Dict[str, Dict]:
        """
        Get all metric mappings from device_mapping table.
        
        Returns a nested dictionary:
        {
            'string': {
                'actual_power': {
                    'metric': 'string_actual_power',
                    'oem_tag': 'active_power',
                    'units': 'W',
                    'device_type': 'string'
                },
                'expected_power': {...},
                'irradiance': {...},
                ...
            },
            'jb': {...},
            'inverter': {...},
            'weather': {...}
        }
        
        Args:
            force_refresh: If True, bypass cache and reload from database
            
        Returns:
            Dictionary of metric mappings organized by device_type
        """
        # Check cache first, handle Redis connection errors gracefully
        if not force_refresh:
            try:
                cached = cache.get(METRIC_MAPPING_CACHE_KEY)
                if cached is not None:
                    return cached
            except Exception:
                # If cache is unavailable (e.g., Redis connection error), continue to load from database
                logger.warning("Cache unavailable for metric mappings, loading from database")
        
        # Load from database
        try:
            total_mappings = device_mapping.objects.filter(asset_code='loss_metrics').count()
            
            if total_mappings == 0:
                # Check if there are any rows with similar asset_code
                sample_asset_codes = device_mapping.objects.values_list('asset_code', flat=True).distinct()[:10]
                logger.warning(f"No mappings found with asset_code='loss_metrics'. Sample asset_codes in table: {list(sample_asset_codes)}")
            
            mappings = device_mapping.objects.filter(
                asset_code='loss_metrics'
            ).values(
                'device_type', 'metric', 'oem_tag', 'units', 'discription'
            )
            
            result = {}
            mapping_count = 0
            for mapping in mappings:
                mapping_count += 1
                device_type = mapping.get('device_type')
                metric = mapping.get('metric')
                oem_tag = mapping.get('oem_tag')
                
                # Skip if essential fields are missing
                if not device_type or not metric:
                    logger.warning(f"Skipping mapping with missing device_type or metric: {mapping}")
                    continue
                
                device_type = device_type.lower()
                
                # Organize by device_type
                if device_type not in result:
                    result[device_type] = {}
                
                # Use metric as key, store full mapping info
                result[device_type][metric] = {
                    'metric': metric,
                    'oem_tag': oem_tag,
                    'units': mapping.get('units', ''),
                    'description': mapping.get('discription', ''),
                    'device_type': device_type
                }
            
            # Cache the result, handle Redis connection errors gracefully
            try:
                cache.set(METRIC_MAPPING_CACHE_KEY, result, CACHE_TIMEOUT)
            except Exception:
                # If cache set fails, continue without caching
                logger.warning("Failed to cache metric mappings, continuing without cache")
            
            return result
            
        except Exception as e:
            logger.error(f"Error loading metric mappings from device_mapping: {e}", exc_info=True)
            # Return empty dict on error
            return {}
    
    @staticmethod
    def get_metric_for_device_type(
        device_type: str,
        metric_name: str,
        mappings: Optional[Dict] = None
    ) -> Optional[Dict]:
        """
        Get metric mapping for a specific device type and metric name.
        
        Args:
            device_type: Device type ('string', 'jb', 'inverter', 'weather')
            metric_name: Metric name (e.g., 'actual_power', 'expected_power', 'irradiance')
            mappings: Optional pre-loaded mappings dict (to avoid re-fetching)
            
        Returns:
            Dictionary with metric info, or None if not found
            {
                'metric': 'string_actual_power',
                'oem_tag': 'active_power',
                'units': 'W',
                'description': '...'
            }
        """
        if mappings is None:
            mappings = MetricMappingService.get_metric_mappings()
        
        device_type = device_type.lower()
        if device_type not in mappings:
            logger.debug(f"No mappings found for device_type: {device_type}")
            return None
        
        device_mappings = mappings[device_type]
        
        # Try exact match first
        if metric_name in device_mappings:
            return device_mappings[metric_name]
        
        # Try case-insensitive search
        for key, value in device_mappings.items():
            if key.lower() == metric_name.lower():
                return value
        
        logger.debug(
            f"Metric '{metric_name}' not found for device_type '{device_type}'. "
            f"Available: {list(device_mappings.keys())}"
        )
        return None
    
    @staticmethod
    def get_oem_tag(
        device_type: str,
        metric_name: str,
        mappings: Optional[Dict] = None
    ) -> Optional[str]:
        """
        Get the OEM tag (original metric name) for a standardized metric.
        
        This is the metric name used in timeseries_data table.
        
        Args:
            device_type: Device type ('string', 'jb', 'inverter', 'weather')
            metric_name: Standardized metric name (e.g., 'actual_power')
            mappings: Optional pre-loaded mappings dict
            
        Returns:
            OEM tag string (e.g., 'active_power'), or None if not found
        """
        mapping = MetricMappingService.get_metric_for_device_type(
            device_type, metric_name, mappings
        )
        return mapping.get('oem_tag') if mapping else None
    
    @staticmethod
    def get_standardized_metric(
        device_type: str,
        oem_tag: str,
        mappings: Optional[Dict] = None
    ) -> Optional[str]:
        """
        Get standardized metric name from OEM tag (reverse lookup).
        
        Args:
            device_type: Device type ('string', 'jb', 'inverter', 'weather')
            oem_tag: Original metric name from timeseries_data
            mappings: Optional pre-loaded mappings dict
            
        Returns:
            Standardized metric name, or None if not found
        """
        if mappings is None:
            mappings = MetricMappingService.get_metric_mappings()
        
        device_type = device_type.lower()
        if device_type not in mappings:
            return None
        
        device_mappings = mappings[device_type]
        
        # Search for matching oem_tag
        for metric_name, mapping_info in device_mappings.items():
            if mapping_info.get('oem_tag', '').lower() == oem_tag.lower():
                return metric_name
        
        return None
    
    @staticmethod
    def list_available_metrics(device_type: Optional[str] = None) -> Dict[str, List[str]]:
        """
        List all available metrics for device types.
        
        Args:
            device_type: Optional filter for specific device type
            
        Returns:
            Dictionary mapping device_type to list of metric names
            {
                'string': ['actual_power', 'expected_power', 'irradiance', ...],
                'jb': [...],
                ...
            }
        """
        mappings = MetricMappingService.get_metric_mappings()
        
        if device_type:
            device_type = device_type.lower()
            if device_type in mappings:
                return {device_type: list(mappings[device_type].keys())}
            return {}
        
        return {
            dt: list(metrics.keys())
            for dt, metrics in mappings.items()
        }
    
    @staticmethod
    def clear_cache():
        """Clear the metric mapping cache (useful after updating device_mapping)"""
        try:
            cache.delete(METRIC_MAPPING_CACHE_KEY)
        except Exception:
            # If cache delete fails, log warning but don't raise error
            logger.warning("Failed to clear metric mapping cache")
    
    @staticmethod
    def validate_mappings() -> Dict[str, List[str]]:
        """
        Validate that required metrics are configured.
        
        Returns:
            Dictionary with 'missing' and 'present' keys listing required metrics
        """
        mappings = MetricMappingService.get_metric_mappings()
        
        # Required metrics for loss calculations
        required = {
            'string': ['actual_power', 'expected_power'],
            'weather': ['irradiance', 'temperature']
        }
        
        missing = {}
        present = {}
        
        for device_type, metrics in required.items():
            missing[device_type] = []
            present[device_type] = []
            
            if device_type not in mappings:
                missing[device_type] = metrics
                continue
            
            device_mappings = mappings[device_type]
            for metric in metrics:
                if metric in device_mappings:
                    present[device_type].append(metric)
                else:
                    missing[device_type].append(metric)
        
        return {
            'missing': missing,
            'present': present
        }

