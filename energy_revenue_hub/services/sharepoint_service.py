from __future__ import annotations

import os
import re
import shutil
import urllib.error
import urllib.parse
import urllib.request
import json
import time
from datetime import date, datetime

from django.conf import settings


def _sanitize_component(value: str | None, default: str = "unknown") -> str:
    text = (value or "").strip()
    if not text:
        text = default
    text = re.sub(r"[^\w\-.]+", "_", text, flags=re.UNICODE)
    text = re.sub(r"_+", "_", text).strip("_")
    return text or default


def _billing_duration_segment(start_date: date | None, end_date: date | None) -> str:
    if not start_date or not end_date:
        today = date.today()
        return f"{today:%m-%d}_{today:%m-%d}"
    return f"{start_date:%m-%d}_{end_date:%m-%d}"


def get_sharepoint_mirror_root() -> str:
    configured = getattr(settings, "ERH_SHAREPOINT_MIRROR_ROOT", None)
    if configured:
        root = configured
    else:
        media_root = getattr(settings, "MEDIA_ROOT", os.path.join(settings.BASE_DIR, "media"))
        root = os.path.join(media_root, "sharepoint_mirror")
    os.makedirs(root, exist_ok=True)
    return root


def upload_file_to_sharepoint_mirror(local_path: str, remote_rel_path: str) -> dict[str, str]:
    root = get_sharepoint_mirror_root()
    normalized = remote_rel_path.replace("\\", "/").lstrip("/")
    destination = os.path.join(root, normalized.replace("/", os.sep))
    os.makedirs(os.path.dirname(destination), exist_ok=True)
    shutil.copy2(local_path, destination)
    return {
        "local_path": local_path,
        "sharepoint_remote_path": normalized,
        "mirror_absolute_path": destination,
        "upload_mode": "mirror",
    }


def _graph_enabled() -> bool:
    return getattr(settings, "ERH_SHAREPOINT_UPLOAD_MODE", "mirror") == "graph"


def _get_drive_id_for_path(remote_rel_path: str) -> str:
    is_generated = remote_rel_path.replace("\\", "/").startswith("PE_invoices/")
    if is_generated:
        return (
            getattr(settings, "ERH_SHAREPOINT_GENERATED_DRIVE_ID", "")
            or getattr(settings, "ERH_SHAREPOINT_DRIVE_ID", "")
        )
    return (
        getattr(settings, "ERH_SHAREPOINT_UTILITY_DRIVE_ID", "")
        or getattr(settings, "ERH_SHAREPOINT_DRIVE_ID", "")
    )


def _get_graph_access_token() -> str:
    tenant_id = getattr(settings, "ERH_SHAREPOINT_TENANT_ID", "")
    client_id = getattr(settings, "ERH_SHAREPOINT_CLIENT_ID", "")
    client_secret = getattr(settings, "ERH_SHAREPOINT_CLIENT_SECRET", "")
    if not (tenant_id and client_id and client_secret):
        raise RuntimeError("Missing SharePoint Graph credentials in environment.")

    token_url = f"https://login.microsoftonline.com/{tenant_id}/oauth2/v2.0/token"
    body = urllib.parse.urlencode(
        {
            "grant_type": "client_credentials",
            "client_id": client_id,
            "client_secret": client_secret,
            "scope": "https://graph.microsoft.com/.default",
        }
    ).encode("utf-8")
    req = urllib.request.Request(token_url, data=body, method="POST")
    req.add_header("Content-Type", "application/x-www-form-urlencoded")
    with urllib.request.urlopen(req, timeout=30) as resp:
        payload = json.loads(resp.read().decode("utf-8"))
    token = payload.get("access_token")
    if not token:
        raise RuntimeError("Could not obtain Graph access token.")
    return token


def _upload_file_to_sharepoint_graph(local_path: str, remote_rel_path: str) -> dict[str, str]:
    drive_id = _get_drive_id_for_path(remote_rel_path)
    if not drive_id:
        raise RuntimeError("Missing SharePoint drive id in environment.")

    access_token = _get_graph_access_token()
    normalized = remote_rel_path.replace("\\", "/").lstrip("/")
    encoded_rel = urllib.parse.quote(normalized, safe="/+._-")
    upload_url = f"https://graph.microsoft.com/v1.0/drives/{drive_id}/root:/{encoded_rel}:/content"
    with open(local_path, "rb") as fh:
        content = fh.read()

    payload: dict[str, object] | None = None
    max_attempts = 4
    for attempt in range(1, max_attempts + 1):
        req = urllib.request.Request(upload_url, data=content, method="PUT")
        req.add_header("Authorization", f"Bearer {access_token}")
        req.add_header("Content-Type", "application/pdf")
        try:
            with urllib.request.urlopen(req, timeout=60) as resp:
                payload = json.loads(resp.read().decode("utf-8"))
            break
        except urllib.error.HTTPError as exc:
            status = int(getattr(exc, "code", 0) or 0)
            detail = exc.read().decode("utf-8", errors="ignore")
            retryable = status == 429 or 500 <= status < 600
            if retryable and attempt < max_attempts:
                retry_after = exc.headers.get("Retry-After") if getattr(exc, "headers", None) else None
                try:
                    delay = float(retry_after) if retry_after else float(2 ** (attempt - 1))
                except Exception:
                    delay = float(2 ** (attempt - 1))
                time.sleep(max(0.5, min(delay, 15.0)))
                continue
            raise RuntimeError(f"Graph upload failed ({status}): {detail}") from exc
        except Exception as exc:
            if attempt < max_attempts:
                time.sleep(float(2 ** (attempt - 1)))
                continue
            raise RuntimeError(f"Graph upload failed: {exc}") from exc

    if payload is None:
        raise RuntimeError("Graph upload failed after retries.")

    return {
        "local_path": local_path,
        "sharepoint_remote_path": normalized,
        "upload_mode": "graph",
        "sharepoint_drive_id": drive_id,
        "sharepoint_item_id": str(payload.get("id", "")),
        "web_url": str(payload.get("webUrl", "")),
    }


def upload_file_to_sharepoint(local_path: str, remote_rel_path: str) -> dict[str, str]:
    if _graph_enabled():
        return _upload_file_to_sharepoint_graph(local_path, remote_rel_path)
    return upload_file_to_sharepoint_mirror(local_path, remote_rel_path)


def download_file_from_sharepoint_graph(
    *,
    sharepoint_item_id: str | None = None,
    sharepoint_drive_id: str | None = None,
    remote_rel_path: str | None = None,
) -> bytes:
    drive_id = (sharepoint_drive_id or "").strip() or _get_drive_id_for_path(str(remote_rel_path or ""))
    item_id = (sharepoint_item_id or "").strip()
    rel = str(remote_rel_path or "").strip().replace("\\", "/").lstrip("/")
    if not drive_id:
        raise RuntimeError("Missing SharePoint drive id for download.")
    if not item_id and not rel:
        raise RuntimeError("Missing SharePoint item id/path for download.")

    access_token = _get_graph_access_token()
    if item_id:
        content_url = f"https://graph.microsoft.com/v1.0/drives/{drive_id}/items/{urllib.parse.quote(item_id, safe='')}/content"
    else:
        encoded_rel = urllib.parse.quote(rel, safe="/+._-")
        content_url = f"https://graph.microsoft.com/v1.0/drives/{drive_id}/root:/{encoded_rel}:/content"

    req = urllib.request.Request(content_url, method="GET")
    req.add_header("Authorization", f"Bearer {access_token}")
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            return resp.read()
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="ignore")
        raise RuntimeError(f"Graph download failed ({int(getattr(exc, 'code', 0) or 0)}): {detail}") from exc

def build_utility_invoice_remote_path(
    *,
    country: str | None,
    start_date: date | None,
    end_date: date | None,
    asset_name: str | None,
    invoice_number: str | None,
    file_name: str | None = None,
) -> str:
    year = str((start_date or end_date or date.today()).year)
    duration = _billing_duration_segment(start_date, end_date)
    asset_part = _sanitize_component(asset_name, "asset")
    inv_part = _sanitize_component(invoice_number, "invoice")
    ext = os.path.splitext(file_name or "")[1].lower() or ".pdf"
    fname = f"{asset_part}+{inv_part}{ext}"
    country_upper = (country or "SG").strip().upper()
    root = "SG_SP_invoices" if country_upper == "SG" else f"{country_upper}_SP_invoices"
    return f"{root}/{year}/{duration}/{fname}"


def build_generated_invoice_remote_path(
    *,
    country: str | None,
    start_date: date | None,
    end_date: date | None,
    asset_name: str | None,
    invoice_number: str | None,
    file_name: str | None = None,
) -> str:
    year = str((start_date or end_date or date.today()).year)
    duration = _billing_duration_segment(start_date, end_date)
    country_upper = _sanitize_component((country or "SG").upper(), "SG")
    asset_part = _sanitize_component(asset_name, "asset")
    inv_part = _sanitize_component(invoice_number, "invoice")
    ext = os.path.splitext(file_name or "")[1].lower() or ".pdf"
    raw_name = os.path.basename(str(file_name or "")).strip()
    if raw_name:
        stem, raw_ext = os.path.splitext(raw_name)
        ext = (raw_ext or ext).lower()
        # Preserve generated local filename (including _v{version}) for remote parity.
        fname = f"{_sanitize_component(stem, f'{asset_part}+{inv_part}')}{ext}"
    else:
        fname = f"{asset_part}+{inv_part}{ext}"
    return f"PE_invoices/{country_upper}/{year}/{duration}/{fname}"


def maybe_to_date(value: object) -> date | None:
    if isinstance(value, date):
        return value
    if isinstance(value, str):
        try:
            return datetime.fromisoformat(value).date()
        except ValueError:
            return None
    return None

