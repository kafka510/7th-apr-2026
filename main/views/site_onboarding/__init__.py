"""Site onboarding views split by adapter / data-collection concern.

Re-exported from ``main.views`` next to ``site_onboarding_views`` so existing
``views.api_*`` URL bindings stay valid.

To add a new OEM adapter: add ``main/views/site_onboarding/<adapter>.py`` and
import its view callables here (and in ``__all__``).
"""
from .adapter_raw_samples import api_adapter_fetch_raw_samples
from .adapter_config import (
    api_adapter_account_list,
    api_asset_adapter_config_data,
    api_create_adapter_account,
    api_create_asset_adapter_config,
    api_data_collection_adapter_ids,
    api_delete_adapter_account,
    api_delete_asset_adapter_config,
    api_update_adapter_account,
    api_update_asset_adapter_config,
)
from .fusion_solar import (
    api_fusion_solar_asset_csv,
    api_fusion_solar_device_csv,
    api_fusion_solar_fetch_devices,
    api_fusion_solar_fetch_plants,
)
from .laplaceid import (
    api_laplaceid_discover_devices_from_csv,
    api_laplaceid_fetch_devices_for_assets,
    api_laplaceid_fetch_nodes,
    api_laplaceid_test_connection,
)
from .masking import _mask_adapter_config, _mask_api_key

__all__ = [
    "_mask_adapter_config",
    "_mask_api_key",
    "api_adapter_fetch_raw_samples",
    "api_adapter_account_list",
    "api_asset_adapter_config_data",
    "api_create_adapter_account",
    "api_create_asset_adapter_config",
    "api_data_collection_adapter_ids",
    "api_delete_adapter_account",
    "api_delete_asset_adapter_config",
    "api_fusion_solar_asset_csv",
    "api_fusion_solar_device_csv",
    "api_fusion_solar_fetch_devices",
    "api_fusion_solar_fetch_plants",
    "api_laplaceid_discover_devices_from_csv",
    "api_laplaceid_fetch_devices_for_assets",
    "api_laplaceid_fetch_nodes",
    "api_laplaceid_test_connection",
    "api_update_adapter_account",
    "api_update_asset_adapter_config",
]
