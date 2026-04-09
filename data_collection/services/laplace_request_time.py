"""
Laplace CSV ``time=`` query parameter (wall-clock in site offset).

asset_list.timezone is a fixed offset like ``+09:00`` / ``-05:00`` (see AssetList validator).
For ``hourly.php`` with ``unit=minute``, we send ``YYYYMMDDHH`` for the **previous full local hour**
relative to current UTC (Django ``timezone.now()``), unless the client passes an explicit ``time``.
"""
from __future__ import annotations

import re
from datetime import timedelta, timezone as dt_timezone
from typing import Optional

from django.utils import timezone as dj_tz

_OFFSET_RE = re.compile(r"^([+-])(\d{2}):(\d{2})$")


def fixed_timezone_from_asset_offset(tz_str: Optional[str]):
    """Return a :class:`datetime.timezone` for ``asset_list.timezone``, or ``None`` if invalid/empty."""
    if not tz_str or not str(tz_str).strip():
        return None
    m = _OFFSET_RE.match(str(tz_str).strip())
    if not m:
        return None
    sign = 1 if m.group(1) == "+" else -1
    h = int(m.group(2))
    mi = int(m.group(3))
    delta = timedelta(hours=sign * h, minutes=sign * mi)
    return dt_timezone(delta)


def laplace_time_yyyymmddhh_previous_local_hour(*, asset_timezone_offset: Optional[str] = None) -> str:
    """
    Previous full clock hour in the asset's offset (or UTC if missing/invalid), as ``YYYYMMDDHH``.
    """
    now = dj_tz.now()
    if now.tzinfo is None:
        now = dj_tz.make_aware(now, dt_timezone.utc)
    tz = fixed_timezone_from_asset_offset(asset_timezone_offset) or dt_timezone.utc
    local = now.astimezone(tz)
    prev = local - timedelta(hours=1)
    return prev.strftime("%Y%m%d%H")
