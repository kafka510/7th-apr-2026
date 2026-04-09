"""
Base contract for adapters (optional).

Adapters are callables(asset_code, config) -> {success, error?, ...}.
They are invoked by acquisition tasks; they fetch data from the asset/source
and write to the database (e.g. timeseries_data). This module documents
the interface; concrete adapters can be plain functions registered in adapters/__init__.py.

Write policy (5/30-min adapters only):
  For 5-min and 30-min acquisition, use the solar-window write policy so we write
  all readings during the day and only changed readings at night. Before writing
  a reading, call data_collection.services.write_policy.should_write_reading()
  (asset_code, adapter_id, current_value, interval_minutes=config.get("acquisition_interval_minutes", 5),
  series_key="default" or metric name). If it returns (True, reason), write to DB
  and then call write_policy.record_written_reading(). If (False, "outside_unchanged"),
  skip the write but still return success. Daily adapters (e.g. Solargis) do not
  use write policy; they write all fetched data.
"""
from typing import Any, Dict


def fetch_and_store(asset_code: str, config: Dict[str, Any]) -> Dict[str, Any]:
    """
    Fetch data from the asset/source and write to DB.

    Override in concrete adapters. Called by data_collection.services.acquisition_runner.
    config includes acquisition_interval_minutes (5, 30, or 1440) injected by the runner.

    Args:
        asset_code: Asset/site code (e.g. from asset_list.asset_code).
        config: Adapter-specific options (API URL, credentials, etc.), plus
                acquisition_interval_minutes when invoked by the runner.

    Returns:
        Dict with at least:
        - success (bool): True if fetch and write succeeded.
        - error (str, optional): Message if success is False.
        Adapters may add more keys (e.g. points_written, duration_seconds).
        Optionally: written=False, write_reason="outside_unchanged" when a read was skipped by write policy.
    """
    raise NotImplementedError("Subclass or register a concrete adapter")
