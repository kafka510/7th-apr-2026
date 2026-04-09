from io import BytesIO
from typing import List, Tuple

import geopandas as gpd
from shapely.geometry import Polygon
from shapely.geometry.multipolygon import MultiPolygon
from shapely.validation import make_valid
from pyproj import Transformer

from .validators import ValidationError, validate_area_m2


def _get_utm_epsg(longitude: float, latitude: float) -> str:
    zone = int((longitude + 180) / 6) + 1
    if latitude >= 0:
        return f"EPSG:{32600 + zone}"
    return f"EPSG:{32700 + zone}"


def _geometry_area_m2(geometry) -> float:
    from shapely.ops import transform
    centroid = geometry.centroid
    utm_crs = _get_utm_epsg(centroid.x, centroid.y)
    transformer = Transformer.from_crs("EPSG:4326", utm_crs, always_xy=True)
    projected = transform(transformer.transform, geometry)
    return projected.area


def read_kml_plant_area(kml_content: bytes) -> float:
    try:
        gdf = gpd.read_file(BytesIO(kml_content), driver="KML")
    except Exception as e:
        raise ValidationError(f"KML read error: {e}") from e

    if gdf.empty:
        raise ValidationError("KML file contains no geometry")

    geometry = gdf.geometry.iloc[0]
    if geometry is None or geometry.is_empty:
        raise ValidationError("KML: first geometry is empty")

    if not isinstance(geometry, (Polygon, MultiPolygon)):
        geometry = geometry.convex_hull
        if not isinstance(geometry, (Polygon, MultiPolygon)):
            raise ValidationError("KML geometry is not a polygon or multipolygon")

    if not geometry.is_valid:
        geometry = make_valid(geometry)
    if geometry.is_empty:
        raise ValidationError("KML: polygon is empty after validation")

    plant_area_m2 = _geometry_area_m2(geometry)
    validate_area_m2(plant_area_m2)
    return plant_area_m2


def read_kml_boundary_coordinates(kml_content: bytes) -> List[List[float]]:
    """
    Extract polygon boundary coordinates from KML for map display.
    Returns list of [lat, lng] pairs (Leaflet format).
    """
    try:
        gdf = gpd.read_file(BytesIO(kml_content), driver="KML")
    except Exception as e:
        raise ValidationError(f"KML read error: {e}") from e

    if gdf.empty:
        raise ValidationError("KML file contains no geometry")

    geometry = gdf.geometry.iloc[0]
    if geometry is None or geometry.is_empty:
        raise ValidationError("KML: first geometry is empty")

    if not isinstance(geometry, (Polygon, MultiPolygon)):
        geometry = geometry.convex_hull
        if not isinstance(geometry, (Polygon, MultiPolygon)):
            raise ValidationError("KML geometry is not a polygon or multipolygon")

    if not geometry.is_valid:
        geometry = make_valid(geometry)
    if geometry.is_empty:
        raise ValidationError("KML: polygon is empty after validation")

    if isinstance(geometry, MultiPolygon):
        geometry = max(geometry.geoms, key=lambda g: g.area)
    exterior = geometry.exterior
    if exterior is None:
        return []

    coords: List[List[float]] = []
    for coord in exterior.coords:
        x, y = float(coord[0]), float(coord[1])
        coords.append([y, x])  # [lat, lng] for Leaflet
    return coords


def compute_dc_capacity(
    plant_area_m2: float,
    module_wattage_wp: float,
    module_area_m2: float,
    land_usage_factor: float,
) -> Tuple[float, float, int]:
    usable_area_m2 = plant_area_m2 * land_usage_factor
    number_of_modules = int(usable_area_m2 / module_area_m2)
    dc_capacity_kwp = (number_of_modules * module_wattage_wp) / 1000.0
    dc_capacity_mwp = dc_capacity_kwp / 1000.0
    return dc_capacity_mwp, usable_area_m2, number_of_modules
