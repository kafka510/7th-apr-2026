"""
PV array layout and KMZ export (Corrected Engineering Version)
Azimuth-aligned grid generation for accurate solar layout.
Copied from solar-insight pre_feasibility/layout_kml.py for Engineering Tools.
"""

from io import BytesIO
from typing import Any, List, Tuple

import geopandas as gpd
from shapely.geometry import box
from shapely.geometry import Polygon, MultiPolygon
from shapely.affinity import rotate
from pyproj import Transformer
import simplekml


def _get_utm_epsg(longitude: float, latitude: float) -> int:
    zone = int((longitude + 180) / 6) + 1
    return 32600 + zone if latitude >= 0 else 32700 + zone


def load_boundary_and_utm(kml_content: bytes) -> Tuple[Any, int]:
    gdf = gpd.read_file(BytesIO(kml_content), driver="KML")
    gdf = gdf[gdf.geometry.type.isin(["Polygon", "MultiPolygon"])]

    if gdf.empty:
        raise ValueError("KML contains no polygon geometry")

    if gdf.crs is None:
        gdf = gdf.set_crs(epsg=4326)

    union_wgs = gdf.geometry.union_all()
    centroid = union_wgs.centroid
    utm_epsg = _get_utm_epsg(centroid.x, centroid.y)

    gdf_utm = gdf.to_crs(epsg=utm_epsg)
    land = gdf_utm.geometry.union_all()

    if not land.is_valid:
        land = land.buffer(0)

    if land.is_empty:
        raise ValueError("Boundary invalid after processing")

    return land, utm_epsg


COORD_PRECISION = 8


def _round_coord(c):
    if len(c) >= 3:
        return (round(c[0], COORD_PRECISION), round(c[1], COORD_PRECISION), round(c[2], COORD_PRECISION))
    return (round(c[0], COORD_PRECISION), round(c[1], COORD_PRECISION))


def _boundary_coords(geom):
    if geom is None or geom.is_empty:
        return []
    if isinstance(geom, MultiPolygon):
        geom = max(geom.geoms, key=lambda g: g.area)
    if not hasattr(geom, "exterior") or geom.exterior is None:
        return []
    return list(geom.exterior.coords)


def _add_module_cell_grid(parent_folder, module_rect_utm, to_wgs84, table_color):
    if module_rect_utm is None:
        return
    minx, miny, maxx, maxy = module_rect_utm.bounds
    w = maxx - minx
    h = maxy - miny
    if w <= 0 or h <= 0:
        return

    def utm_to_wgs(cx, cy):
        x, y = to_wgs84.transform(float(cx), float(cy))
        return _round_coord((x, y))

    for i in range(1, 3):
        cx = minx + (w * i / 3)
        line = parent_folder.newlinestring(name="")
        line.coords = [utm_to_wgs(cx, miny), utm_to_wgs(cx, maxy)]
        line.tessellate = 1
        line.altitudemode = simplekml.AltitudeMode.clamptoground
        line.style.linestyle.color = simplekml.Color.changealphaint(100, table_color)
        line.style.linestyle.width = 0.5
    for j in range(1, 3):
        cy = miny + (h * j / 3)
        line = parent_folder.newlinestring(name="")
        line.coords = [utm_to_wgs(minx, cy), utm_to_wgs(maxx, cy)]
        line.tessellate = 1
        line.altitudemode = simplekml.AltitudeMode.clamptoground
        line.style.linestyle.color = simplekml.Color.changealphaint(100, table_color)
        line.style.linestyle.width = 0.5


def _to_single_polygon(geom):
    if geom is None or geom.is_empty:
        return None
    if isinstance(geom, MultiPolygon):
        geom = max(geom.geoms, key=lambda g: g.area)
    if not geom.is_valid:
        geom = geom.buffer(0)
    if isinstance(geom, MultiPolygon):
        geom = max(geom.geoms, key=lambda g: g.area)
    return geom if isinstance(geom, Polygon) and not geom.is_empty else None


def generate_tables(
    usable_land,
    table_length_m,
    table_width_m,
    row_spacing_m,
    structure_gap_m,
    azimuth_deg,
):
    tables = []
    origin = usable_land.centroid
    rotated_land = rotate(usable_land, -azimuth_deg, origin=origin, use_radians=False)
    minx, miny, maxx, maxy = rotated_land.bounds
    row_pitch = table_width_m + row_spacing_m
    y = miny

    while y <= maxy:
        x = minx
        while x <= maxx:
            placed = False
            full_tbl = box(x, y, x + table_length_m, y + table_width_m)
            if rotated_land.contains(full_tbl):
                tables.append(full_tbl)
                x += table_length_m + structure_gap_m
                placed = True
            else:
                half_length = table_length_m / 2
                half_tbl = box(x, y, x + half_length, y + table_width_m)
                if rotated_land.contains(half_tbl):
                    tables.append(half_tbl)
                    x += half_length + structure_gap_m
                    placed = True
                else:
                    quarter_length = table_length_m / 4
                    quarter_tbl = box(x, y, x + quarter_length, y + table_width_m)
                    if rotated_land.contains(quarter_tbl):
                        tables.append(quarter_tbl)
                        x += quarter_length + structure_gap_m
                        placed = True
            if not placed:
                x += table_length_m / 8
        y += row_pitch

    final_tables = [
        _to_single_polygon(rotate(tbl, azimuth_deg, origin=origin, use_radians=False))
        for tbl in tables
    ]
    return [t for t in final_tables if t is not None]


def _add_grid_folder_to_kml(kml: simplekml.Kml, grid_overlays: dict) -> None:
    gf = kml.newfolder(name="Grid Connectivity")
    gf.description = (
        f"Nearest TL Voltage: {grid_overlays.get('line_voltage_kv', 0)} kV | "
        f"Distance to Line: {grid_overlays.get('distance_to_line_m', 0)} m | "
        f"Substation: {grid_overlays.get('substation_name') or 'N/A'}"
    )
    line_coords = grid_overlays.get("nearest_line_coords_wgs84") or []
    if len(line_coords) >= 2:
        tl = gf.newlinestring(name="Nearest Transmission Line")
        tl.coords = line_coords
        tl.tessellate = 1
        tl.altitudemode = simplekml.AltitudeMode.clamptoground
        tl.style.linestyle.color = simplekml.Color.orange
        tl.style.linestyle.width = 4
    conn_coords = grid_overlays.get("connection_line_coords_wgs84") or []
    if len(conn_coords) >= 2:
        conn = gf.newlinestring(name="Connection (Site to TL)")
        conn.coords = conn_coords
        conn.tessellate = 1
        conn.altitudemode = simplekml.AltitudeMode.clamptoground
        conn.style.linestyle.color = simplekml.Color.rgb(255, 0, 0)
        conn.style.linestyle.width = 3
    sub_coords = grid_overlays.get("substation_coords_wgs84")
    if sub_coords:
        pt = gf.newpoint(name=grid_overlays.get("substation_name") or "Nearest Substation")
        pt.coords = [sub_coords]
        pt.altitudemode = simplekml.AltitudeMode.clamptoground
        pt.style.iconstyle.scale = 1.2
        pt.style.labelstyle.scale = 1.2


def run_layout_export(
    kml_content: bytes,
    *,
    modules_per_table: int,
    module_wp: float,
    table_length_m: float,
    table_width_m: float,
    azimuth_deg: float,
    row_spacing_m: float,
    structure_gap_m: float,
    boundary_offset_m: float,
    array_config: str = "landscape",
    grid_overlays_callback: Any = None,
) -> dict:
    land, utm_epsg = load_boundary_and_utm(kml_content)
    land_area_m2 = land.area
    usable_land = land.buffer(-boundary_offset_m)

    if usable_land.is_empty:
        raise ValueError("Boundary offset too large – no usable land")

    if not usable_land.is_valid:
        usable_land = usable_land.buffer(0)

    tables = generate_tables(
        usable_land,
        table_length_m,
        table_width_m,
        row_spacing_m,
        structure_gap_m,
        azimuth_deg,
    )

    table_count = len(tables)
    to_wgs84 = Transformer.from_crs(
        f"EPSG:{utm_epsg}",
        "EPSG:4326",
        always_xy=True
    )

    kml = simplekml.Kml()
    run_folder = kml.newfolder(name="PV Layout")

    land_coords = _boundary_coords(land)
    if land_coords:
        boundary = run_folder.newlinestring(name="Land Boundary")
        boundary.coords = [_round_coord(to_wgs84.transform(float(c[0]), float(c[1]))) for c in land_coords]
        boundary.tessellate = 1
        boundary.altitudemode = simplekml.AltitudeMode.clamptoground
        boundary.style.linestyle.color = simplekml.Color.red
        boundary.style.linestyle.width = 3

    usable_coords = _boundary_coords(usable_land)
    if usable_coords:
        offset_line = run_folder.newlinestring(name="Usable Boundary")
        offset_line.coords = [_round_coord(to_wgs84.transform(float(c[0]), float(c[1]))) for c in usable_coords]
        offset_line.tessellate = 1
        offset_line.altitudemode = simplekml.AltitudeMode.clamptoground
        offset_line.style.linestyle.color = simplekml.Color.yellow
        offset_line.style.linestyle.width = 2

    prefix = "4L" if array_config == "landscape" else "4P"
    full_label = f"{prefix}X24"
    half_label = f"{prefix}X12"
    quarter_label = f"{prefix}X6"

    full_folder = run_folder.newfolder(name=f"{full_label} (Full Tables)")
    half_folder = run_folder.newfolder(name=f"{half_label} (Half Tables)")
    quarter_folder = run_folder.newfolder(name=f"{quarter_label} (Quarter Tables)")

    full_count = half_count = quarter_count = actual_total_modules = 0

    for tbl in tables:
        tbl = _to_single_polygon(tbl)
        if tbl is None:
            continue
        coords_wgs = [
            _round_coord(to_wgs84.transform(float(c[0]), float(c[1])))
            for c in _boundary_coords(tbl)
        ]
        if not coords_wgs:
            continue
        tbl_minx, tbl_miny, tbl_maxx, tbl_maxy = tbl.bounds
        tbl_length = tbl_maxx - tbl_minx
        length_ratio = tbl_length / table_length_m

        if length_ratio >= 0.90:
            module_cols = modules_per_table
            table_color = simplekml.Color.changealphaint(200, simplekml.Color.rgb(0, 0, 150))
            folder = full_folder
            table_label = full_label
            full_count += 1
            type_index = full_count
        elif length_ratio >= 0.45:
            module_cols = modules_per_table // 2
            table_color = simplekml.Color.changealphaint(200, simplekml.Color.rgb(0, 90, 255))
            folder = half_folder
            table_label = half_label
            half_count += 1
            type_index = half_count
        else:
            module_cols = modules_per_table // 4
            table_color = simplekml.Color.changealphaint(200, simplekml.Color.rgb(120, 180, 255))
            folder = quarter_folder
            table_label = quarter_label
            quarter_count += 1
            type_index = quarter_count

        actual_total_modules += module_cols

        poly = folder.newpolygon(name=f"{table_label}_{type_index}")
        poly.outerboundaryis = coords_wgs
        poly.tessellate = 1
        poly.altitudemode = simplekml.AltitudeMode.clamptoground
        poly.style.polystyle.color = simplekml.Color.changealphaint(230, simplekml.Color.white)
        poly.style.linestyle.color = simplekml.Color.white
        poly.style.linestyle.width = 3

        cx = (tbl_minx + tbl_maxx) / 2
        cy = (tbl_miny + tbl_maxy) / 2
        lng, lat = to_wgs84.transform(float(cx), float(cy))
        r = _round_coord((lng, lat))
        pt = folder.newpoint(name=f"{table_label}_{type_index}")
        pt.coords = [(r[0], r[1])]
        pt.altitudemode = simplekml.AltitudeMode.clamptoground
        pt.style.iconstyle.scale = 0.01
        pt.style.labelstyle.color = simplekml.Color.white
        pt.style.labelstyle.scale = 1.3

        if module_cols > 0:
            module_length = tbl_length / module_cols
            table_modules_folder = folder.newfolder(name=f"{table_label}_{type_index} modules")
            for m in range(module_cols):
                mx1 = tbl_minx + m * module_length
                mx2 = mx1 + module_length
                my1, my2 = tbl_miny, tbl_maxy
                module_rect = box(mx1, my1, mx2, my2)
                module_rect_valid = _to_single_polygon(module_rect)
                if module_rect_valid is None:
                    continue
                module_coords = [
                    _round_coord(to_wgs84.transform(float(c[0]), float(c[1])))
                    for c in _boundary_coords(module_rect_valid)
                ]
                if not module_coords:
                    continue
                mod_poly = table_modules_folder.newpolygon(name=f"M{m+1}({module_cols})")
                mod_poly.outerboundaryis = module_coords
                mod_poly.tessellate = 1
                mod_poly.altitudemode = simplekml.AltitudeMode.clamptoground
                mod_poly.style.polystyle.color = table_color
                mod_poly.style.linestyle.color = simplekml.Color.rgb(30, 30, 50)
                mod_poly.style.linestyle.width = 1
                _add_module_cell_grid(table_modules_folder, module_rect, to_wgs84, table_color)

    total_dc_kwp_val = (
        full_count * modules_per_table
        + half_count * (modules_per_table // 2)
        + quarter_count * (modules_per_table // 4)
    ) * module_wp / 1000
    run_folder.description = (
        f"Full Tables: {full_count}\n"
        f"Half Tables: {half_count}\n"
        f"Quarter Tables: {quarter_count}\n"
        f"Total Tables: {table_count}\n"
        f"Total Modules: {actual_total_modules}\n"
        f"DC Capacity: {total_dc_kwp_val:.2f} kWp"
    )

    full_dc_kwp = full_count * modules_per_table * module_wp / 1000
    half_dc_kwp = half_count * (modules_per_table // 2) * module_wp / 1000
    quarter_dc_kwp = quarter_count * (modules_per_table // 4) * module_wp / 1000
    total_dc_kwp = full_dc_kwp + half_dc_kwp + quarter_dc_kwp
    partial_result = {
        "total_dc_kwp": total_dc_kwp,
        "land_area_m2": land_area_m2,
        "table_count": table_count,
    }
    grid_connectivity = None
    grid_connectivity_error = None
    if callable(grid_overlays_callback):
        import logging
        try:
            grid_overlays = grid_overlays_callback(partial_result)
            if grid_overlays:
                _add_grid_folder_to_kml(kml, grid_overlays)
                grid_connectivity = grid_overlays
        except Exception as e:
            logging.getLogger(__name__).warning("Grid connectivity analysis failed: %s", e)
            grid_connectivity_error = str(e)

    buf = BytesIO()
    kml.savekmz(buf)

    out = {
        "kmz_bytes": buf.getvalue(),
        "land_area_m2": land_area_m2,
        "table_count": table_count,
        "interrow_spacing_m": row_spacing_m,
        "full_tables": full_count,
        "half_tables": half_count,
        "quarter_tables": quarter_count,
        "full_dc_kwp": round(full_dc_kwp, 2),
        "half_dc_kwp": round(half_dc_kwp, 2),
        "quarter_dc_kwp": round(quarter_dc_kwp, 2),
        "total_dc_kwp": round(total_dc_kwp, 2),
        "total_modules": actual_total_modules,
    }
    if grid_connectivity is not None:
        out["grid_connectivity"] = grid_connectivity
    if grid_connectivity_error is not None:
        out["grid_connectivity_error"] = grid_connectivity_error
    return out
