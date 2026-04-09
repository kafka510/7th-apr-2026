"""
Grid Connectivity Analysis for Solar Pre-Feasibility (Engineering Tools).

Analyzes proximity to transmission lines and substations, extracts voltage/capacity,
and evaluates feasibility of connecting a solar plant to the grid.
Uses grid network KMZ files from engineering_tools/grid_network/{country}/ (e.g. japan, korea, singapore).
"""

import re
from pathlib import Path
from typing import Any

import geopandas as gpd
from shapely.geometry import Point
from shapely.ops import nearest_points


class GridNetworkFileNotFoundError(Exception):
    """Raised when the grid network KMZ file is not found for the given country/region."""

    pass


class GridConnectivityError(Exception):
    """Base exception for grid connectivity analysis failures."""

    pass


_VOLTAGE_RE = re.compile(r"(\d+(?:\.\d+)?)\s*kV", re.IGNORECASE)
_CAPACITY_MW_RE = re.compile(r"(\d+(?:\.\d+)?)\s*MW", re.IGNORECASE)


def _get_utm_epsg(site_lon: float, site_lat: float) -> int:
    """Compute UTM EPSG code for the site location (global safe)."""
    zone = int((site_lon + 180) / 6) + 1
    return 32600 + zone if site_lat >= 0 else 32700 + zone


def _search_attrs_for_value(attrs: dict, regex: re.Pattern) -> float | None:
    """Search all string attributes for a numeric match and return the first found."""
    for val in attrs.values():
        if val is None:
            continue
        s = str(val).strip()
        if not s:
            continue
        m = regex.search(s)
        if m:
            try:
                return float(m.group(1))
            except (ValueError, TypeError):
                continue
    return None


def _gather_string_attrs(row: gpd.GeoSeries) -> dict:
    """Gather all string-like attributes from a GeoDataFrame row for regex search."""
    attrs = {}
    for col in row.index:
        if col == "geometry":
            continue
        v = row[col]
        if v is not None and isinstance(v, (str, int, float)):
            attrs[col] = str(v)
    return attrs


def _resolve_kmz_path(data_root: Path, country: str, region: str | None) -> Path:
    """
    Resolve grid network KMZ path. Supports:
    - Region-specific: {country}/{region}.kmz
    - Country-wide single file: {country}/{country}.kmz
    - Fallback: first .kmz file in country folder (for files like "TL Line Network Japan.kmz")
    """
    country_clean = country.lower().strip().replace(" ", "_")
    country_dir = data_root / country_clean
    if not country_dir.exists() or not country_dir.is_dir():
        raise GridNetworkFileNotFoundError(
            f"Grid network folder not found: {country_dir}. "
            f"Expected: engineering_tools/grid_network/{country_clean}/"
        )

    candidates = []
    if region:
        region_clean = region.lower().strip().replace(" ", "_")
        candidates.append(country_dir / f"{region_clean}.kmz")
    candidates.append(country_dir / f"{country_clean}.kmz")

    for p in candidates:
        if p.exists():
            return p

    kmz_files = list(country_dir.glob("*.kmz"))
    if kmz_files:
        return kmz_files[0]

    raise GridNetworkFileNotFoundError(
        f"No .kmz file found in {country_dir}. "
        f"Place grid network file (e.g. japan.kmz or TL Line Network Japan.kmz) in engineering_tools/grid_network/{country_clean}/"
    )


def _load_grid_geometries(
    data_root: Path, country: str, region: str | None
) -> tuple[Path, gpd.GeoDataFrame, gpd.GeoDataFrame]:
    """
    Load transmission lines and substations from grid network KMZ.
    Returns (kmz_path, transmission_lines_gdf, substations_gdf).
    """
    kmz_path = _resolve_kmz_path(data_root, country, region)

    try:
        import pyogrio

        layer_list = pyogrio.list_layers(str(kmz_path))
        layer_indices = list(range(min(len(layer_list), 50)))
    except ImportError:
        layer_indices = [0]

    if not layer_indices:
        raise GridConnectivityError("No layers found in grid network file")

    all_lines: list[dict[str, Any]] = []
    all_points: list[dict[str, Any]] = []
    crs = None

    for layer_idx in layer_indices:
        try:
            gdf = gpd.read_file(kmz_path, layer=layer_idx)
        except Exception:
            continue

        if gdf.empty or gdf.geometry is None:
            continue

        if gdf.crs is None:
            gdf = gdf.set_crs(epsg=4326)
        crs = gdf.crs

        for idx, row in gdf.iterrows():
            geom = row.geometry
            if geom is None or geom.is_empty:
                continue
            attrs = {k: v for k, v in row.items() if k != "geometry"}

            if geom.geom_type in ("LineString", "LinearRing"):
                all_lines.append({**attrs, "geometry": geom})
            elif geom.geom_type == "MultiLineString":
                for line in geom.geoms:
                    all_lines.append({**attrs, "geometry": line})
            elif geom.geom_type == "Point":
                all_points.append({**attrs, "geometry": geom})
            elif geom.geom_type == "MultiPoint":
                for pt in geom.geoms:
                    all_points.append({**attrs, "geometry": pt})

    if not all_lines:
        raise GridConnectivityError("No transmission lines found in grid network file")

    lines_gdf = gpd.GeoDataFrame(all_lines, crs=crs or "EPSG:4326")
    points_gdf = (
        gpd.GeoDataFrame(all_points, crs=crs or "EPSG:4326")
        if all_points
        else gpd.GeoDataFrame(crs=crs or "EPSG:4326")
    )

    return kmz_path, lines_gdf, points_gdf


def analyze_grid_connectivity(
    site_lat: float,
    site_lon: float,
    plant_ac_mw: float,
    country: str,
    data_root: Path,
    region: str | None = None,
    connection_tolerance: int = 200,
    return_geometries: bool = False,
) -> dict[str, Any]:
    """
    Analyze grid connectivity for a solar plant site.

    Args:
        site_lat: Site latitude (WGS84)
        site_lon: Site longitude (WGS84)
        plant_ac_mw: Plant AC capacity in MW
        country: Country (e.g. "japan") - loads from data_root/{country}/
        data_root: Base path to grid network data (e.g. BASE_DIR / "engineering_tools" / "grid_network")
        region: Optional region for region-specific file; if None, uses country-wide file
        connection_tolerance: Max distance (m) from line to consider substation connected
        return_geometries: If True, include WGS84 geometries for KML overlay

    Returns:
        Dict with line_name, line_voltage_kv, distance_to_line_m, substation_name, etc.
        When return_geometries=True, adds nearest_line_coords_wgs84, substation_coords_wgs84,
        connection_line_coords_wgs84 (site to nearest point on TL).
    """
    _, lines_gdf, substations_gdf = _load_grid_geometries(data_root, country, region)

    utm_epsg = _get_utm_epsg(site_lon, site_lat)
    site_point = Point(site_lon, site_lat)
    site_gdf = gpd.GeoDataFrame(
        [{"geometry": site_point}],
        crs=4326,
    ).to_crs(epsg=utm_epsg)
    site_utm = site_gdf.geometry.iloc[0]

    lines_utm = lines_gdf.to_crs(epsg=utm_epsg)
    if substations_gdf.empty:
        subs_utm = gpd.GeoDataFrame()
    else:
        subs_utm = substations_gdf.to_crs(epsg=utm_epsg)

    distances = lines_utm.geometry.distance(site_utm)
    nearest_line_idx = distances.idxmin()
    nearest_line_row = lines_utm.loc[nearest_line_idx]
    min_line_dist = float(nearest_line_row.geometry.distance(site_utm))

    if nearest_line_row is None:
        raise GridConnectivityError("Could not find nearest transmission line")

    distance_to_line_m = float(min_line_dist)

    line_name = ""
    for col in ["name", "Name", "NAME", "description", "Description"]:
        if col in nearest_line_row.index and nearest_line_row[col] is not None:
            line_name = str(nearest_line_row[col]).strip()
            break
    if not line_name:
        line_name = f"Line_{nearest_line_idx}"

    attrs = _gather_string_attrs(nearest_line_row)
    line_voltage_kv = _search_attrs_for_value(attrs, _VOLTAGE_RE)
    if line_voltage_kv is None:
        line_voltage_kv = 0.0

    installed_capacity_mw: float | None = None
    available_capacity_mw: float | None = None
    substation_name = ""
    distance_to_substation_m: float | None = None
    connected_subs: list = []

    if not subs_utm.empty:
        nearest_line_geom = nearest_line_row.geometry
        for idx, sub_row in subs_utm.iterrows():
            d = sub_row.geometry.distance(nearest_line_geom)
            if d <= connection_tolerance:
                dist_to_site = sub_row.geometry.distance(site_utm)
                for col in ["name", "Name", "NAME", "description", "Description"]:
                    if col in sub_row.index and sub_row[col] is not None:
                        substation_name = str(sub_row[col]).strip()
                        break
                if not substation_name:
                    substation_name = f"Substation_{idx}"
                sub_attrs = _gather_string_attrs(sub_row)
                inst = _search_attrs_for_value(sub_attrs, _CAPACITY_MW_RE)
                connected_subs.append((dist_to_site, substation_name, inst, sub_row))
        if connected_subs:
            connected_subs.sort(key=lambda x: x[0])
            _, substation_name, installed_capacity_mw, _ = connected_subs[0]
            distance_to_substation_m = float(connected_subs[0][0])
            if installed_capacity_mw is not None:
                available_capacity_mw = installed_capacity_mw

    if installed_capacity_mw is None:
        installed_capacity_mw = 0.0
    if available_capacity_mw is None:
        available_capacity_mw = 0.0
    if distance_to_substation_m is None:
        distance_to_substation_m = 0.0

    if plant_ac_mw > available_capacity_mw and available_capacity_mw > 0:
        capacity_status = "INSUFFICIENT GRID CAPACITY"
    elif available_capacity_mw == 0 and installed_capacity_mw == 0:
        capacity_status = "UNKNOWN (no capacity data in grid file)"
    else:
        capacity_status = "SUFFICIENT GRID CAPACITY"

    out: dict[str, Any] = {
        "line_name": line_name,
        "line_voltage_kv": round(float(line_voltage_kv), 2),
        "distance_to_line_m": round(distance_to_line_m, 2),
        "substation_name": substation_name,
        "installed_capacity_mw": round(float(installed_capacity_mw), 2),
        "available_capacity_mw": round(float(available_capacity_mw), 2),
        "distance_to_substation_m": round(float(distance_to_substation_m), 2),
        "capacity_status": capacity_status,
    }

    if return_geometries:
        nearest_line_wgs = lines_gdf.loc[nearest_line_idx].geometry
        if nearest_line_wgs is not None and not nearest_line_wgs.is_empty:
            if hasattr(nearest_line_wgs, "coords"):
                out["nearest_line_coords_wgs84"] = [
                    (round(c[0], 8), round(c[1], 8)) for c in nearest_line_wgs.coords
                ]
            else:
                out["nearest_line_coords_wgs84"] = []
        else:
            out["nearest_line_coords_wgs84"] = []

        site_point_wgs = Point(site_lon, site_lat)
        nearest_line_geom = lines_gdf.loc[nearest_line_idx].geometry
        if nearest_line_geom is not None:
            pt_site, pt_line = nearest_points(site_point_wgs, nearest_line_geom)
            out["connection_line_coords_wgs84"] = [
                (round(site_lon, 8), round(site_lat, 8)),
                (round(float(pt_line.x), 8), round(float(pt_line.y), 8)),
            ]
        else:
            out["connection_line_coords_wgs84"] = []

        if substation_name and connected_subs:
            sub_row = connected_subs[0][3]
            idx = sub_row.name if hasattr(sub_row, "name") else None
            if idx is not None and idx in substations_gdf.index:
                sub_geom = substations_gdf.loc[idx].geometry
                if sub_geom is not None and not sub_geom.is_empty:
                    out["substation_coords_wgs84"] = (
                        round(float(sub_geom.x), 8),
                        round(float(sub_geom.y), 8),
                    )
                else:
                    out["substation_coords_wgs84"] = None
            else:
                out["substation_coords_wgs84"] = None
        else:
            out["substation_coords_wgs84"] = None

    return out
