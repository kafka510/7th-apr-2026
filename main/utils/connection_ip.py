"""Connection / client IP extraction for audit-friendly activity logging."""

from __future__ import annotations

import ipaddress
from typing import Any, Dict, Optional


def _parse_ip(value: str) -> Optional[str]:
    if not value or not str(value).strip():
        return None
    try:
        return str(ipaddress.ip_address(value.strip()))
    except ValueError:
        return None


def extract_connection_ips(request) -> Dict[str, Any]:
    """
    Return peer (REMOTE_ADDR), raw X-Forwarded-For, and resolved client IP.

    client_ip: first hop in X-Forwarded-For when present and parseable; else
    REMOTE_ADDR if parseable; else 127.0.0.1.
    """
    meta = request.META
    peer_raw = (meta.get("REMOTE_ADDR") or "").strip()
    forwarded_for = (meta.get("HTTP_X_FORWARDED_FOR") or "").strip()

    client_ip: Optional[str] = None
    if forwarded_for:
        first_hop = forwarded_for.split(",")[0].strip()
        client_ip = _parse_ip(first_hop)
    if not client_ip:
        client_ip = _parse_ip(peer_raw)
    if not client_ip:
        client_ip = "127.0.0.1"

    return {
        "peer_ip": peer_raw[:45],
        "forwarded_for": forwarded_for,
        "client_ip": client_ip,
    }


def get_connection_ip_fields_for_log(request) -> Dict[str, Any]:
    """Kwargs for UserActivityLog.objects.create (includes legacy ip_address)."""
    d = extract_connection_ips(request)
    return {
        "peer_ip": d["peer_ip"],
        "forwarded_for": d["forwarded_for"],
        "client_ip": d["client_ip"],
        "ip_address": d["client_ip"],
    }
