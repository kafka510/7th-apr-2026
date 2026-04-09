"""
Stub SolarGIS adapter: no-op for pipeline testing. Registers as 'solargis'.

Used until real SolarGIS API integration in Phase 7. Daily ingest task
invokes this for assets configured with adapter_id='solargis'.
"""
import logging
from typing import Any, Dict

from data_collection.adapters import register

logger = logging.getLogger(__name__)


@register("solargis")
def solargis_fetch_and_store(asset_code: str, config: Dict[str, Any]) -> Dict[str, Any]:
    """
    Stub SolarGIS adapter: no real API call or DB write. Returns success for pipeline testing.
    """
    logger.debug("SolarGIS stub adapter run for asset_code=%s", asset_code)
    return {"success": True, "adapter": "solargis", "asset_code": asset_code}
