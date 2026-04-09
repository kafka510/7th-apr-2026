"""
Engineering Tools API views - Solar Insight (Solargis monthly), Manual DC yield.
"""
import json
import logging
from pathlib import Path

from django.conf import settings
from django.http import JsonResponse
from django.utils.decorators import method_decorator
from django.views.decorators.http import require_http_methods

from engineering_tools.mixins import EngineeringToolsProtectedView
from engineering_tools.solar_services.yield_engine import (
    ManualDCInput,
    ManualDCOutput,
    MonthlySolarData,
    calculate_yield,
)

logger = logging.getLogger(__name__)


def _get_float(req, key, default=None):
    val = req.POST.get(key)
    if val is None:
        return default
    try:
        return float(val)
    except (TypeError, ValueError):
        return default


def _get_str(req, key, default=None):
    return req.POST.get(key, default)


def _bad_request(detail):
    return JsonResponse({"detail": detail}, status=400)


@method_decorator(require_http_methods(["POST"]), name="dispatch")
class SolargisMonthlyView(EngineeringToolsProtectedView):
    """POST /engineering-tools/api/solargis-monthly/ - Parse SolarGIS Prospect CSV."""

    def post(self, request):
        try:
            from engineering_tools.solar_services.validators import (
                validate_location,
                validate_csv_file,
            )
            from engineering_tools.solar_services.solargis_prospect_parser import (
                parse_solargis_prospect_monthly,
                extract_solargis_metadata,
            )
        except ImportError as e:
            logger.exception("Import error")
            return _bad_request(str(e))

        lat = _get_float(request, "latitude")
        lng = _get_float(request, "longitude")
        if lat is None or lng is None:
            return _bad_request("latitude and longitude are required")

        try:
            validate_location(lat, lng)
        except Exception as e:
            return _bad_request(str(e))

        solargis_csv = request.FILES.get("solargis_csv")
        if not solargis_csv or not solargis_csv.name:
            return _bad_request("solargis_csv: filename required")

        try:
            validate_csv_file(solargis_csv.name)
        except Exception as e:
            return _bad_request(str(e))

        location_name = _get_str(request, "location")

        try:
            csv_content = solargis_csv.read()
        except Exception as exc:
            logger.exception("Failed to read SolarGIS CSV upload")
            return _bad_request(f"Failed to read SolarGIS CSV: {exc}")

        if not csv_content:
            return _bad_request("solargis_csv: file is empty")

        try:
            records = parse_solargis_prospect_monthly(csv_content)
        except Exception as exc:
            logger.exception("Unexpected error parsing SolarGIS CSV")
            return _bad_request(str(exc))

        metadata = extract_solargis_metadata(csv_content)
        display_location = metadata.get("site_name") or location_name

        payload = {
            "location": display_location,
            "site_name": metadata.get("site_name"),
            "lat": lat,
            "lng": lng,
            "data_type": "SolarGIS LTA Monthly",
            "records": records,
        }
        return JsonResponse(payload)


def _get_json_body(request):
    if request.content_type and "application/json" in request.content_type:
        try:
            return json.loads(request.body.decode("utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError):
            return None
    return None


@method_decorator(require_http_methods(["POST"]), name="dispatch")
class ManualDCYieldView(EngineeringToolsProtectedView):
    """
    POST /engineering-tools/api/manual-dc-yield/
    Body: JSON Manual DC input (site, system, losses, monthly_data with 12 entries).
    Returns: monthly_energy_mwh, annual_energy_mwh, specific_yield_kwh_per_kwp, capacity_factor_percent.
    """

    def post(self, request):
        data = _get_json_body(request)
        if data is None:
            return JsonResponse({"detail": "Invalid or missing JSON body"}, status=400)

        # Validate and build monthly_data
        monthly_raw = data.get("monthly_data") or data.get("monthly_data_list")
        if not monthly_raw or not isinstance(monthly_raw, list):
            return JsonResponse(
                {"detail": "monthly_data must be an array of 12 monthly entries"},
                status=400,
            )
        if len(monthly_raw) != 12:
            return JsonResponse(
                {"detail": "monthly_data must contain exactly 12 entries"},
                status=400,
            )

        monthly_data = []
        for i, m in enumerate(monthly_raw):
            if not isinstance(m, dict):
                return JsonResponse(
                    {"detail": f"monthly_data[{i}] must be an object with month, ghi, diffuse, temperature"},
                    status=400,
                )
            try:
                monthly_data.append(
                    MonthlySolarData(
                        month=str(m.get("month", "")) or f"Month{i+1}",
                        ghi=float(m["ghi"]),
                        diffuse=float(m["diffuse"]),
                        temperature=float(m["temperature"]),
                    )
                )
            except (KeyError, TypeError, ValueError) as e:
                return JsonResponse(
                    {"detail": f"monthly_data[{i}]: need ghi, diffuse, temperature. {e!s}"},
                    status=400,
                )

        def _f(key, default=None):
            v = data.get(key)
            if v is None:
                return default
            try:
                return float(v)
            except (TypeError, ValueError):
                return default

        latitude = _f("latitude")
        longitude = _f("longitude")
        tilt = _f("tilt", 25.0)
        azimuth = _f("azimuth", 0.0)
        albedo = _f("albedo", 0.2)
        dc_capacity_kwp = _f("dc_capacity_kwp")
        performance_ratio = _f("performance_ratio", 85.0)
        inverter_efficiency = _f("inverter_efficiency", 98.5)
        temp_coefficient = _f("temp_coefficient", -0.4)
        mismatch_loss = _f("mismatch_loss", 0.0)
        wiring_loss = _f("wiring_loss", 0.0)
        soiling_loss = _f("soiling_loss", 0.0)
        snow_loss = _f("snow_loss", 0.0)
        degradation = _f("degradation", 0.0)
        additional_loss = _f("additional_loss", 0.0)
        # Summary Output (Excel B48–B65): module/inverter for total modules, strings, area, AC
        module_wp = _f("module_wp", 0.0)
        module_length_m = _f("module_length_m", 0.0)
        module_width_m = _f("module_width_m", 0.0)
        modules_in_series_raw = data.get("modules_in_series")
        modules_in_series = 0
        if modules_in_series_raw is not None:
            try:
                modules_in_series = max(0, int(modules_in_series_raw))
            except (TypeError, ValueError):
                pass
        inverter_capacity_kw = _f("inverter_capacity_kw", 0.0)
        gcr_default_pct = _f("gcr_default_pct", 58.78)
        shadow_loss_pct = _f("shadow_loss_pct", 0.0)
        bifacial_gain_pct = _f("bifacial_gain_pct", 0.0)

        if dc_capacity_kwp is None or dc_capacity_kwp <= 0:
            return JsonResponse(
                {"detail": "dc_capacity_kwp must be a positive number"},
                status=400,
            )
        if latitude is None or longitude is None:
            return JsonResponse(
                {"detail": "latitude and longitude are required"},
                status=400,
            )
        if not (0 <= performance_ratio <= 100):
            return JsonResponse(
                {"detail": "performance_ratio must be between 0 and 100"},
                status=400,
            )
        for name, val in [
            ("mismatch_loss", mismatch_loss),
            ("wiring_loss", wiring_loss),
            ("soiling_loss", soiling_loss),
            ("snow_loss", snow_loss),
            ("degradation", degradation),
            ("additional_loss", additional_loss),
        ]:
            if val is not None and not (0 <= val <= 100):
                return JsonResponse(
                    {"detail": f"{name} must be between 0 and 100"},
                    status=400,
                )

        inp = ManualDCInput(
            latitude=latitude,
            longitude=longitude,
            tilt=tilt or 25.0,
            azimuth=azimuth or 0.0,
            albedo=albedo if albedo is not None else 0.2,
            dc_capacity_kwp=dc_capacity_kwp,
            performance_ratio=performance_ratio if performance_ratio is not None else 85.0,
            inverter_efficiency=inverter_efficiency if inverter_efficiency is not None else 98.5,
            temp_coefficient=temp_coefficient if temp_coefficient is not None else -0.4,
            mismatch_loss=mismatch_loss if mismatch_loss is not None else 0.0,
            wiring_loss=wiring_loss if wiring_loss is not None else 0.0,
            soiling_loss=soiling_loss if soiling_loss is not None else 0.0,
            snow_loss=snow_loss if snow_loss is not None else 0.0,
            degradation=degradation if degradation is not None else 0.0,
            additional_loss=additional_loss if additional_loss is not None else 0.0,
            monthly_data=monthly_data,
            module_wp=module_wp or 0.0,
            module_length_m=module_length_m or 0.0,
            module_width_m=module_width_m or 0.0,
            modules_in_series=modules_in_series,
            inverter_capacity_kw=inverter_capacity_kw or 0.0,
            gcr_default_pct=gcr_default_pct if gcr_default_pct is not None else 58.78,
            shadow_loss_pct=shadow_loss_pct if shadow_loss_pct is not None else 0.0,
            bifacial_gain_pct=bifacial_gain_pct if bifacial_gain_pct is not None else 0.0,
        )

        try:
            result = calculate_yield(inp)
        except Exception as e:
            logger.exception("Manual DC yield calculation failed")
            return JsonResponse(
                {"detail": f"Calculation failed: {e!s}"},
                status=500,
            )

        out: ManualDCOutput = result
        payload: dict[str, object] = {
            "monthly_energy_mwh": out.monthly_energy_mwh,
            "annual_energy_mwh": out.annual_energy_mwh,
            "specific_yield_kwh_per_kwp": out.specific_yield_kwh_per_kwp,
            "capacity_factor_percent": out.capacity_factor_percent,
        }
        # Summary Output Data (Excel image / B48–B65)
        payload["summary"] = {
            "total_modules": out.total_modules,
            "total_strings": out.total_strings,
            "pv_area_m2": out.pv_area_m2,
            "land_area_m2": out.land_area_m2,
            "land_area_ha": out.land_area_ha,
            "gcr_pct": out.gcr_pct,
            "shadow_loss_pct": out.shadow_loss_pct,
            "bifacial_gain_pct": out.bifacial_gain_pct,
            "temperature_loss_pct": out.temperature_loss_pct,
            "dc_capacity_kwp": dc_capacity_kwp,
            "ac_capacity_kw": out.ac_capacity_kw,
            "num_inverters": out.num_inverters,
            "dc_ac_ratio": out.dc_ac_ratio,
            "annual_energy_mwh": out.annual_energy_mwh,
            "specific_yield_kwh_per_kwp": out.specific_yield_kwh_per_kwp,
            "performance_ratio_pct": out.performance_ratio_pct,
        }

        # Optional grid connectivity (nearest transmission line & substation)
        grid_voltage_kv = None
        substation_name = None
        try:
            country_val = (data.get("grid_country") or data.get("country") or "").strip()
            country = str(country_val) if isinstance(country_val, str) else str(country_val)
            region_raw = data.get("grid_region") or data.get("region")
            region = None
            if isinstance(region_raw, str):
                region = region_raw.strip() or None
            elif region_raw is not None:
                region = str(region_raw).strip() or None

            if country:
                from engineering_tools.solar_services.grid_connectivity import (
                    analyze_grid_connectivity,
                )

                data_root = getattr(
                    settings,
                    "GRID_NETWORK_DATA_ROOT",
                    Path(settings.BASE_DIR) / "engineering_tools" / "grid_network",
                )
                if not isinstance(data_root, Path):
                    data_root = Path(data_root)

                plant_ac_mw = (out.ac_capacity_kw or 0.0) / 1000.0
                if plant_ac_mw > 0:
                    grid = analyze_grid_connectivity(
                        site_lat=latitude,
                        site_lon=longitude,
                        plant_ac_mw=plant_ac_mw,
                        country=country,
                        data_root=data_root,
                        region=region,
                        return_geometries=False,
                    )
                    grid_voltage_kv = grid.get("line_voltage_kv")
                    substation_name = grid.get("substation_name")
        except Exception as e:  # pragma: no cover - best-effort, non-fatal
            logger.warning("Grid connectivity analysis failed: %s", e)

        if grid_voltage_kv is not None:
            payload["nearest_tl_voltage_kv"] = grid_voltage_kv
        if substation_name:
            payload["substation_name"] = substation_name

        return JsonResponse(payload)
