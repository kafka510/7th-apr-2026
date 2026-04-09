"""LaplaceID adapter endpoints for site onboarding."""
import json

from django.contrib.auth.decorators import login_required
from django.http import JsonResponse

from accounts.decorators import role_required_api
from ..shared.utilities import ensure_unicode_string

from .fusion_solar import _fusion_solar_build_gii_device_rows


@role_required_api(allowed_roles=['admin'])
@login_required
def api_laplaceid_test_connection(request):
    """
    Test Laplace (laplaceid) adapter account by calling XML instant.php with unit=node.

    POST body: { "adapter_account_id": 123, "groupid": "1" (optional) }
    Returns { success, nodes: [ { node_id, name, setTime, tags } ] }.
    """
    if request.method != "POST":
        return JsonResponse({"error": "Only POST method allowed"}, status=405)
    try:
        from data_collection.models import AdapterAccount
        from data_collection.adapters.laplaceid import fetch_instant_xml

        data = json.loads(request.body or "{}")
        adapter_account_id = data.get("adapter_account_id")
        try:
            adapter_account_id_int = int(adapter_account_id)
        except Exception:
            return JsonResponse({"success": False, "error": "adapter_account_id is required"}, status=400)

        account = AdapterAccount.objects.filter(id=adapter_account_id_int, adapter_id="laplaceid").first()
        if not account:
            return JsonResponse({"success": False, "error": "Adapter account not found"}, status=400)

        cfg = dict(account.config or {})
        api_base_url = ensure_unicode_string(cfg.get("api_base_url") or "").strip()
        username = ensure_unicode_string(cfg.get("username") or "").strip()
        password = ensure_unicode_string(cfg.get("password") or "").strip()
        if not api_base_url or not username or not password:
            return JsonResponse(
                {"success": False, "error": "laplaceid adapter account config missing api_base_url, username or password"},
                status=400,
            )

        groupid = ensure_unicode_string(data.get("groupid") or cfg.get("groupid") or "1").strip() or "1"
        # Provider path convention: base + /{username}/services/api/generating/
        from data_collection.adapters.laplaceid import _build_api_root
        xml_root_suffix = ensure_unicode_string(cfg.get("xml_api_root_suffix") or "services/api/generating").strip() or "services/api/generating"
        path_username = ensure_unicode_string(cfg.get("path_username") or username).strip() or username
        base_url = _build_api_root(api_base_url=api_base_url, path_username=path_username, api_root_suffix=xml_root_suffix)
        if not base_url:
            return JsonResponse({"success": False, "error": "Invalid LaplaceID api_base_url/path_username/xml_api_root_suffix"}, status=400)
        meta, nodes, err = fetch_instant_xml(
            base_url=base_url,
            username=username,
            password=password,
            groupid=groupid,
            time_param="now",
            aliases=True,
            api_path="instant.php",
        )
        if err:
            return JsonResponse({"success": False, "error": err}, status=200)
        return JsonResponse({"success": True, "meta": meta, "nodes": nodes})
    except Exception as e:
        return JsonResponse({"success": False, "error": str(e)}, status=500)


@role_required_api(allowed_roles=['admin'])
@login_required
def api_laplaceid_fetch_nodes(request):
    """
    Fetch Laplace nodes for an asset/account (helper for device_list onboarding).

    POST body: { "asset_code": "JP-MINA", "adapter_account_id": 123, "groupid": "1" (optional) }
    Returns { success, nodes: [...] }.
    """
    if request.method != "POST":
        return JsonResponse({"error": "Only POST method allowed"}, status=405)
    try:
        from data_collection.models import AdapterAccount
        from data_collection.adapters.laplaceid import fetch_instant_xml

        data = json.loads(request.body or "{}")
        asset_code = ensure_unicode_string(data.get("asset_code") or "").strip()
        if not asset_code:
            return JsonResponse({"success": False, "error": "asset_code is required"}, status=400)
        adapter_account_id = data.get("adapter_account_id")
        try:
            adapter_account_id_int = int(adapter_account_id)
        except Exception:
            return JsonResponse({"success": False, "error": "adapter_account_id is required"}, status=400)

        account = AdapterAccount.objects.filter(id=adapter_account_id_int, adapter_id="laplaceid").first()
        if not account:
            return JsonResponse({"success": False, "error": "Adapter account not found"}, status=400)

        cfg = dict(account.config or {})
        api_base_url = ensure_unicode_string(cfg.get("api_base_url") or "").strip()
        username = ensure_unicode_string(cfg.get("username") or "").strip()
        password = ensure_unicode_string(cfg.get("password") or "").strip()
        if not api_base_url or not username or not password:
            return JsonResponse(
                {"success": False, "error": "laplaceid adapter account config missing api_base_url, username or password"},
                status=400,
            )

        groupid = ensure_unicode_string(data.get("groupid") or cfg.get("groupid") or "1").strip() or "1"
        from data_collection.adapters.laplaceid import _build_api_root
        xml_root_suffix = ensure_unicode_string(cfg.get("xml_api_root_suffix") or "services/api/generating").strip() or "services/api/generating"
        path_username = ensure_unicode_string(cfg.get("path_username") or username).strip() or username
        base_url = _build_api_root(api_base_url=api_base_url, path_username=path_username, api_root_suffix=xml_root_suffix)
        if not base_url:
            return JsonResponse({"success": False, "error": "Invalid LaplaceID api_base_url/path_username/xml_api_root_suffix"}, status=400)
        meta, nodes, err = fetch_instant_xml(
            base_url=base_url,
            username=username,
            password=password,
            groupid=groupid,
            time_param="now",
            aliases=True,
            api_path="instant.php",
        )
        if err:
            return JsonResponse({"success": False, "error": err}, status=200)
        return JsonResponse({"success": True, "asset_code": asset_code, "meta": meta, "nodes": nodes})
    except Exception as e:
        return JsonResponse({"success": False, "error": str(e)}, status=500)


@role_required_api(allowed_roles=['admin'])
@login_required
def api_laplaceid_discover_devices_from_csv(request):
    """
    Discover Laplace device codes by downloading a small CSV sample and parsing headers.

    Laplace CSV headers often contain device-scoped columns like:
      "{device_code} {oem_tag}"
    Example: "PCS1 交流電力(kW)" → device_code="PCS1"

    This endpoint does NOT require asset_list; it is intended for the onboarding wizard Devices tab.

    POST body:
      {
        "adapter_account_id": 123,
        "groupid": "1" (optional),
        "unit": "minute" (optional, default "minute"),
        "time": "YYYYMMDDHH" (optional, default current hour),
        "types": ["pcs","string","battery","approvedmeter"] (optional),
        "csv_api": "hourly.php" (optional, default "hourly.php"),
        "asset_code": "SITE1" (optional) — if set, default time= uses asset_list.timezone offset
      }

    Returns:
      {
        "success": true,
        "devices": [ { device_code, device_name, device_type, seen_in_types: [...] } ],
        "errors": [ { type, error } ],
        "sample": { unit, time, groupid, csv_api }
      }
    """
    if request.method != "POST":
        return JsonResponse({"error": "Only POST method allowed"}, status=405)
    try:
        from data_collection.models import AdapterAccount
        from data_collection.adapters.laplaceid import _build_api_root, _decode_csv_bytes
        import requests
        from requests.auth import HTTPDigestAuth
        import csv as _csv
        import io as _io
        from django.utils import timezone as dj_tz

        data = json.loads(request.body or "{}")
        adapter_account_id = data.get("adapter_account_id")
        try:
            adapter_account_id_int = int(adapter_account_id)
        except Exception:
            return JsonResponse({"success": False, "error": "adapter_account_id is required"}, status=400)

        account = AdapterAccount.objects.filter(id=adapter_account_id_int, adapter_id="laplaceid").first()
        if not account:
            return JsonResponse({"success": False, "error": "Adapter account not found"}, status=400)

        cfg = dict(account.config or {})
        api_base_url = ensure_unicode_string(cfg.get("api_base_url") or "").strip()
        username = ensure_unicode_string(cfg.get("username") or "").strip()
        password = ensure_unicode_string(cfg.get("password") or "").strip()
        if not api_base_url or not username or not password:
            return JsonResponse(
                {"success": False, "error": "laplaceid adapter account config missing api_base_url, username or password"},
                status=400,
            )

        groupid = ensure_unicode_string(data.get("groupid") or cfg.get("groupid") or "1").strip() or "1"
        unit = ensure_unicode_string(data.get("unit") or "minute").strip() or "minute"
        csv_api = ensure_unicode_string(data.get("csv_api") or "hourly.php").strip() or "hourly.php"
        types = data.get("types") or ["pcs", "string", "battery", "approvedmeter", "wh"]
        if not isinstance(types, list):
            types = ["pcs", "string", "battery", "approvedmeter", "wh"]
        types = [ensure_unicode_string(t).strip() for t in types if ensure_unicode_string(t).strip()]
        if not types:
            types = ["pcs"]

        # Default time: previous full local hour (YYYYMMDDHH) when unit=minute, using optional asset_list.timezone
        explicit_time_body = ensure_unicode_string(data.get("time") or "").strip()
        time_param = explicit_time_body
        asset_tz_for_time = None
        asset_code_opt = ensure_unicode_string(data.get("asset_code") or "").strip()
        if asset_code_opt:
            from main.models import AssetList

            row = AssetList.objects.filter(asset_code=asset_code_opt).only("timezone").first()
            if row:
                asset_tz_for_time = ensure_unicode_string(row.timezone or "").strip() or None
        if not time_param:
            if unit == "minute":
                from data_collection.services.laplace_request_time import laplace_time_yyyymmddhh_previous_local_hour

                time_param = laplace_time_yyyymmddhh_previous_local_hour(asset_timezone_offset=asset_tz_for_time)
            else:
                time_param = dj_tz.now().strftime("%Y%m%d")

        path_username = ensure_unicode_string(cfg.get("path_username") or username).strip() or username
        csv_root_suffix = ensure_unicode_string(cfg.get("csv_api_root_suffix") or "services/api/download").strip() or "services/api/download"
        csv_root = _build_api_root(api_base_url=api_base_url, path_username=path_username, api_root_suffix=csv_root_suffix)
        if not csv_root:
            return JsonResponse({"success": False, "error": "Invalid LaplaceID api_base_url/path_username/csv_api_root_suffix"}, status=400)

        device_map = {}  # device_code -> {device_code, device_name, device_type, seen_in_types:set}
        errors = []
        from data_collection.services.laplace_csv_headers import scan_laplace_csv_header_row, wst_column_device_slug

        # site-level / weather columns (no "{code} {tag}" pattern): header -> set of Laplace CSV types where seen
        site_header_types: dict[str, set[str]] = {}

        def _guess_device_type(code: str, dataset_type: str) -> str:
            c = (code or "").upper()
            if dataset_type == "string":
                return "string"
            if dataset_type == "battery":
                return "battery"
            if dataset_type == "approvedmeter":
                return "meter"
            if c.startswith("PCS"):
                return "inverter"
            return dataset_type or "device"

        for t in types:
            params = {
                "unit": unit,
                "groupid": groupid,
                "data": "measuringdata",
                "format": "csv",
                "time": time_param,
                "type": t,
            }
            url = f"{csv_root.rstrip('/')}/{csv_api.lstrip('/')}"
            try:
                resp = requests.get(url, params=params, auth=HTTPDigestAuth(username, password), timeout=60)
                if resp.status_code != 200:
                    errors.append({"type": t, "error": f"HTTP {resp.status_code}"})
                    continue
                text = _decode_csv_bytes(resp.content)
                reader = _csv.reader(_io.StringIO(text))
                header = next(reader, None)
                if not header:
                    errors.append({"type": t, "error": "Empty CSV"})
                    continue
                hdr = [ensure_unicode_string(c) for c in header]
                codes_this, site_this = scan_laplace_csv_header_row(hdr)
                for sh in site_this:
                    site_header_types.setdefault(sh, set()).add(t)
                for device_code in codes_this:
                    entry = device_map.get(device_code)
                    if not entry:
                        entry = {
                            "device_code": device_code,
                            "device_name": device_code,
                            "device_type": _guess_device_type(device_code, t),
                            "seen_in_types": set(),
                        }
                        device_map[device_code] = entry
                    entry["seen_in_types"].add(t)
            except Exception as e:
                errors.append({"type": t, "error": str(e)})
                continue

        # Weather / site metrics: one logical device per site-level column (mapping uses full header as device_type_id)
        for site_hdr, seen_ts in sorted(site_header_types.items(), key=lambda x: x[0]):
            slug = wst_column_device_slug(site_hdr)
            device_map[slug] = {
                "device_code": slug,
                "device_name": site_hdr,
                "device_type": "wst",
                "seen_in_types": set(seen_ts),
            }

        devices = []
        for dc, entry in sorted(device_map.items(), key=lambda x: x[0]):
            devices.append(
                {
                    "device_code": entry["device_code"],
                    "device_name": entry["device_name"],
                    "device_type": entry["device_type"],
                    "seen_in_types": sorted(list(entry["seen_in_types"])),
                }
            )

        return JsonResponse(
            {
                "success": True,
                "devices": devices,
                "errors": errors,
                "sample": {
                    "unit": unit,
                    "time": time_param,
                    "groupid": groupid,
                    "csv_api": csv_api,
                    "time_mode": "explicit" if explicit_time_body else "previous_local_hour",
                    "asset_code_for_timezone": asset_code_opt or None,
                    "effective_timezone_offset": (
                        (asset_tz_for_time or "UTC")
                        if (not explicit_time_body and unit == "minute")
                        else None
                    ),
                },
            }
        )
    except Exception as e:
        return JsonResponse({"success": False, "error": str(e)}, status=500)


@role_required_api(allowed_roles=['admin'])
@login_required
def api_laplaceid_fetch_devices_for_assets(request):
    """
    Build device_list-like rows for laplaceid by:
    - discovering device_codes from CSV headers (across types)
    - expanding them per selected asset_code (parent_code)
    - adding synthetic GII tilt devices for assets with tilt_configs (same convention as Fusion Solar)

    POST body:
      { "adapter_account_id": 123, "asset_codes": ["A1","A2"], ... optional discover params ... }

    Returns:
      { success: true, devices: [ {device_id, device_name, device_code, device_type_id, parent_code, device_type, country, device_source} ] }
    """
    if request.method != "POST":
        return JsonResponse({"error": "Only POST method allowed"}, status=405)
    try:
        data = json.loads(request.body or "{}")
        adapter_account_id = data.get("adapter_account_id")
        try:
            adapter_account_id_int = int(adapter_account_id)
        except Exception:
            return JsonResponse({"success": False, "error": "adapter_account_id is required"}, status=400)
        asset_codes = data.get("asset_codes") or []
        if not isinstance(asset_codes, list):
            asset_codes = []
        asset_codes = [ensure_unicode_string(x).strip() for x in asset_codes if ensure_unicode_string(x).strip()]
        if not asset_codes:
            return JsonResponse({"success": False, "error": "asset_codes is required"}, status=400)

        # Reuse the discover endpoint logic by calling the function directly.
        # We construct a minimal request-like call by reusing the same code path via HTTP would be wasteful.
        # Instead: call the discover function's core by invoking it with a synthesized request body.
        # Practical approach: call api_laplaceid_discover_devices_from_csv via its underlying logic is not factored,
        # so we re-implement a small internal call here by making a local request dict and calling requests.
        # (Keeps behavior consistent with wizard.)
        from data_collection.models import AdapterAccount
        from data_collection.adapters.laplaceid import _build_api_root, _decode_csv_bytes
        import requests
        from requests.auth import HTTPDigestAuth
        import csv as _csv
        import io as _io
        from django.utils import timezone as dj_tz

        account = AdapterAccount.objects.filter(id=adapter_account_id_int, adapter_id="laplaceid").first()
        if not account:
            return JsonResponse({"success": False, "error": "Adapter account not found"}, status=400)
        cfg = dict(account.config or {})
        api_base_url = ensure_unicode_string(cfg.get("api_base_url") or "").strip()
        username = ensure_unicode_string(cfg.get("username") or "").strip()
        password = ensure_unicode_string(cfg.get("password") or "").strip()
        if not api_base_url or not username or not password:
            return JsonResponse({"success": False, "error": "laplaceid account missing api_base_url/username/password"}, status=400)

        groupid = ensure_unicode_string(data.get("groupid") or cfg.get("groupid") or "1").strip() or "1"
        unit = ensure_unicode_string(data.get("unit") or "minute").strip() or "minute"
        csv_api = ensure_unicode_string(data.get("csv_api") or "hourly.php").strip() or "hourly.php"
        types = data.get("types") or ["pcs", "string", "battery", "approvedmeter", "wh"]
        if not isinstance(types, list):
            types = ["pcs", "string", "battery", "approvedmeter", "wh"]
        types = [ensure_unicode_string(t).strip() for t in types if ensure_unicode_string(t).strip()]
        if not types:
            types = ["pcs"]

        from main.models import AssetList

        asset_rows = list(AssetList.objects.filter(asset_code__in=asset_codes).only("asset_code", "country", "timezone"))
        asset_country_map: dict[str, str] = {
            a.asset_code: ensure_unicode_string(a.country or "").strip() for a in asset_rows
        }
        tz_map: dict[str, str] = {a.asset_code: ensure_unicode_string(a.timezone or "").strip() for a in asset_rows}

        explicit_time = ensure_unicode_string(data.get("time") or "").strip()
        time_param = explicit_time
        laplace_csv_meta: dict = {}
        if not time_param:
            if unit == "minute":
                from data_collection.services.laplace_request_time import laplace_time_yyyymmddhh_previous_local_hour

                primary_ac = sorted(asset_codes)[0]
                primary_tz = (tz_map.get(primary_ac) or "").strip() or None
                distinct_offsets = {(tz_map.get(ac) or "").strip() for ac in asset_codes if (tz_map.get(ac) or "").strip()}
                if len(distinct_offsets) > 1:
                    laplace_csv_meta["warning"] = (
                        "Multiple asset_list.timezone values among asset_codes; "
                        f"Laplace time= uses offset from first sorted asset_code={primary_ac}."
                    )
                time_param = laplace_time_yyyymmddhh_previous_local_hour(asset_timezone_offset=primary_tz)
                laplace_csv_meta["time"] = time_param
                laplace_csv_meta["timezone_offset"] = primary_tz or "UTC"
                laplace_csv_meta["timezone_source_asset_code"] = primary_ac
                laplace_csv_meta["time_mode"] = "previous_local_hour"
            else:
                time_param = dj_tz.now().strftime("%Y%m%d")
                laplace_csv_meta["time"] = time_param
                laplace_csv_meta["time_mode"] = "local_day_default"
        else:
            laplace_csv_meta["time"] = time_param
            laplace_csv_meta["time_mode"] = "explicit"

        path_username = ensure_unicode_string(cfg.get("path_username") or username).strip() or username
        csv_root_suffix = ensure_unicode_string(cfg.get("csv_api_root_suffix") or "services/api/download").strip() or "services/api/download"
        csv_root = _build_api_root(api_base_url=api_base_url, path_username=path_username, api_root_suffix=csv_root_suffix)
        if not csv_root:
            return JsonResponse({"success": False, "error": "Invalid LaplaceID base url configuration"}, status=400)

        from data_collection.services.laplace_csv_headers import scan_laplace_csv_header_row, wst_column_device_slug

        device_codes: dict[str, set[str]] = {}  # code -> seen_in_types
        site_header_types: dict[str, set[str]] = {}

        for t in types:
            params = {"unit": unit, "groupid": groupid, "data": "measuringdata", "format": "csv", "time": time_param, "type": t}
            url = f"{csv_root.rstrip('/')}/{csv_api.lstrip('/')}"
            resp = requests.get(url, params=params, auth=HTTPDigestAuth(username, password), timeout=60)
            if resp.status_code != 200:
                continue
            text = _decode_csv_bytes(resp.content)
            reader = _csv.reader(_io.StringIO(text))
            header = next(reader, None)
            if not header:
                continue
            hdr = [ensure_unicode_string(c) for c in header]
            codes_this, site_this = scan_laplace_csv_header_row(hdr)
            for sh in site_this:
                site_header_types.setdefault(sh, set()).add(t)
            for code in codes_this:
                device_codes.setdefault(code, set()).add(t)

        def _guess(code: str, seen: set[str]) -> str:
            c = (code or "").upper()
            if "string" in seen:
                return "string"
            if "battery" in seen:
                return "battery"
            if "approvedmeter" in seen:
                return "meter"
            if c.startswith("PCS"):
                return "inverter"
            return "device"

        # Build device rows per asset
        devices_out: list[dict] = []
        for ac in asset_codes:
            country = asset_country_map.get(ac, "")
            for code, seen in sorted(device_codes.items(), key=lambda x: x[0]):
                dtype = _guess(code, seen)
                # Make device_id unique per asset to avoid collisions across sites
                safe_asset = "".join(ch for ch in ac if ch.isalnum() or ch in "_-")
                safe_code = "".join(ch for ch in code if ch.isalnum() or ch in "_-")
                device_id = f"{safe_asset}_{safe_code}" if safe_asset and safe_code else f"{ac}_{code}"
                devices_out.append(
                    {
                        "device_id": device_id,
                        "device_name": code,
                        "device_code": code,
                        "device_type_id": dtype,
                        "parent_code": ac,
                        "device_type": dtype,
                        "country": country,
                        "device_source": "laplaceid",
                    }
                )
            for site_hdr, seen in sorted(site_header_types.items(), key=lambda x: x[0]):
                slug = wst_column_device_slug(site_hdr)
                safe_asset = "".join(ch for ch in ac if ch.isalnum() or ch in "_-")
                safe_slug = "".join(ch for ch in slug if ch.isalnum() or ch in "_-")
                device_id = f"{safe_asset}_{safe_slug}" if safe_asset and safe_slug else f"{ac}_{slug}"
                devices_out.append(
                    {
                        "device_id": device_id,
                        "device_name": site_hdr,
                        "device_code": slug,
                        "device_type_id": site_hdr,
                        "parent_code": ac,
                        "device_type": "wst",
                        "country": country,
                        "device_source": "laplaceid",
                    }
                )
            # Add GII synthetic devices if asset has tilt_configs
            try:
                for gii in _fusion_solar_build_gii_device_rows(ac):
                    gii = dict(gii)
                    gii["device_source"] = "gii"
                    devices_out.append(gii)
            except Exception:
                pass

        return JsonResponse({"success": True, "devices": devices_out, "laplace_csv": laplace_csv_meta})
    except Exception as e:
        return JsonResponse({"success": False, "error": str(e)}, status=500)


