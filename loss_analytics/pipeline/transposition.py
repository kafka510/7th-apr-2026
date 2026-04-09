"""
GHI to GII (Global Horizontal Irradiance to Global Inclined Irradiance) transposition.

Lives in loss_analytics per plan; used by transpose task and can be called from
data acquisition. Full model: solar position, extraterrestrial, clearness index
(Erbs diffuse/beam split), angle of incidence, Hay-Davies diffuse transposition,
beam on tilt, ground reflection.

Azimuth convention: 0 = south, east negative, west positive (degrees).
Tilt: 0 = horizontal (degrees).
"""
from __future__ import annotations

import math
from datetime import datetime, tzinfo
from typing import Optional

# Solar constant W/m²
G_SC = 1367.0

# Sea-level atmospheric pressure (Pa) for altitude correction
P0_PA = 101325.0

# Minimum solar elevation (degrees) to trust the transposition model.
MIN_SUN_ELEV_DEG = 3.0


def gii_device_id(asset_code: str, tilt_deg: float, azimuth_deg: float) -> str:
    """
    Synthetic device_id for storing GII in timeseries_data.
    Format: {asset_code}_gii_{tilt}_{azimuth}
    """
    tilt_str = _format_angle(tilt_deg)
    az_str = _format_angle(azimuth_deg)
    return f"{asset_code}_gii_{tilt_str}_{az_str}"


def _format_angle(deg: float) -> str:
    """Format angle for device_id; use 'n' prefix for negative to avoid minus in ID."""
    if deg < 0:
        return f"n{abs(int(round(deg)))}"
    return str(int(round(deg)))


def _relative_pressure(altitude_m: float) -> float:
    """Relative pressure P/P0 from barometric formula (ISO 2533–like)."""
    h = max(0.0, min(15000.0, float(altitude_m)))
    return (1.0 - 2.25577e-5 * h) ** 5.25588


def ghi_to_gii(
    ghi: float,
    dt: datetime,
    lat_deg: float,
    lon_deg: float,
    tilt_deg: float,
    azimuth_deg: float,
    altitude_m: float = 0.0,
    rho: float = 0.2,
    local_tz: Optional[tzinfo] = None,
) -> float:
    """
    Transpose GHI (W/m²) to GII (W/m²) for a tilted plane.

    Args:
        ghi: Global horizontal irradiance (W/m²).
        dt: Timestamp (timezone-aware; UTC recommended).
        lat_deg, lon_deg: Latitude/longitude (degrees).
        tilt_deg: Tilt angle (degrees, 0 = horizontal).
        azimuth_deg: Azimuth (degrees, 0 = south, east negative, west positive).
        altitude_m: Site altitude (m). Default 0.
        rho: Ground albedo (0–1). Default 0.2.
        local_tz: Optional timezone for the asset.

    Returns:
        GII in W/m². Returns 0 if sun below horizon or invalid; passes through
        horizontal value when solar elevation is below MIN_SUN_ELEV_DEG.
    """
    if ghi is None or (isinstance(ghi, float) and (ghi < 0 or math.isnan(ghi))):
        return 0.0
    ghi = float(ghi)

    dt_work = dt
    tz_offset_hours = 0.0
    if local_tz is not None:
        dt_work = dt.astimezone(local_tz)
        if dt_work.utcoffset() is not None:
            tz_offset_hours = dt_work.utcoffset().total_seconds() / 3600.0

    phi = math.radians(lat_deg)
    n = _day_of_year(dt_work)
    delta_rad = math.radians(23.45 * math.sin(math.radians(360.0 / 365.0 * (284 + n))))

    hour = dt_work.hour + dt_work.minute / 60.0 + dt_work.second / 3600.0
    solar_time_h = hour + (lon_deg / 15.0 - tz_offset_hours)
    omega_deg = 15.0 * (solar_time_h - 12.0)
    omega = math.radians(omega_deg)

    cos_theta_z = (
        math.sin(phi) * math.sin(delta_rad)
        + math.cos(phi) * math.cos(delta_rad) * math.cos(omega)
    )
    if cos_theta_z <= 0:
        return 0.0
    cos_theta_z = min(1.0, cos_theta_z)

    elev_deg = 90.0 - math.degrees(math.acos(cos_theta_z))
    if elev_deg < MIN_SUN_ELEV_DEG:
        return ghi

    e0 = 1.0 + 0.033 * math.cos(math.radians(360.0 * n / 365.0))
    g0h = G_SC * e0 * cos_theta_z
    if g0h <= 0:
        return 0.0

    kt = ghi / g0h
    kt = max(0.0, min(1.2, kt))

    if kt <= 0.22:
        kd = 1.0 - 0.09 * kt
    elif kt <= 0.8:
        kd = (
            0.9511
            - 0.1604 * kt
            + 4.388 * kt**2
            - 16.638 * kt**3
            + 12.336 * kt**4
        )
    else:
        kd = 0.165

    dhi = kd * ghi
    dni = (ghi - dhi) / cos_theta_z if cos_theta_z > 1e-10 else 0.0
    dni = max(0.0, dni)

    p_ratio = _relative_pressure(altitude_m)
    if p_ratio > 1e-10:
        dni = dni * (1.0 / p_ratio) ** 0.7

    beta = math.radians(tilt_deg)
    gamma = math.radians(azimuth_deg)
    cos_theta_i = (
        math.sin(delta_rad) * math.sin(phi) * math.cos(beta)
        - math.sin(delta_rad) * math.cos(phi) * math.sin(beta) * math.cos(gamma)
        + math.cos(delta_rad) * math.cos(phi) * math.cos(omega) * math.cos(beta)
        + math.cos(delta_rad) * math.sin(phi) * math.cos(omega) * math.sin(beta) * math.cos(gamma)
        + math.cos(delta_rad) * math.sin(omega) * math.sin(beta) * math.sin(gamma)
    )
    cos_theta_i = max(0.0, cos_theta_i)

    a = dni / (G_SC * e0) if (G_SC * e0) > 1e-10 else 0.0
    a = min(1.0, max(0.0, a))
    rb = cos_theta_i / cos_theta_z if cos_theta_z > 1e-10 else 0.0
    d_tilt = dhi * (a * rb + (1.0 - a) * (1.0 + math.cos(beta)) / 2.0)
    b_tilt = dni * cos_theta_i
    r_tilt = rho * ghi * (1.0 - math.cos(beta)) / 2.0
    gii = b_tilt + d_tilt + r_tilt
    return max(0.0, gii)


def _day_of_year(dt: datetime) -> int:
    """Day of year 1–366."""
    start = datetime(dt.year, 1, 1, tzinfo=dt.tzinfo)
    return (dt - start).days + 1
