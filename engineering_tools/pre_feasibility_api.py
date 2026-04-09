"""
Pre-feasibility API for Engineering Tools (Solar Insight parity).
In-memory store: projects, site_orientation, module_assumptions, string_configuration.
Module and inverter master data loaded from CSV under data_master/.
"""
import csv
import json
import logging
from math import ceil, floor
from pathlib import Path

from django.conf import settings
from django.http import HttpResponse, JsonResponse
from django.views.decorators.http import require_http_methods
from django.utils.decorators import method_decorator

from engineering_tools.mixins import EngineeringToolsProtectedView
from engineering_tools.solar_services.pre_feasibility_validators import (
    PreFeasibilityValidationError,
    validate_tilt_deg,
    validate_azimuth_deg,
    validate_structure_height_m,
    validate_soiling_rate_pct,
    validate_module_wp,
    validate_degradation_pct_per_year,
    validate_module_dimensions,
    validate_strings_per_inverter,
)

logger = logging.getLogger(__name__)

# In-memory store (no DB). Keyed by project_id (int).
_project_counter = 0
_store = {
    "projects": {},
    "site_orientation": {},
    "module_assumptions": {},
    "string_configuration": {},
}

_DATA_MASTER_DIR = Path(__file__).resolve().parent / "data_master"
_MODULE_MASTER_CACHE = None
_INVERTER_MASTER_CACHE = None


def _bad_request(detail: str, status: int = 400):
    return JsonResponse({"detail": detail}, status=status)


def _get_json_body(request):
    if request.content_type and "application/json" in request.content_type:
        try:
            return json.loads(request.body.decode("utf-8"))
        except json.JSONDecodeError:
            return None
    return None


def _load_module_master():
    global _MODULE_MASTER_CACHE
    if _MODULE_MASTER_CACHE is not None:
        return _MODULE_MASTER_CACHE
    path = _DATA_MASTER_DIR / "pv_module_master_v1.csv"
    if not path.exists():
        _MODULE_MASTER_CACHE = []
        return _MODULE_MASTER_CACHE
    out = []
    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for i, row in enumerate(reader):
            try:
                out.append({
                    "id": i + 1,
                    "make": (row.get("make") or "").strip(),
                    "model": (row.get("model") or "").strip(),
                    "watt_peak": int(float(row.get("watt_peak", 0))),
                    "height_m": float(row.get("height_m", 0)),
                    "width_m": float(row.get("width_m", 0)),
                    "efficiency_pct": float(row.get("efficiency_pct", 0)),
                    "voc_v": float(row.get("voc_v", 0)),
                    "vmp_v": float(row.get("vmp_v", 0)),
                    "temp_coeff_pmax_pct": float(row.get("temp_coeff_pmax_pct", 0)),
                    "temp_coeff_voc_pct": float(row.get("temp_coeff_voc_pct", 0)),
                    "bifaciality_factor": float(row.get("bifaciality_factor", 0.8)),
                })
            except (ValueError, TypeError):
                continue
    _MODULE_MASTER_CACHE = out
    return out


def _load_inverter_master():
    global _INVERTER_MASTER_CACHE
    if _INVERTER_MASTER_CACHE is not None:
        return _INVERTER_MASTER_CACHE
    path = _DATA_MASTER_DIR / "inverter_master_v1.csv"
    if not path.exists():
        _INVERTER_MASTER_CACHE = []
        return _INVERTER_MASTER_CACHE
    out = []
    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for i, row in enumerate(reader):
            try:
                model = (row.get("model") or "").strip()
                out.append({
                    "id": i + 1,
                    "make": (row.get("make") or "").strip(),
                    "model": model,
                    "ac_capacity_kw": float(row.get("ac_capacity_kw", 0)),
                    "efficiency_pct": float(row.get("efficiency_pct", 0)),
                    "mppt_min_v": int(float(row.get("mppt_min_v", 0))),
                    "mppt_max_v": int(float(row.get("mppt_max_v", 0))),
                    "pcs_nameplate": model,
                })
            except (ValueError, TypeError):
                continue
    _INVERTER_MASTER_CACHE = out
    return out


@method_decorator(require_http_methods(["POST"]), name="dispatch")
class ProjectGetOrCreateView(EngineeringToolsProtectedView):
    def post(self, request):
        data = _get_json_body(request)
        if not data:
            return _bad_request("JSON body required")
        try:
            lat = float(data.get("latitude"))
            lng = float(data.get("longitude"))
        except (TypeError, ValueError):
            return _bad_request("latitude and longitude must be numbers")
        if not (-90 <= lat <= 90):
            return _bad_request("Latitude must be between -90 and 90")
        if not (-180 <= lng <= 180):
            return _bad_request("Longitude must be between -180 and 180")
        # Reuse existing project when the same coordinates are requested again.
        # This keeps site orientation, module assumptions, and string configuration
        # in sync across all Engineering blocks for a given location.
        for pid, proj in _store["projects"].items():
            if proj.get("latitude") == lat and proj.get("longitude") == lng:
                return JsonResponse({"id": pid, "latitude": lat, "longitude": lng})
        global _project_counter
        _project_counter += 1
        pid = _project_counter
        _store["projects"][pid] = {"latitude": lat, "longitude": lng}
        return JsonResponse({"id": pid, "latitude": lat, "longitude": lng})


class SiteOrientationView(EngineeringToolsProtectedView):
    def get(self, request, project_id: int):
        if project_id not in _store["projects"]:
            return _bad_request("Project not found", 404)
        proj = _store["projects"][project_id]
        data = _store["site_orientation"].get(project_id, {})
        return JsonResponse({
            "latitude": proj["latitude"],
            "longitude": proj["longitude"],
            "tilt_deg": data.get("tilt_deg"),
            "azimuth_deg": data.get("azimuth_deg"),
            "structure_height_m": data.get("structure_height_m"),
            "soiling_rate_pct": data.get("soiling_rate_pct"),
        })

    def _save(self, request, project_id: int):
        if project_id not in _store["projects"]:
            return _bad_request("Project not found", 404)
        data = _get_json_body(request)
        if not data:
            return _bad_request("JSON body required")
        try:
            tilt_deg = float(data.get("tilt_deg"))
            azimuth_deg = float(data.get("azimuth_deg"))
        except (TypeError, ValueError):
            return _bad_request("tilt_deg and azimuth_deg must be numbers")
        structure_height_m = data.get("structure_height_m")
        if structure_height_m not in (None, ""):
            try:
                structure_height_m = float(structure_height_m)
            except (TypeError, ValueError):
                structure_height_m = None
        else:
            structure_height_m = None
        try:
            soiling_rate_pct = float(data.get("soiling_rate_pct"))
        except (TypeError, ValueError):
            return _bad_request("soiling_rate_pct must be a number")
        try:
            validate_tilt_deg(tilt_deg)
            validate_azimuth_deg(azimuth_deg)
            validate_structure_height_m(structure_height_m)
            validate_soiling_rate_pct(soiling_rate_pct)
        except PreFeasibilityValidationError as e:
            return _bad_request(str(e))
        proj = _store["projects"][project_id]
        _store["site_orientation"][project_id] = {
            "latitude": proj["latitude"],
            "longitude": proj["longitude"],
            "tilt_deg": tilt_deg,
            "azimuth_deg": azimuth_deg,
            "structure_height_m": structure_height_m,
            "soiling_rate_pct": soiling_rate_pct,
        }
        return JsonResponse(_store["site_orientation"][project_id])

    @method_decorator(require_http_methods(["POST", "PUT"]))
    def post(self, request, project_id: int):
        return self._save(request, project_id)

    put = post


class ModuleAssumptionsView(EngineeringToolsProtectedView):
    def get(self, request, project_id: int):
        if project_id not in _store["projects"]:
            return _bad_request("Project not found", 404)
        data = _store["module_assumptions"].get(project_id, {})
        if not data:
            return JsonResponse({
                "module_make": "",
                "module_model": "",
                "module_wp": None,
                "module_length_mm": None,
                "module_width_mm": None,
                "module_efficiency_pct": None,
                "degradation_pct_per_year": None,
                "module_master_id": None,
            })
        return JsonResponse(data)

    def _save(self, request, project_id: int):
        if project_id not in _store["projects"]:
            return _bad_request("Project not found", 404)
        data = _get_json_body(request)
        if not data:
            return _bad_request("JSON body required")
        module_make = (data.get("module_make") or "").strip()
        module_model = (data.get("module_model") or "").strip()
        if not module_make:
            return _bad_request("module_make is required")
        if not module_model:
            return _bad_request("module_model is required")
        try:
            module_wp = int(data.get("module_wp"))
            module_length_mm = int(data.get("module_length_mm"))
            module_width_mm = int(data.get("module_width_mm"))
        except (TypeError, ValueError):
            return _bad_request("Module power and dimensions must be integers")
        module_efficiency_pct = data.get("module_efficiency_pct")
        if module_efficiency_pct not in (None, ""):
            try:
                module_efficiency_pct = float(module_efficiency_pct)
            except (TypeError, ValueError):
                module_efficiency_pct = None
        else:
            module_efficiency_pct = None
        try:
            degradation = float(data.get("degradation_pct_per_year"))
        except (TypeError, ValueError):
            return _bad_request("degradation_pct_per_year must be a number")
        try:
            validate_module_wp(module_wp)
            validate_module_dimensions(module_length_mm, module_width_mm)
            validate_degradation_pct_per_year(degradation)
        except PreFeasibilityValidationError as e:
            return _bad_request(str(e))
        module_master_id = data.get("module_master_id")
        _store["module_assumptions"][project_id] = {
            "module_make": module_make,
            "module_model": module_model,
            "module_wp": module_wp,
            "module_length_mm": module_length_mm,
            "module_width_mm": module_width_mm,
            "module_efficiency_pct": module_efficiency_pct,
            "degradation_pct_per_year": degradation,
            "module_master_id": module_master_id,
        }
        return JsonResponse(_store["module_assumptions"][project_id])

    @method_decorator(require_http_methods(["POST", "PUT"]))
    def post(self, request, project_id: int):
        return self._save(request, project_id)

    put = post


def _compute_min_max_modules(module_master_id: int, inverter_master_id: int):
    modules = {m["id"]: m for m in _load_module_master()}
    inverters = {i["id"]: i for i in _load_inverter_master()}
    mod = modules.get(module_master_id)
    inv = inverters.get(inverter_master_id)
    if not mod or not inv:
        return None, None
    vmp = mod.get("vmp_v") or 0
    voc = mod.get("voc_v") or 0
    temp_coeff_pmax_pct = mod.get("temp_coeff_pmax_pct") or 0
    mppt_min_v = inv.get("mppt_min_v") or 0
    mppt_max_v = inv.get("mppt_max_v") or 0
    if not vmp or not voc:
        return None, None
    temp_coeff = temp_coeff_pmax_pct / 100.0
    delta_t_hot = 50.0 - 25.0
    vmp_at_hot = vmp * (1.0 + temp_coeff * delta_t_hot)
    if vmp_at_hot <= 0:
        return None, None
    min_modules = ceil(mppt_min_v / vmp_at_hot)
    delta_t_cold = 0.0 - 25.0
    voc_at_cold = voc * (1.0 + temp_coeff * delta_t_cold)
    if voc_at_cold <= 0:
        return None, None
    max_modules = floor(mppt_max_v / voc_at_cold)
    if min_modules <= 0 or max_modules <= 0 or min_modules > max_modules:
        return None, None
    return min_modules, max_modules


class StringConfigurationView(EngineeringToolsProtectedView):
    def get(self, request, project_id: int):
        if project_id not in _store["projects"]:
            return _bad_request("Project not found", 404)
        data = dict(_store["string_configuration"].get(project_id, {}))
        if not data:
            data = {
                "module_master_id": None,
                "inverter_master_id": None,
                "inverter_make": None,
                "inverter_model": None,
                "min_modules_in_series": None,
                "max_modules_in_series": None,
                "design_modules_in_series": None,
                "strings_per_inverter": None,
                "dc_ac_ratio": None,
            }
        # Optional preview: compute min/max when inverter_master_id is in query (for UI to show before save)
        inverter_master_id_param = request.GET.get("inverter_master_id")
        if inverter_master_id_param is not None:
            try:
                inv_id = int(inverter_master_id_param)
            except (TypeError, ValueError):
                inv_id = None
            if inv_id is not None:
                mod_assumptions = _store["module_assumptions"].get(project_id)
                module_master_id = mod_assumptions.get("module_master_id") if mod_assumptions else None
                if module_master_id:
                    min_modules, max_modules = _compute_min_max_modules(int(module_master_id), inv_id)
                    if min_modules is not None and max_modules is not None:
                        data["min_modules_in_series"] = min_modules
                        data["max_modules_in_series"] = max_modules
                # If no module assumptions or computation failed, keep existing None min/max
        return JsonResponse(data)

    def _save(self, request, project_id: int):
        if project_id not in _store["projects"]:
            return _bad_request("Project not found", 404)
        mod_assumptions = _store["module_assumptions"].get(project_id)
        if not mod_assumptions:
            return _bad_request("Module assumptions must be saved before string configuration")
        data = _get_json_body(request)
        if not data:
            return _bad_request("JSON body required")
        inverter_master_id = data.get("inverter_master_id")
        if inverter_master_id is None:
            return _bad_request("inverter_master_id is required")
        inverters = {i["id"]: i for i in _load_inverter_master()}
        inv = inverters.get(int(inverter_master_id))
        if not inv:
            return _bad_request("Selected inverter master not found")
        module_master_id = mod_assumptions.get("module_master_id")
        if not module_master_id:
            return _bad_request("Module assumptions must reference a module master (select from list)")
        min_modules, max_modules = _compute_min_max_modules(
            int(module_master_id), int(inverter_master_id)
        )
        if min_modules is None:
            return _bad_request("Cannot compute valid modules-in-series range for this module/inverter pair")
        design_modules_in_series = data.get("design_modules_in_series")
        if design_modules_in_series not in (None, ""):
            try:
                design_modules_in_series = int(design_modules_in_series)
            except (TypeError, ValueError):
                return _bad_request("design_modules_in_series must be an integer")
            if not (min_modules <= design_modules_in_series <= max_modules):
                return _bad_request(
                    f"design_modules_in_series must be between {min_modules} and {max_modules}"
                )
        else:
            design_modules_in_series = None
        strings_per_inverter = data.get("strings_per_inverter")
        if strings_per_inverter not in (None, ""):
            try:
                strings_per_inverter = int(strings_per_inverter)
                validate_strings_per_inverter(strings_per_inverter)
            except (TypeError, ValueError, PreFeasibilityValidationError) as e:
                return _bad_request(str(e))
        else:
            strings_per_inverter = None
        dc_ac_ratio = data.get("dc_ac_ratio")
        if dc_ac_ratio not in (None, ""):
            try:
                dc_ac_ratio = float(dc_ac_ratio)
            except (TypeError, ValueError):
                dc_ac_ratio = None
        else:
            dc_ac_ratio = None
        _store["string_configuration"][project_id] = {
            "module_master_id": int(module_master_id),
            "inverter_master_id": int(inverter_master_id),
            "inverter_make": inv["make"],
            "inverter_model": inv["model"],
            "min_modules_in_series": min_modules,
            "max_modules_in_series": max_modules,
            "design_modules_in_series": design_modules_in_series,
            "strings_per_inverter": strings_per_inverter,
            "dc_ac_ratio": dc_ac_ratio,
        }
        return JsonResponse(_store["string_configuration"][project_id])

    @method_decorator(require_http_methods(["POST", "PUT"]))
    def post(self, request, project_id: int):
        return self._save(request, project_id)

    put = post


class ModuleMasterListView(EngineeringToolsProtectedView):
    def get(self, request):
        modules = _load_module_master()
        make = request.GET.get("make", "").strip()
        if make:
            modules = [m for m in modules if (m.get("make") or "").strip().lower() == make.lower()]
        return JsonResponse(modules, safe=False)


class InverterMasterListView(EngineeringToolsProtectedView):
    def get(self, request):
        inverters = _load_inverter_master()
        make = request.GET.get("make", "").strip()
        if make:
            inverters = [i for i in inverters if (i.get("make") or "").strip().lower() == make.lower()]
        return JsonResponse(inverters, safe=False)


# ---------------------------------------------------------------------------
# Export Layout KML (PV array layout + optional grid TL/substation overlay)
# ---------------------------------------------------------------------------

def _get_int_post(request, key: str):
    val = request.POST.get(key)
    if val is None or val == "":
        return None
    try:
        return int(float(val))
    except (TypeError, ValueError):
        return None


def _get_float_post(request, key: str):
    val = request.POST.get(key)
    if val is None or val == "":
        return None
    try:
        return float(val)
    except (TypeError, ValueError):
        return None


def _compute_table_dimensions(array_config: str, length_mm, width_mm):
    """Return (table_length_m, table_width_m) from array config and module dimensions (mm)."""
    h_m = length_mm / 1000.0
    w_m = width_mm / 1000.0
    if array_config == "portrait":
        table_length_m = 2.0 * h_m + 0.02
        table_width_m = 2.0 * w_m
    else:
        table_length_m = 4.0 * w_m + 0.06
        table_width_m = 4.0 * h_m
    return table_length_m, table_width_m


@method_decorator(require_http_methods(["POST"]), name="dispatch")
class ExportLayoutKmlView(EngineeringToolsProtectedView):
    """
    POST multipart: boundary_kml (file), project_id (optional), layout params, country (optional).
    Returns KMZ download and X-Export-Summary header with KPI + grid connectivity (TL/substation).
    """

    def post(self, request):
        from engineering_tools.solar_services.grid_connectivity import analyze_grid_connectivity
        from engineering_tools.solar_services.layout_kml import run_layout_export

        boundary_kml = request.FILES.get("boundary_kml")
        if not boundary_kml or not boundary_kml.name:
            return _bad_request("boundary_kml file is required")
        if not boundary_kml.name.lower().endswith((".kml", ".kmz")):
            return _bad_request("boundary_kml must be a .kml or .kmz file")
        try:
            kml_content = boundary_kml.read()
        except Exception as e:
            logger.exception("Failed to read boundary KML")
            return _bad_request(f"Failed to read file: {e}")
        if not kml_content:
            return _bad_request("boundary_kml file is empty")

        project_id = _get_int_post(request, "project_id")
        array_config = (request.POST.get("array_config") or "").strip().lower()
        if array_config not in ("portrait", "landscape"):
            array_config = None

        modules_per_table = _get_int_post(request, "modules_per_table")
        module_wp = _get_float_post(request, "module_wp")
        table_length_m = _get_float_post(request, "table_length_m")
        table_width_m = _get_float_post(request, "table_width_m")
        azimuth_deg = _get_float_post(request, "azimuth_deg")
        row_spacing_m = _get_float_post(request, "row_spacing_m")
        structure_gap_m = _get_float_post(request, "structure_gap_m")
        boundary_offset_m = _get_float_post(request, "boundary_offset_m")

        project = None
        if project_id and project_id in _store["projects"]:
            project = _store["projects"][project_id]
            orient = _store["site_orientation"].get(project_id, {})
            if azimuth_deg is None and orient.get("azimuth_deg") is not None:
                azimuth_deg = float(orient["azimuth_deg"])
            mod_assumptions = _store["module_assumptions"].get(project_id)
            if mod_assumptions is not None:
                if module_wp is None and mod_assumptions.get("module_wp") is not None:
                    module_wp = float(mod_assumptions["module_wp"])
                length_mm = mod_assumptions.get("module_length_mm")
                width_mm = mod_assumptions.get("module_width_mm")
                if array_config and length_mm is not None and width_mm is not None:
                    if table_length_m is None or table_width_m is None:
                        tl, tw = _compute_table_dimensions(array_config, length_mm, width_mm)
                        if table_length_m is None:
                            table_length_m = tl
                        if table_width_m is None:
                            table_width_m = tw
            str_cfg = _store["string_configuration"].get(project_id, {})
            if modules_per_table is None and str_cfg.get("design_modules_in_series") is not None:
                modules_per_table = int(str_cfg["design_modules_in_series"])

        if modules_per_table is None or module_wp is None:
            return _bad_request(
                "modules_per_table and module_wp are required (or save module/string config and send project_id)"
            )
        if table_length_m is None or table_width_m is None:
            if array_config and project_id and project is not None:
                mod_assumptions = _store["module_assumptions"].get(project_id)
                if mod_assumptions and mod_assumptions.get("module_length_mm") is not None and mod_assumptions.get("module_width_mm") is not None:
                    try:
                        table_length_m, table_width_m = _compute_table_dimensions(
                            array_config,
                            mod_assumptions["module_length_mm"],
                            mod_assumptions["module_width_mm"],
                        )
                    except Exception:
                        pass
            if table_length_m is None or table_width_m is None:
                return _bad_request(
                    "table_length_m and table_width_m are required (or provide project_id and array_config with saved module assumptions)"
                )
        if azimuth_deg is None:
            return _bad_request("azimuth_deg is required (or save site orientation and send project_id)")
        if row_spacing_m is None:
            return _bad_request("row_spacing_m is required")
        if structure_gap_m is None:
            return _bad_request("structure_gap_m is required (distance between adjacent modules)")
        if boundary_offset_m is None:
            return _bad_request("boundary_offset_m is required (boundary setback)")

        country = (request.POST.get("country") or "").strip()
        region = (request.POST.get("region") or "").strip() or None
        grid_overlays_callback = None
        if country and project_id and project is not None:
            data_root = getattr(settings, "GRID_NETWORK_DATA_ROOT", Path(settings.BASE_DIR) / "engineering_tools" / "grid_network")
            if not isinstance(data_root, Path):
                data_root = Path(data_root)
            if not data_root.exists():
                logging.getLogger(__name__).warning("GRID_NETWORK_DATA_ROOT does not exist: %s", data_root)
            dc_ac_ratio_val = 1.25
            str_cfg = _store["string_configuration"].get(project_id, {})
            if str_cfg.get("dc_ac_ratio") is not None:
                try:
                    dc_ac_ratio_val = float(str_cfg["dc_ac_ratio"])
                except (TypeError, ValueError):
                    pass

            def _grid_callback(partial):
                plant_ac_mw = (partial["total_dc_kwp"] / 1000.0) / dc_ac_ratio_val
                return analyze_grid_connectivity(
                    site_lat=project["latitude"],
                    site_lon=project["longitude"],
                    plant_ac_mw=plant_ac_mw,
                    country=country,
                    data_root=data_root,
                    region=region,
                    return_geometries=True,
                )

            grid_overlays_callback = _grid_callback

        try:
            result = run_layout_export(
                kml_content,
                modules_per_table=modules_per_table,
                module_wp=float(module_wp),
                table_length_m=float(table_length_m),
                table_width_m=float(table_width_m),
                azimuth_deg=float(azimuth_deg),
                row_spacing_m=float(row_spacing_m),
                structure_gap_m=float(structure_gap_m),
                boundary_offset_m=float(boundary_offset_m),
                array_config=array_config or "landscape",
                grid_overlays_callback=grid_overlays_callback,
            )
        except ValueError as e:
            return _bad_request(str(e))

        summary = {
            "land_area_m2": round(result["land_area_m2"], 1),
            "table_count": result["table_count"],
            "interrow_spacing_m": round(result["interrow_spacing_m"], 3),
            "full_tables": result["full_tables"],
            "half_tables": result["half_tables"],
            "quarter_tables": result["quarter_tables"],
            "full_dc_kwp": result["full_dc_kwp"],
            "half_dc_kwp": result["half_dc_kwp"],
            "quarter_dc_kwp": result["quarter_dc_kwp"],
            "total_dc_kwp": result["total_dc_kwp"],
            "total_modules": result["total_modules"],
        }
        grid_connectivity = result.get("grid_connectivity")
        if grid_connectivity:
            summary["grid_connectivity"] = grid_connectivity
            summary["nearest_tl_voltage_kv"] = grid_connectivity["line_voltage_kv"]
            summary["distance_to_line_m"] = grid_connectivity["distance_to_line_m"]
            summary["substation_name"] = grid_connectivity["substation_name"]
            summary["line_name"] = grid_connectivity["line_name"]
            summary["distance_to_substation_m"] = grid_connectivity["distance_to_substation_m"]
        grid_err = result.get("grid_connectivity_error")
        if grid_err:
            summary["grid_connectivity_error"] = grid_err

        filename = "PV_Array_Layout.kmz"
        response = HttpResponse(result["kmz_bytes"], content_type="application/vnd.google-earth.kmz")
        response["Content-Disposition"] = f'attachment; filename="{filename}"'
        response["X-Export-Summary"] = json.dumps(summary)
        return response
