"""
Satellite irradiance device_id resolution for linked assets.

When an asset uses satellite irradiance from another nearby site (stored in
asset_list.satellite_irradiance_source_asset_code), this helper returns the
correct device_id to query timeseries_data.
"""
import logging
from typing import Optional

logger = logging.getLogger(__name__)

SATELLITE_DEVICE_SUFFIX = "_sat"


def get_satellite_irradiance_device_id(asset_code: str) -> Optional[str]:
    """
    Return the device_id to use for querying satellite irradiance (GHI, GTI, etc.) for an asset.

    - If asset_list.satellite_irradiance_source_asset_code is set, use that asset's _sat device.
    - Otherwise use {asset_code}_sat.

    Returns None if the asset does not exist in asset_list.
    """
    from main.models import AssetList

    try:
        asset = AssetList.objects.get(asset_code=asset_code)
    except AssetList.DoesNotExist:
        logger.warning("get_satellite_irradiance_device_id: asset_code=%s not found in asset_list", asset_code)
        return None

    source = getattr(asset, "satellite_irradiance_source_asset_code", None)
    if source and str(source).strip():
        return f"{str(source).strip()}{SATELLITE_DEVICE_SUFFIX}"
    return f"{asset_code}{SATELLITE_DEVICE_SUFFIX}"
