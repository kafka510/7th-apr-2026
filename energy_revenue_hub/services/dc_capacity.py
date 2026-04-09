"""
DC capacity weights for utility export split (see BILLING plan §3.2 / §9.3).

Authoritative: sum of ``device_list.dc_cap`` for rows with ``parent_code`` = asset.
If there are no devices under the asset, fall back to ``asset_list.capacity`` as a site-level weight.
"""

from __future__ import annotations

from decimal import Decimal
from typing import Optional, Tuple

from main.models import AssetList, device_list


def resolve_dc_capacity_kw(asset_code: str) -> Tuple[Optional[Decimal], Optional[str]]:
    """
    Returns (capacity_kw, error_message). Error means billing must not proceed with DC-weighted split.
    """
    devices = list(device_list.objects.filter(parent_code=asset_code))
    if devices:
        caps: list[Decimal] = []
        missing_dc = False
        for d in devices:
            if d.dc_cap is None:
                missing_dc = True
                continue
            try:
                cap = Decimal(str(d.dc_cap))
            except Exception:
                missing_dc = True
                continue
            if cap > 0:
                caps.append(cap)
            else:
                missing_dc = True

        if caps and not missing_dc:
            return sum(caps), None

        # Some device rows are missing dc_cap; fall back to site-level capacity if available.
        try:
            site = AssetList.objects.get(pk=asset_code)
            if site.capacity is not None and site.capacity > 0:
                return Decimal(str(site.capacity)), None
        except AssetList.DoesNotExist:
            pass

        return None, (
            f"No DC capacity available in the asset list for {asset_code}. "
            "Cannot compute billing split for this utility invoice."
        )
    try:
        site = AssetList.objects.get(pk=asset_code)
        if site.capacity is not None and site.capacity > 0:
            return Decimal(str(site.capacity)), None
    except AssetList.DoesNotExist:
        pass
    return None, (
        f"No DC capacity available in the asset list for {asset_code}. "
        "Cannot compute billing split for this utility invoice."
    )
