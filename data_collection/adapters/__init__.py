"""
Adapter registry: adapter_id → callable(asset_code, config) that fetches data and writes to DB.

Multiple sites can use the same adapter with different config. Adapters are invoked
by Celery data-acquisition tasks (run by workers). Register adapters here; use
get_adapter(adapter_id) to resolve and invoke.
"""
import logging
from typing import Any, Callable, Dict, Optional

logger = logging.getLogger(__name__)

# Type: (asset_code: str, config: dict) -> dict with at least 'success': bool, optional 'error': str
AdapterCallable = Callable[[str, Dict[str, Any]], Dict[str, Any]]

_REGISTRY: Dict[str, AdapterCallable] = {}


def register(adapter_id: str) -> Callable[[AdapterCallable], AdapterCallable]:
    """Decorator to register an adapter callable under adapter_id."""

    def _register(fn: AdapterCallable) -> AdapterCallable:
        if adapter_id in _REGISTRY:
            logger.warning("Overwriting existing adapter_id=%s", adapter_id)
        _REGISTRY[adapter_id] = fn
        return fn

    return _register


def get_adapter(adapter_id: str) -> Optional[AdapterCallable]:
    """Return the callable for adapter_id, or None if not registered."""
    return _REGISTRY.get(adapter_id)


def get_registered_ids() -> list:
    """Return list of registered adapter IDs (for admin/UI)."""
    return list(_REGISTRY.keys())


def fetch_and_store(asset_code: str, adapter_id: str, config: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Resolve adapter by adapter_id and run fetch_and_store for the given asset.

    Returns dict with at least 'success' (bool) and optionally 'error' (str), plus
    adapter-specific keys (e.g. 'points_written').
    """
    adapter = get_adapter(adapter_id)
    if adapter is None:
        return {"success": False, "error": f"Unknown adapter_id: {adapter_id}"}
    config = config or {}
    try:
        return adapter(asset_code, config)
    except Exception as e:
        logger.exception("Adapter %s failed for asset %s", adapter_id, asset_code)
        return {"success": False, "error": str(e)}


# Import adapters so they register themselves
from data_collection.adapters import stub  # noqa: E402, F401
from data_collection.adapters import solargis  # noqa: E402, F401
from data_collection.adapters import fusion_solar  # noqa: E402, F401
from data_collection.adapters import laplaceid  # noqa: E402, F401
