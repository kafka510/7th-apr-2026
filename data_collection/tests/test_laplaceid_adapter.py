from __future__ import annotations

from datetime import timezone as dt_timezone


def test_split_header_device_code_and_oem_tag():
    from data_collection.adapters.laplaceid import _split_header

    assert _split_header("3 acEnergy") == ("3", "acEnergy")
    assert _split_header("  10   日射量(kWh/m2)  ") == ("10", "日射量(kWh/m2)")
    assert _split_header("日射量(kWh/m2)") == (None, "日射量(kWh/m2)")


def test_parse_provider_datetime_naive_attaches_default_tz():
    from data_collection.adapters.laplaceid import _parse_provider_datetime

    dt = _parse_provider_datetime("2026/03/18 18:24", dt_timezone.utc)
    assert dt is not None
    assert dt.tzinfo is not None
    assert dt.isoformat().startswith("2026-03-18T18:24")

