"""
Stub adapter: no-op for pipeline testing. Registers as 'stub'.

Used until real adapters (OEM, SolarGIS) are implemented. Logs and returns success
so the full path task → resolve adapter → call adapter works.
"""
import logging
from typing import Any, Dict

from data_collection.adapters import register

logger = logging.getLogger(__name__)


@register("stub")
def stub_fetch_and_store(asset_code: str, config: Dict[str, Any]) -> Dict[str, Any]:
    """
    Stub adapter: no real fetch or DB write. Returns success for pipeline testing.
    """
    logger.debug("Stub adapter run for asset_code=%s (config keys: %s)", asset_code, list(config.keys()))
    return {"success": True, "adapter": "stub", "asset_code": asset_code}
