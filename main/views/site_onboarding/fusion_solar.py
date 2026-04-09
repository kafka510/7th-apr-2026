"""Fusion Solar adapter endpoints for site onboarding."""
import csv
import io
import json
import logging
import re
from datetime import datetime

from django.contrib.auth.decorators import login_required
from django.http import HttpResponse, JsonResponse

from accounts.decorators import role_required_api
from ...models import AssetList
from ..shared.utilities import ensure_unicode_string

logger = logging.getLogger(__name__)


@role_required_api(allowed_roles=['admin'])
@login_required
def api_fusion_solar_fetch_plants(request):
    """
    Fetch Fusion Solar plant list from API. Admin only.
    POST body: { "adapter_id": "fusion_solar", "adapter_account_id": 123 }
    Returns { "success": true, "plants": [ { stationCode, stationName, capacity, ... } ] } or { "success": false, "error": "..." }.
    """
    if request.method != 'POST':
        return JsonResponse({'error': 'Only POST method allowed'}, status=405)
    try:
        from data_collection.adapters.fusion_solar import get_station_list

        from data_collection.models import AdapterAccount

        data = json.loads(request.body or '{}')
        adapter_id = ensure_unicode_string(data.get("adapter_id") or "fusion_solar").strip() or "fusion_solar"
        if adapter_id != "fusion_solar":
            return JsonResponse({"success": False, "error": f"Adapter not supported for site list: {adapter_id}"}, status=400)

        adapter_account_id = data.get('adapter_account_id')
        try:
            adapter_account_id_int = int(adapter_account_id)
        except Exception:
            return JsonResponse({'success': False, 'error': 'adapter_account_id is required'}, status=400)

        account = AdapterAccount.objects.filter(id=adapter_account_id_int, adapter_id='fusion_solar').first()
        if not account:
            return JsonResponse({'success': False, 'error': 'Adapter account not found'}, status=400)

        cfg = dict(account.config or {})
        base_url = ensure_unicode_string(cfg.get('api_base_url') or '').strip()
        username = ensure_unicode_string(cfg.get('username') or '').strip()
        password = ensure_unicode_string(cfg.get('password') or cfg.get('system_code') or '').strip()
        if not base_url or not username or not password:
            return JsonResponse({'success': False, 'error': 'Fusion Solar adapter account config missing api_base_url, username or password'}, status=400)
        plants, err = get_station_list(base_url, username, password)
        if err:
            return JsonResponse({'success': False, 'error': err}, status=200)
        return JsonResponse({'success': True, 'plants': plants or []})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


def _fusion_solar_api_device_to_device_list_row(api_dev: dict, asset_code: str, index: int) -> dict:
    """
    Map Fusion Solar API device dict to device_list-like row.
    API keys often: devId, devName, devTypeId, devTypeName, esnCode, etc.
    API may return devId/id/devTypeId as integers; normalise to string before .strip().
    We set: device_code = API devId (for API calls), device_id = unique id (asset_code + _ + devId or index),
    device_name, device_type_id, parent_code = asset_code, country = placeholder.
    """
    def _str(v):
        if v is None:
            return ''
        return str(v).strip()

    dev_id_api = _str(api_dev.get('devId') or api_dev.get('id')) or str(index)
    dev_name = _str(api_dev.get('devName') or api_dev.get('name') or api_dev.get('devTypeName')) or dev_id_api
    dev_type_id = _str(api_dev.get('devTypeId') or api_dev.get('devType')) or '1'
    # device_id should come directly from the OEM devId (sanitised), without prefixing asset_code.
    safe_id = "".join(c for c in str(dev_id_api) if c.isalnum() or c in '_-')
    device_id = safe_id or f"dev_{index}"
    # Map devTypeId to device_type string (lowercase, spaces -> underscores) as per user mapping.
    dev_type_map = {
        '1': 'string_inv',
        '2': 'smartlogger',
        '8': 'sts',
        '10': 'wst',
        '13': 'protocol_converter',
        '16': 'general_device',
        '17': 'grid_meter',
        '22': 'pid',
        '37': 'pinnet_data_logger',
        '38': 'residential_inverter',
        '39': 'battery',
        '40': 'backup_box',
        '41': 'ess',
        '45': 'plc',
        '46': 'optimizer',
        '47': 'emt',
        '62': 'dongle',
        '63': 'distributed_smartlogger',
        '70': 'safety_box',
    }
    device_type_str = dev_type_map.get(str(dev_type_id)) or (_str(api_dev.get('devTypeName')) or str(dev_type_id)).replace(' ', '_').lower()
    # Device make: Huawei for devTypeId 1 or 2
    device_make = 'huawei' if str(dev_type_id) in ('1', '2') else ''
    latitude = api_dev.get('latitude')
    longitude = api_dev.get('longitude')
    optimizer_no = api_dev.get('optimizerNumber') or api_dev.get('optimizerNo') or 0
    model = _str(api_dev.get('model'))
    esn_code = _str(api_dev.get('esnCode'))
    software_version = _str(api_dev.get('softwareVersion'))
    return {
        'device_id': device_id,
        'device_name': dev_name,
        'device_code': str(dev_id_api),
        'device_type_id': str(dev_type_id),
        'parent_code': asset_code,
        'device_type': device_type_str,
        'device_make': device_make,
        'device_model': model,
        'device_serial': esn_code,
        'optimizer_no': optimizer_no,
        'latitude': latitude,
        'longitude': longitude,
        'software_version': software_version,
        'country': '',
    }


def _extract_connected_strings_from_data_item_map(data_item_map: dict) -> list[int]:
    """
    Parse keys like pv1_i, pv2_i, ... from getDevRealKpi dataItemMap.
    A string is considered connected when value is not null.
    """
    if not isinstance(data_item_map, dict):
        return []
    connected: list[int] = []
    for k, v in data_item_map.items():
        if v is None:
            continue
        m = re.match(r"^pv(\d+)_i$", str(k))
        if not m:
            continue
        try:
            connected.append(int(m.group(1)))
        except (TypeError, ValueError):
            continue
    connected.sort()
    return connected


def _fusion_solar_string_device_rows(
    *,
    asset_code: str,
    inverter_device_name: str,
    inverter_device_id: str,
    inverter_device_code: str,
    connected_strings: list[int],
) -> list[dict]:
    """
    Build one synthetic string-device row per connected PV string index.
    """
    rows: list[dict] = []
    for s_no in connected_strings:
        sid = f"{inverter_device_id}_s{s_no}"
        string_name = f"{inverter_device_name}_string_{s_no}"
        rows.append(
            {
                "device_id": sid,
                "device_name": string_name,
                "device_code": f"pv{s_no}",
                "device_type_id": "string",
                "parent_code": asset_code,
                "device_type": "string",
                "country": "",
                "string_no": s_no,
                "connected_strings": str(s_no),
                "device_sub_group": inverter_device_id,
                "device_source": "",
            }
        )
    return rows


def _enrich_with_inverter_strings(
    *,
    base_url: str,
    username: str,
    password: str,
    devices: list[dict],
) -> list[dict]:
    """
    Query getDevRealKpi once for inverter devTypeId=1 and:
    - fill inverter.connected_strings with comma-separated connected indices
    - append synthetic string devices for each connected index
    """
    from data_collection.adapters.fusion_solar import get_dev_real_kpi, _get_or_refresh_token

    inverter_rows = [d for d in devices if str(d.get("device_type_id") or "").strip() == "1"]
    if not inverter_rows:
        return devices

    # Normalise and de-duplicate inverter devIds for OEM call.
    inverter_dev_ids: list[str] = []
    seen = set()
    for row in inverter_rows:
        dev_code = str(row.get("device_code") or "").strip()
        if dev_code and dev_code not in seen:
            seen.add(dev_code)
            inverter_dev_ids.append(dev_code)
    if not inverter_dev_ids:
        return devices

    token = _get_or_refresh_token(base_url, username, password)
    if not token:
        return devices

    out, status = get_dev_real_kpi(base_url, token, ",".join(inverter_dev_ids), "1")
    if status in (401, 403):
        token = _get_or_refresh_token(base_url, username, password, force_refresh=True)
        if token:
            out, status = get_dev_real_kpi(base_url, token, ",".join(inverter_dev_ids), "1")
    if not out or not out.get("success"):
        return devices

    data_rows = out.get("data") or []
    if not isinstance(data_rows, list):
        return devices

    by_dev_id = {}
    for item in data_rows:
        if not isinstance(item, dict):
            continue
        dev_id = str(item.get("devId") or "").strip()
        if dev_id:
            by_dev_id[dev_id] = item

    string_rows: list[dict] = []
    for inv in inverter_rows:
        inv_device_code = str(inv.get("device_code") or "").strip()
        item = by_dev_id.get(inv_device_code)
        if not item:
            continue
        connected = _extract_connected_strings_from_data_item_map(item.get("dataItemMap") or {})
        if not connected:
            continue
        inv["connected_strings"] = ",".join(str(x) for x in connected)
        inv["string_no"] = len(connected)
        string_rows.extend(
            _fusion_solar_string_device_rows(
                asset_code=str(inv.get("parent_code") or ""),
                inverter_device_name=str(inv.get("device_name") or "inverter"),
                inverter_device_id=str(inv.get("device_id") or ""),
                inverter_device_code=inv_device_code,
                connected_strings=connected,
            )
        )

    if not string_rows:
        return devices
    return [*devices, *string_rows]


def _fusion_solar_build_gii_device_rows(asset_code: str) -> list[dict]:
    """
    Build synthetic GII devices for an asset, without writing to device_list.

    Mirrors _ensure_gii_devices_in_device_list() convention:
    device_id = gii_device_id(asset_code, tilt_deg, azimuth_deg)
    device_name = "GII {tilt}° {azimuth}°"
    device_type_id = "gii", device_type = "GII"
    parent_code = asset_code
    """
    from main.models import AssetList
    from loss_analytics.pipeline.transposition import gii_device_id

    rows: list[dict] = []
    asset = AssetList.objects.filter(asset_code=asset_code).first()
    if not asset or not getattr(asset, "tilt_configs", None) or not isinstance(asset.tilt_configs, list):
        return rows
    country = (getattr(asset, "country", None) or "").strip() or "—"
    for cfg in asset.tilt_configs:
        if not isinstance(cfg, dict):
            continue
        try:
            tilt_deg = float(cfg.get("tilt_deg", 0))
            azimuth_deg = float(cfg.get("azimuth_deg", 0))
        except (TypeError, ValueError):
            continue
        dev_id = gii_device_id(asset_code, tilt_deg, azimuth_deg)
        device_name = f"GII {int(round(tilt_deg))}° {int(round(azimuth_deg))}°"
        code = dev_id[:40] if len(dev_id) > 40 else dev_id
        rows.append(
            {
                "device_id": dev_id,
                "device_name": device_name[:40],
                "device_code": code,
                "device_type_id": "gii",
                "device_type": "GII",
                "parent_code": asset_code[:40] if len(asset_code) > 40 else asset_code,
                "country": country[:40] if len(country) > 40 else country,
                "device_source": "gii",
                "device_serial": "",
                "device_model": "",
                "device_make": "",
                "latitude": 0.0,
                "longitude": 0.0,
                "optimizer_no": 0,
                "software_version": "",
            }
        )
    return rows


@role_required_api(allowed_roles=['admin'])
@login_required
def api_fusion_solar_fetch_devices(request):
    """
    Fetch Fusion Solar device list for a plant. Admin only.
    POST body: { "asset_code": "SITE1" } — uses Fusion Solar config and asset provider_asset_id for plant_id.
    Or: { "asset_code": "SITE1", "plant_id": "NE=123" } to override plant.
    Or: { "asset_code": "SITE1", "adapter_account_id": 5 } to force using a specific adapter account
    when multiple Fusion Solar configs exist for an asset.
    Returns { "success": true, "devices": [ device_list-like rows ] } or { "success": false, "error": "..." }.
    """
    if request.method != 'POST':
        return JsonResponse({'error': 'Only POST method allowed'}, status=405)
    try:
        from data_collection.adapters import fusion_solar as fusion_solar_adapter
        from data_collection.models import AssetAdapterConfig

        data = json.loads(request.body or '{}')
        asset_code = ensure_unicode_string(data.get('asset_code') or '').strip()
        # We intentionally ignore any external plant_id override in favour of provider_asset_id.
        plant_id_override = ''  # (data.get('plant_id') or '').strip()
        adapter_account_id_raw = data.get('adapter_account_id')
        adapter_account_id = None
        try:
            if adapter_account_id_raw not in (None, ''):
                adapter_account_id = int(adapter_account_id_raw)
        except (TypeError, ValueError):
            return JsonResponse({'success': False, 'error': 'adapter_account_id must be an integer'}, status=400)

        if not asset_code:
            return JsonResponse({'success': False, 'error': 'asset_code is required'}, status=400)

        config = None
        try:
            qs = AssetAdapterConfig.objects.select_related('adapter_account').filter(
                asset_code=asset_code,
                adapter_id='fusion_solar',
            )
            if adapter_account_id is not None:
                qs = qs.filter(adapter_account_id=adapter_account_id)
            rec = qs.get()
            # Debug raw configs before merging (with passwords scrubbed)
            raw_account_config = {}
            if getattr(rec, 'adapter_account', None) is not None:
                try:
                    raw_account_config = rec.adapter_account.config or {}
                except Exception:
                    raw_account_config = {}
            raw_asset_config = rec.config or {}
            def _scrub(cfg: dict) -> dict:
                if not isinstance(cfg, dict):
                    return {}
                scrubbed = dict(cfg)
                if 'password' in scrubbed:
                    scrubbed['password'] = '***'
                if 'system_code' in scrubbed:
                    scrubbed['system_code'] = '***'
                return scrubbed
            logger.info(
                "Fusion Solar configs for asset_code=%s adapter_account_id=%s raw_account_config=%s raw_asset_config=%s",
                asset_code,
                adapter_account_id,
                _scrub(raw_account_config),
                _scrub(raw_asset_config),
            )
            # Build effective config for this endpoint:
            # - Always take credentials (api_base_url / username / password) from the adapter account config
            #   when adapter_account_id is provided.
            # - Allow non-empty asset-level values to override non-credential fields (e.g. plant_id, rate limits).
            if adapter_account_id is not None:
                # Credentials pinned to adapter account
                config = dict(raw_account_config)
                for k, v in (raw_asset_config or {}).items():
                    if k in ('api_base_url', 'username', 'password', 'system_code'):
                        # Never let empty or conflicting asset-level values override account credentials
                        continue
                    if v not in (None, ''):
                        config[k] = v
            else:
                # Legacy behaviour when no adapter_account_id is passed: simple merge
                config = dict(raw_account_config)
                for k, v in (raw_asset_config or {}).items():
                    if v not in (None, ''):
                        config[k] = v

            logger.info(
                "Fusion Solar merged config for asset_code=%s adapter_account_id=%s merged_config=%s",
                asset_code,
                adapter_account_id,
                _scrub(config),
            )
        except AssetAdapterConfig.DoesNotExist:
            if adapter_account_id is not None:
                return JsonResponse(
                    {
                        'success': False,
                        'error': f'No Fusion Solar config for asset {asset_code} and adapter_account_id={adapter_account_id}',
                    },
                    status=400,
                )
            return JsonResponse(
                {'success': False, 'error': f'No Fusion Solar config for asset {asset_code}'},
                status=400,
            )

        base_url = ensure_unicode_string(config.get('api_base_url') or '').strip()
        username = ensure_unicode_string(config.get('username') or '').strip()
        password = ensure_unicode_string(config.get('password') or config.get('system_code') or '').strip()
        logger.info(
            "Fusion Solar final credentials for asset_code=%s adapter_account_id=%s base_url=%s username_present=%s password_present=%s",
            asset_code,
            adapter_account_id,
            base_url,
            bool(username),
            bool(password),
        )
        if not base_url or not username or not password:
            logger.warning(
                "Fusion Solar effective config missing creds for asset_code=%s adapter_account_id=%s config=%s",
                asset_code,
                adapter_account_id,
                {'api_base_url': base_url, 'username_present': bool(username), 'password_present': bool(password)},
            )
            return JsonResponse(
                {
                    'success': False,
                    'error': 'Fusion Solar config missing api_base_url, username or password',
                    'adapter_account_id': adapter_account_id,
                },
                status=400,
            )

        # Always use provider_asset_id from AssetList as plant_id for devices helper.
        try:
            asset = AssetList.objects.get(asset_code=asset_code)
            plant_id = (getattr(asset, 'provider_asset_id', None) or '').strip()
        except AssetList.DoesNotExist:
            plant_id = ''
        if not plant_id:
            return JsonResponse({'success': False, 'error': 'plant_id not in config and asset has no provider_asset_id'}, status=400)

        get_dev_list_detailed = getattr(fusion_solar_adapter, 'get_dev_list_detailed', None)
        if callable(get_dev_list_detailed):
            devs, err, diagnostics = get_dev_list_detailed(base_url, username, password, plant_id)
        else:
            # Backward-compatible fallback for environments still running older adapter module.
            get_dev_list = getattr(fusion_solar_adapter, 'get_dev_list')
            devs, err = get_dev_list(base_url, username, password, plant_id)
            diagnostics = {
                'fallback': 'get_dev_list_detailed not available in adapter module',
                'status': None,
                'provider_success': None,
                'provider_failCode': None,
                'provider_message': None,
                'station_code': plant_id,
            }
        if err:
            logger.error(
                "Fusion Solar get_dev_list error for asset_code=%s adapter_account_id=%s base_url=%s plant_id=%s error=%s diagnostics=%s",
                asset_code,
                adapter_account_id,
                base_url,
                plant_id,
                err,
                diagnostics,
            )
            return JsonResponse(
                {
                    'success': False,
                    'error': err,
                    'provider_diagnostics': diagnostics,
                    'asset_code': asset_code,
                    'plant_id': plant_id,
                },
                status=200,
            )
        devices = []
        for i, api_dev in enumerate(devs or []):
            if not isinstance(api_dev, dict):
                continue
            row = _fusion_solar_api_device_to_device_list_row(api_dev, asset_code, i)
            devices.append(row)
        # Enrich inverter rows from getDevRealKpi and append synthetic connected string rows.
        devices = _enrich_with_inverter_strings(
            base_url=base_url,
            username=username,
            password=password,
            devices=devices,
        )
        # Also include synthetic GII tilt devices for this asset (device_id convention matches acquisition path)
        devices.extend(_fusion_solar_build_gii_device_rows(asset_code))
        return JsonResponse({'success': True, 'devices': devices})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)

def _fusion_solar_station_to_asset_row(api_station: dict) -> dict:
    """
    Map Fusion Solar API station dict to asset_list-like row for CSV.
    API keys often: stationCode, stationName, capacity, longitude, latitude, etc.
    """
    code = (api_station.get('stationCode') or api_station.get('stationId') or '').strip()
    name = (api_station.get('stationName') or api_station.get('name') or '').strip() or code
    return {
        'asset_code': '',  # user fills or derives from stationCode
        'asset_name': name,
        'provider_asset_id': code,
        'capacity': api_station.get('capacity') or api_station.get('installCapacity') or '',
        'country': (api_station.get('country') or api_station.get('countryCode') or '').strip(),
        'latitude': api_station.get('latitude') or '',
        'longitude': api_station.get('longitude') or '',
        'asset_number': '',
        'pv_syst_pr': '',
        'tilt_configs': '',
    }


# asset_list CSV columns for Fusion Solar export (subset used in template)
FUSION_SOLAR_ASSET_CSV_HEADERS = [
    'asset_code', 'asset_name', 'provider_asset_id', 'capacity', 'country',
    'latitude', 'longitude', 'asset_number', 'pv_syst_pr', 'tilt_configs',
]
# device_list CSV columns for Fusion Solar export
FUSION_SOLAR_DEVICE_CSV_HEADERS = [
    'device_id', 'device_name', 'device_code', 'device_type_id', 'parent_code',
    'device_type', 'country',
]


@role_required_api(allowed_roles=['admin'])
@login_required
def api_fusion_solar_asset_csv(request):
    """
    Generate and download CSV with asset_list-shaped rows from Fusion Solar plants. Admin only.
    POST body: { "api_base_url", "username", "password" }.
    """
    if request.method != 'POST':
        return JsonResponse({'error': 'Only POST method allowed'}, status=405)
    try:
        from data_collection.adapters.fusion_solar import get_station_list

        data = json.loads(request.body or '{}')
        base_url = ensure_unicode_string(data.get('api_base_url') or '').strip()
        username = ensure_unicode_string(data.get('username') or '').strip()
        password = ensure_unicode_string(data.get('password') or '').strip()
        if not base_url or not username or not password:
            return JsonResponse({'error': 'api_base_url, username and password are required'}, status=400)
        plants, err = get_station_list(base_url, username, password)
        if err:
            return JsonResponse({'success': False, 'error': err}, status=200)
        buf = io.StringIO()
        writer = csv.DictWriter(buf, fieldnames=FUSION_SOLAR_ASSET_CSV_HEADERS, extrasaction='ignore')
        writer.writeheader()
        for st in (plants or []):
            if isinstance(st, dict):
                row = _fusion_solar_station_to_asset_row(st)
                writer.writerow(row)
        response = HttpResponse(content_type='text/csv; charset=utf-8')
        response['Content-Disposition'] = f'attachment; filename="fusion_solar_assets_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv"'
        response.write('\ufeff')
        response.write(buf.getvalue())
        return response
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@role_required_api(allowed_roles=['admin'])
@login_required
def api_fusion_solar_device_csv(request):
    """
    Generate and download CSV with device_list-shaped rows from Fusion Solar devices for one plant. Admin only.
    POST body: { "asset_code": "SITE1" } or { "asset_code", "plant_id" }. Uses Fusion Solar config for asset.
    """
    if request.method != 'POST':
        return JsonResponse({'error': 'Only POST method allowed'}, status=405)
    try:
        from data_collection.adapters.fusion_solar import get_dev_list
        from data_collection.models import AssetAdapterConfig

        data = json.loads(request.body or '{}')
        asset_code = ensure_unicode_string(data.get('asset_code') or '').strip()
        plant_id_override = (data.get('plant_id') or '').strip()
        if not asset_code:
            return JsonResponse({'error': 'asset_code is required'}, status=400)
        try:
            rec = AssetAdapterConfig.objects.select_related('adapter_account').get(asset_code=asset_code, adapter_id='fusion_solar')
            config = rec.get_effective_config()
        except AssetAdapterConfig.DoesNotExist:
            return JsonResponse({'error': f'No Fusion Solar config for asset {asset_code}'}, status=400)
        base_url = (config.get('api_base_url') or '').strip()
        username = (config.get('username') or '').strip()
        password = (config.get('password') or config.get('system_code') or '').strip()
        if not base_url or not username or not password:
            return JsonResponse({'error': 'Fusion Solar config missing api_base_url, username or password'}, status=400)
        plant_id = plant_id_override or (config.get('plant_id') or '').strip()
        if not plant_id:
            try:
                asset = AssetList.objects.get(asset_code=asset_code)
                plant_id = (getattr(asset, 'provider_asset_id', None) or '').strip()
            except AssetList.DoesNotExist:
                pass
        if not plant_id:
            return JsonResponse({'error': 'plant_id not in config and asset has no provider_asset_id'}, status=400)
        devs, err = get_dev_list(base_url, username, password, plant_id)
        if err:
            return JsonResponse({'success': False, 'error': err}, status=200)
        devices = []
        for i, api_dev in enumerate(devs or []):
            if isinstance(api_dev, dict):
                devices.append(_fusion_solar_api_device_to_device_list_row(api_dev, asset_code, i))
        buf = io.StringIO()
        writer = csv.DictWriter(buf, fieldnames=FUSION_SOLAR_DEVICE_CSV_HEADERS, extrasaction='ignore')
        writer.writeheader()
        for row in devices:
            writer.writerow(row)
        response = HttpResponse(content_type='text/csv; charset=utf-8')
        response['Content-Disposition'] = f'attachment; filename="fusion_solar_devices_{asset_code}_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv"'
        response.write('\ufeff')
        response.write(buf.getvalue())
        return response
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

