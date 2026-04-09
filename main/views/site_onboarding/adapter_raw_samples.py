"""
Return raw provider payloads for site-onboarding verification (per adapter).

Each selected asset can yield one or more files (e.g. Laplace: one CSV per dataset type).
"""
from __future__ import annotations

import csv
import io
import json
import re
from collections import defaultdict
from typing import Any, Dict, List

from django.contrib.auth.decorators import login_required
from django.http import JsonResponse

from accounts.decorators import role_required_api

from ..shared.utilities import ensure_unicode_string


def _safe_filename_part(s: str, max_len: int = 80) -> str:
    s = (s or "").strip()
    s = re.sub(r"[^\w\.\-]+", "_", s, flags=re.UNICODE).strip("_")
    return (s or "file")[:max_len]


@role_required_api(allowed_roles=["admin"])
@login_required
def api_adapter_fetch_raw_samples(request):
    """
    Fetch raw samples from the OEM API for manual verification.

    POST JSON:
      - adapter_id (required)
      - adapter_account_id (required for laplaceid; optional filter for fusion_solar / solargis)
      - asset_codes: non-empty list of asset_code strings
      - Laplace-only optional: groupid, unit, time, types, csv_api

    Returns:
      { success, files: [ { asset_code, filename, content, media_type, label? } ], errors: [...] }
    """
    if request.method != "POST":
        return JsonResponse({"error": "Only POST method allowed"}, status=405)
    try:
        import requests
        from requests.auth import HTTPDigestAuth

        from django.utils import timezone as dj_tz

        from data_collection.adapters.laplaceid import _build_api_root, _decode_csv_bytes
        from data_collection.models import AdapterAccount, AssetAdapterConfig

        data = json.loads(request.body or "{}")
        adapter_id = ensure_unicode_string(data.get("adapter_id") or "").strip()
        if not adapter_id:
            return JsonResponse({"success": False, "error": "adapter_id is required"}, status=400)

        adapter_account_id_raw = data.get("adapter_account_id")
        adapter_account_id = None
        try:
            if adapter_account_id_raw not in (None, ""):
                adapter_account_id = int(adapter_account_id_raw)
        except (TypeError, ValueError):
            return JsonResponse({"success": False, "error": "adapter_account_id must be an integer"}, status=400)

        asset_codes = data.get("asset_codes") or []
        if not isinstance(asset_codes, list):
            asset_codes = []
        asset_codes = [ensure_unicode_string(x).strip() for x in asset_codes if ensure_unicode_string(x).strip()]
        if not asset_codes:
            return JsonResponse({"success": False, "error": "asset_codes is required"}, status=400)

        files: List[Dict[str, Any]] = []
        errors: List[Dict[str, Any]] = []

        if adapter_id == "laplaceid":
            if adapter_account_id is None:
                return JsonResponse({"success": False, "error": "adapter_account_id is required for laplaceid"}, status=400)
            account = AdapterAccount.objects.filter(id=adapter_account_id, adapter_id="laplaceid").first()
            if not account:
                return JsonResponse({"success": False, "error": "Laplace adapter account not found"}, status=400)
            cfg = dict(account.config or {})
            api_base_url = ensure_unicode_string(cfg.get("api_base_url") or "").strip()
            username = ensure_unicode_string(cfg.get("username") or "").strip()
            password = ensure_unicode_string(cfg.get("password") or "").strip()
            if not api_base_url or not username or not password:
                return JsonResponse({"success": False, "error": "laplaceid account missing api_base_url, username or password"}, status=400)

            groupid = ensure_unicode_string(data.get("groupid") or cfg.get("groupid") or "1").strip() or "1"
            unit = ensure_unicode_string(data.get("unit") or "minute").strip() or "minute"
            csv_api = ensure_unicode_string(data.get("csv_api") or "hourly.php").strip() or "hourly.php"
            types = data.get("types") or ["pcs", "string", "battery", "approvedmeter", "wh"]
            if not isinstance(types, list):
                types = ["pcs", "string", "battery", "approvedmeter", "wh"]
            types = [ensure_unicode_string(t).strip() for t in types if ensure_unicode_string(t).strip()]
            if not types:
                types = ["pcs"]

            explicit_time = ensure_unicode_string(data.get("time") or "").strip()

            path_username = ensure_unicode_string(cfg.get("path_username") or username).strip() or username
            csv_root_suffix = ensure_unicode_string(cfg.get("csv_api_root_suffix") or "services/api/download").strip() or "services/api/download"
            csv_root = _build_api_root(api_base_url=api_base_url, path_username=path_username, api_root_suffix=csv_root_suffix)
            if not csv_root:
                return JsonResponse({"success": False, "error": "Invalid LaplaceID CSV API root URL"}, status=400)

            from data_collection.services.laplace_request_time import laplace_time_yyyymmddhh_previous_local_hour
            from main.models import AssetList

            def _laplace_fetch_types(time_param: str) -> Dict[str, str]:
                out: Dict[str, str] = {}
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
                            errors.append({"asset_code": "*", "detail": f"Laplace type={t}: HTTP {resp.status_code}"})
                            continue
                        out[t] = _decode_csv_bytes(resp.content)
                    except Exception as e:
                        errors.append({"asset_code": "*", "detail": f"Laplace type={t}: {e}"})
                return out

            if explicit_time or unit != "minute":
                time_param = explicit_time or dj_tz.now().strftime("%Y%m%d")
                type_bodies = _laplace_fetch_types(time_param)
                for ac in asset_codes:
                    for t, body in type_bodies.items():
                        fn = f"laplaceid_{_safe_filename_part(ac)}_{_safe_filename_part(t)}_{_safe_filename_part(time_param)}.csv"
                        files.append(
                            {
                                "asset_code": ac,
                                "filename": fn,
                                "content": "\ufeff" + body,
                                "media_type": "text/csv; charset=utf-8",
                                "label": f"Laplace CSV ({t}) time={time_param}",
                            }
                        )
            else:
                assets_tz = list(AssetList.objects.filter(asset_code__in=asset_codes).only("asset_code", "timezone"))
                tz_by_code = {a.asset_code: ensure_unicode_string(a.timezone or "").strip() for a in assets_tz}
                groups: Dict[str, List[str]] = defaultdict(list)
                for ac in asset_codes:
                    off = (tz_by_code.get(ac) or "").strip() or "__UTC__"
                    groups[off].append(ac)
                for off_key, ac_group in groups.items():
                    tz_arg = None if off_key == "__UTC__" else off_key
                    time_param = laplace_time_yyyymmddhh_previous_local_hour(asset_timezone_offset=tz_arg)
                    type_bodies = _laplace_fetch_types(time_param)
                    for ac in ac_group:
                        for t, body in type_bodies.items():
                            fn = f"laplaceid_{_safe_filename_part(ac)}_{_safe_filename_part(t)}_{_safe_filename_part(time_param)}.csv"
                            files.append(
                                {
                                    "asset_code": ac,
                                    "filename": fn,
                                    "content": "\ufeff" + body,
                                    "media_type": "text/csv; charset=utf-8",
                                    "label": f"Laplace CSV ({t}) time={time_param} tz={tz_arg or 'UTC'}",
                                }
                            )

        elif adapter_id == "fusion_solar":
            from main.models import AssetList

            from data_collection.adapters.fusion_solar import get_dev_list

            for ac in asset_codes:
                qs = AssetAdapterConfig.objects.select_related("adapter_account").filter(asset_code=ac, adapter_id="fusion_solar")
                if adapter_account_id is not None:
                    qs = qs.filter(adapter_account_id=adapter_account_id)
                rec = qs.first()
                if not rec:
                    errors.append({"asset_code": ac, "detail": "No Fusion Solar asset adapter config"})
                    continue
                config = rec.get_effective_config()
                base_url = ensure_unicode_string(config.get("api_base_url") or "").strip()
                username = ensure_unicode_string(config.get("username") or "").strip()
                password = ensure_unicode_string(config.get("password") or config.get("system_code") or "").strip()
                if not base_url or not username or not password:
                    errors.append({"asset_code": ac, "detail": "Fusion Solar config missing api_base_url, username or password"})
                    continue
                try:
                    asset = AssetList.objects.get(asset_code=ac)
                    plant_id = (getattr(asset, "provider_asset_id", None) or "").strip()
                except AssetList.DoesNotExist:
                    plant_id = ""
                if not plant_id:
                    plant_id = ensure_unicode_string(config.get("plant_id") or "").strip()
                if not plant_id:
                    errors.append({"asset_code": ac, "detail": "Missing provider_asset_id / plant_id"})
                    continue

                devs, err = get_dev_list(base_url, username, password, plant_id)
                if err:
                    errors.append({"asset_code": ac, "detail": err})
                    continue
                devs = [d for d in (devs or []) if isinstance(d, dict)]
                keys: set[str] = set()
                for d in devs:
                    keys.update(str(k) for k in d.keys())
                fieldnames = sorted(keys)
                buf = io.StringIO()
                writer = csv.DictWriter(buf, fieldnames=fieldnames, extrasaction="ignore")
                writer.writeheader()
                for d in devs:
                    row: Dict[str, Any] = {}
                    for k in fieldnames:
                        v = d.get(k)
                        if isinstance(v, (dict, list)):
                            row[k] = json.dumps(v, ensure_ascii=False)
                        elif v is None:
                            row[k] = ""
                        else:
                            row[k] = v
                    writer.writerow(row)
                files.append(
                    {
                        "asset_code": ac,
                        "filename": f"fusion_solar_{_safe_filename_part(ac)}_getDevList.csv",
                        "content": "\ufeff" + buf.getvalue(),
                        "media_type": "text/csv; charset=utf-8",
                        "label": "Fusion Solar getDevList (raw)",
                    }
                )

        elif adapter_id == "solargis":
            from data_collection.adapters.solargis import solargis_fetch_raw_data_delivery_xml

            for ac in asset_codes:
                qs = AssetAdapterConfig.objects.filter(asset_code=ac, adapter_id="solargis")
                if adapter_account_id is not None:
                    qs = qs.filter(adapter_account_id=adapter_account_id)
                rec = qs.first()
                if not rec:
                    errors.append({"asset_code": ac, "detail": "No SolarGIS asset adapter config"})
                    continue
                cfg = rec.get_effective_config()
                out = solargis_fetch_raw_data_delivery_xml(ac, cfg)
                if not out.get("success"):
                    errors.append({"asset_code": ac, "detail": out.get("error", "SolarGIS request failed")})
                    continue
                files.append(
                    {
                        "asset_code": ac,
                        "filename": f"solargis_{_safe_filename_part(ac)}_data_delivery.xml",
                        "content": out.get("content") or "",
                        "media_type": "application/xml; charset=utf-8",
                        "label": "SolarGIS dataDelivery (XML)",
                    }
                )

        else:
            for ac in asset_codes:
                buf = io.StringIO()
                w = csv.writer(buf)
                w.writerow(["adapter_id", "asset_code", "note"])
                w.writerow(
                    [
                        adapter_id,
                        ac,
                        "Raw provider sample export is not implemented for this adapter; use OEM portal or extend adapter_raw_samples.",
                    ]
                )
                files.append(
                    {
                        "asset_code": ac,
                        "filename": f"{_safe_filename_part(adapter_id)}_{_safe_filename_part(ac)}_raw_sample.csv",
                        "content": "\ufeff" + buf.getvalue(),
                        "media_type": "text/csv; charset=utf-8",
                        "label": "Placeholder",
                    }
                )

        return JsonResponse({"success": True, "files": files, "errors": errors, "adapter_id": adapter_id})
    except Exception as e:
        return JsonResponse({"success": False, "error": str(e)}, status=500)
