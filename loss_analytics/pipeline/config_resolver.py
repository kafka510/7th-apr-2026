"""
Resolve device and asset config for loss analytics from main.models.

Returns only devices that are configured for loss and have loss_calculation_enabled
True or null (excluded when False).
"""
from typing import List, Optional, Dict, Any

from django.db.models import Q


def get_configured_string_devices_for_asset(asset_code: str):
    """
    Return QuerySet of string devices for the asset that are configured for loss
    (module_datasheet_id, modules_in_series set) and enabled (loss_calculation_enabled
    True or null). Excludes devices with loss_calculation_enabled=False.
    """
    from main.models import device_list, get_configured_loss_string_devices_for_asset
    return get_configured_loss_string_devices_for_asset(asset_code)


def get_configured_inverter_devices_for_asset(asset_code: str):
    """
    Return QuerySet of inverter devices for the asset that have
    loss_calculation_enabled True or null. Matches main logic: device_type contains '_inv'.
    """
    from main.models import device_list
    return device_list.objects.filter(
        parent_code=asset_code,
        device_type__icontains="_inv",
    ).filter(
        Q(loss_calculation_enabled__isnull=True) | Q(loss_calculation_enabled=True)
    )


def get_asset(asset_code: str):
    """Return AssetList instance or None."""
    from main.models import AssetList
    try:
        return AssetList.objects.get(asset_code=asset_code)
    except AssetList.DoesNotExist:
        return None


def get_asset_tilt_configs(asset_code: str) -> List[Dict[str, Any]]:
    """Return tilt_configs list for the asset; empty list if not set."""
    asset = get_asset(asset_code)
    if not asset:
        return []
    tilt_configs = getattr(asset, "tilt_configs", None)
    if not tilt_configs or not isinstance(tilt_configs, list):
        return []
    return tilt_configs
