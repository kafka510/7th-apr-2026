"""
Build JSON snapshots for ``GeneratedInvoice.invoice_snapshot_json`` (frozen billing truth for PDFs).
"""

from __future__ import annotations

import math
from datetime import date, datetime, timedelta
from decimal import Decimal, ROUND_HALF_UP
from typing import Any

from django.utils import timezone

from energy_revenue_hub.contract_profiles import normalize_contract_type_key
from energy_revenue_hub.models import BillingLineItem, BillingSession, UtilityInvoice
from energy_revenue_hub.services.billing_cycle import warning_message_for_line
from main.models import assets_contracts, device_list


def _prim(v: Any) -> Any:
    if v is None:
        return None
    if isinstance(v, Decimal):
        return str(v)
    if isinstance(v, (date, datetime)):
        return v.isoformat()
    return v


def _fmt_date_ddmmyyyy(v: Any) -> str:
    if isinstance(v, datetime):
        return v.date().strftime("%d/%m/%Y")
    if isinstance(v, date):
        return v.strftime("%d/%m/%Y")
    s = str(v or "").strip()
    if not s:
        return ""
    try:
        return datetime.fromisoformat(s).strftime("%d/%m/%Y")
    except Exception:
        return s


def _fmt_date_d_mon_yyyy(v: Any) -> str:
    if isinstance(v, datetime):
        d = v.date()
    elif isinstance(v, date):
        d = v
    else:
        s = str(v or "").strip()
        if not s:
            return ""
        try:
            d = datetime.fromisoformat(s).date()
        except Exception:
            return s
    return d.strftime("%d %b %Y").lstrip("0")


def _plus_days(v: Any, days: int) -> date | None:
    if isinstance(v, datetime):
        return v.date() + timedelta(days=days)
    if isinstance(v, date):
        return v + timedelta(days=days)
    s = str(v or "").strip()
    if not s:
        return None
    try:
        return datetime.fromisoformat(s).date() + timedelta(days=days)
    except Exception:
        return None


def _q2(v: Any) -> Decimal:
    return _as_decimal(v).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def _q6(v: Any) -> Decimal:
    return _as_decimal(v).quantize(Decimal("0.000001"), rounding=ROUND_HALF_UP)


def _as_decimal(v: Any) -> Decimal:
    if v in (None, ""):
        return Decimal("0")
    try:
        return Decimal(str(v))
    except Exception:
        return Decimal("0")


def _meter_reading_source_display_value(v: Any) -> str:
    """
    Format meter reading source / device serial for PDFs without scientific notation.
    Large values from JSON (numbers) or float coercion often appear as 1.02E+11; this
    renders the full integer or normalized decimal. Alphanumeric codes pass through.
    """
    if v is None:
        return ""
    if isinstance(v, bool):
        return str(v)
    if isinstance(v, int):
        return str(v)
    if isinstance(v, Decimal):
        d = v
        if not d.is_finite():
            return ""
        if d == d.to_integral():
            return format(int(d), "d")
        s = format(d.normalize(), "f")
        return s.rstrip("0").rstrip(".") if "." in s else s
    if isinstance(v, float):
        if not math.isfinite(v):
            return ""
        d = Decimal(str(v))
        if d == d.to_integral():
            return format(int(d), "d")
        s = format(d.normalize(), "f")
        return s.rstrip("0").rstrip(".") if "." in s else s
    raw = str(v).strip()
    if not raw:
        return ""
    try:
        d = Decimal(raw)
    except Exception:
        return raw
    if not d.is_finite():
        return raw
    if d == d.to_integral():
        return format(int(d), "d")
    s = format(d.normalize(), "f")
    return s.rstrip("0").rstrip(".") if "." in s else s


def _safe_div(n: Decimal, d: Decimal) -> Decimal:
    if d == 0:
        return Decimal("0")
    return n / d


def _first_session_asset_code(session: BillingSession) -> str:
    for raw in session.asset_list or []:
        if isinstance(raw, dict):
            c = str(raw.get("asset_code") or raw.get("code") or "").strip()
        else:
            c = str(raw).strip()
        if c:
            return c
    return ""


def _primary_asset_code_from_line_items(line_items: list[BillingLineItem]) -> str:
    """Asset code for this PDF: line items for one generated invoice share one asset."""
    for li in line_items:
        c = str(li.asset_code or "").strip()
        if c:
            return c
    return ""


def _meter_reading_device_serial_for_asset(asset_code: str) -> str:
    """
    Meter reading source = device_serial of the device with device_type_id = 63 (meter type)
    and parent_code = asset_list.asset_code.
    """
    code = str(asset_code or "").strip()
    if not code:
        return ""
    row = (
        device_list.objects.filter(parent_code=code, device_type_id="63")
        .only("device_serial")
        .order_by("device_id")
        .first()
    )
    if not row:
        return ""
    return _meter_reading_source_display_value(getattr(row, "device_serial", "") or "").strip()


def _gst_rate_decimal_for_lines(
    session: BillingSession, line_items: list[BillingLineItem], extras: dict[str, Any]
) -> Decimal:
    raw = extras.get("gst_rate")
    if raw is not None and raw != "":
        try:
            return Decimal(str(raw))
        except Exception:
            pass
    code = _primary_asset_code_from_line_items(line_items)
    if not code:
        code = _first_session_asset_code(session)
    if code:
        row = assets_contracts.objects.filter(asset_code=code).first()
        if row is not None and getattr(row, "gst_rate", None) is not None:
            return Decimal(str(row.gst_rate))
    return Decimal("0.09")


def _contract_party_snapshot_for_lines(session: BillingSession, line_items: list[BillingLineItem]) -> dict[str, Any]:
    """Customer / bank / address from ``assets_contracts`` for the asset being invoiced (not the first session asset)."""
    code = _primary_asset_code_from_line_items(line_items)
    if not code:
        code = _first_session_asset_code(session)
    if not code:
        return {}
    row = assets_contracts.objects.filter(asset_code=code).first()
    if row is None:
        return {}
    return {
        "spv_name": row.spv_name or "",
        "sp_account_no": row.sp_account_no or "",
        "customer_asset_name": row.customer_asset_name or row.asset_name or "",
        "asset_address": (row.asset_address or "").strip(),
        "bank_name": getattr(row, "bank_name", None) or "",
        "bank_account_no": getattr(row, "bank_account_no", None) or "",
        "bank_swift": getattr(row, "bank_swift", None) or "",
        "bank_branch_code": getattr(row, "bank_branch_code", None) or "",
    }


def _utilities_for_invoice_snapshot(
    line_items: list[BillingLineItem],
    utility_rows: list[UtilityInvoice],
) -> list[UtilityInvoice]:
    """
    Utility invoice rows that belong to this asset invoice (same asset_code or account_key as lines).
    Avoids reusing another customer's utility row as the primary (u0) header source.
    """
    if not utility_rows:
        return []
    assets = {str(li.asset_code or "").strip() for li in line_items if str(li.asset_code or "").strip()}
    acct_keys: set[str] = set()
    for li in line_items:
        ex = li.line_extras_json or {}
        if isinstance(ex, dict):
            ak = str(ex.get("account_key") or "").strip()
            if ak:
                acct_keys.add(ak)
    matched: list[UtilityInvoice] = []
    for u in utility_rows:
        ua = str(u.asset_code or "").strip()
        un = str(u.account_no or "").strip()
        if assets and ua and ua in assets:
            matched.append(u)
        elif acct_keys and un and un in acct_keys:
            matched.append(u)
    if not matched:
        primary = _primary_asset_code_from_line_items(line_items)
        if primary:
            for u in utility_rows:
                if str(u.asset_code or "").strip() == primary:
                    matched.append(u)
    if not matched:
        return list(utility_rows)
    seen: set[str] = set()
    out: list[UtilityInvoice] = []
    for u in matched:
        sid = str(u.id)
        if sid in seen:
            continue
        seen.add(sid)
        out.append(u)
    return out


def _line_kind_safe(li: BillingLineItem) -> str:
    lk = getattr(li, "line_kind", None)
    if lk is None:
        return ""
    s = str(lk).strip()
    if s.startswith("<") and "Mock" in s:
        return ""
    return s


def _is_maiora_style(session: BillingSession, line_items: list[BillingLineItem]) -> bool:
    ct = normalize_contract_type_key(getattr(session, "billing_contract_type", None) or "")
    if ct == "sg_ppa_maiora":
        return True
    return any(_line_kind_safe(li) for li in line_items)


def _resolve_billing_period_span_for_pdf(
    session: BillingSession,
    line_items: list[BillingLineItem],
    utility_rows: list[UtilityInvoice],
) -> tuple[date | None, date | None]:
    """
    Full utility billing window for the PDF header (e.g. 14 Jan–13 Feb), not the session window.
    Uses utility rows matched by asset_code / line account_key; falls back to min/max line periods.
    """
    acct_keys: set[str] = set()
    assets: set[str] = set()
    for li in line_items:
        if li.asset_code:
            assets.add(str(li.asset_code).strip())
        ex = li.line_extras_json or {}
        if isinstance(ex, dict):
            ak = str(ex.get("account_key") or "").strip()
            if ak:
                acct_keys.add(ak)
    matched: list[tuple[date, date]] = []
    for u in utility_rows:
        ua = str(u.asset_code or "").strip()
        un = str(u.account_no or "").strip()
        ps = getattr(u, "period_start", None)
        pe = getattr(u, "period_end", None)
        if not ps or not pe:
            continue
        if ua and ua in assets:
            matched.append((ps, pe))
        elif un and un in acct_keys:
            matched.append((ps, pe))
    if matched:
        return min(p[0] for p in matched), max(p[1] for p in matched)
    ps = [li.period_start for li in line_items if getattr(li, "period_start", None)]
    pe = [li.period_end for li in line_items if getattr(li, "period_end", None)]
    if ps and pe:
        return min(ps), max(pe)
    return getattr(session, "start_date", None), getattr(session, "end_date", None)


def build_invoice_snapshot_json(
    session: BillingSession,
    line_items: list[BillingLineItem],
    *,
    version: int,
    utility_rows: list[UtilityInvoice] | None = None,
) -> dict[str, Any]:
    """Immutable-friendly dict for PDF and audit (amounts as strings)."""
    util_all = list(utility_rows or [])
    util = _utilities_for_invoice_snapshot(line_items, util_all)
    lines_out: list[dict[str, Any]] = []
    total_invoice = Decimal("0")
    total_export = Decimal("0")
    total_revenue = Decimal("0")
    as_of_pdf = timezone.now().date()
    bm_sess = getattr(session, "billing_month", None)
    ct_sess = getattr(session, "billing_contract_type", "") or ""
    for li in line_items:
        ik = _as_decimal(getattr(li, "invoice_kwh", None))
        ek = _as_decimal(getattr(li, "export_kwh", None))
        rv = _as_decimal(getattr(li, "revenue", None))
        total_invoice += ik
        total_export += ek
        total_revenue += rv
        period_start = getattr(li, "period_start", None)
        period_end = getattr(li, "period_end", None)
        invoice_kwh = _as_decimal(li.invoice_kwh)
        ppa_rate = _as_decimal(li.ppa_rate)
        revenue = _as_decimal(li.revenue)
        row = {
            "asset_code": li.asset_code or "",
            "asset_name": li.asset_name or "",
            "actual_kwh": _prim(li.actual_kwh),
            "export_kwh": _prim(li.export_kwh),
            "invoice_kwh": _prim(li.invoice_kwh),
            "ppa_rate": _prim(li.ppa_rate),
            "revenue": _prim(li.revenue),
            "sort_order": getattr(li, "sort_order", 0) or 0,
            "line_kind": (getattr(li, "line_kind", None) or "") or "",
            "segment_index": li.segment_index,
            "period_start": _prim(period_start),
            "period_end": _prim(period_end),
            "period_display": (
                f"{_fmt_date_ddmmyyyy(period_start)} - {_fmt_date_ddmmyyyy(period_end)}"
                if period_start and period_end
                else ""
            ),
            "leasing_year_label": (getattr(li, "leasing_year_label", None) or "") or "",
            "leasing_year_display_label": (getattr(li, "leasing_year_label", None) or "") or "",
            "amount_excl_gst": _prim(getattr(li, "amount_excl_gst", None)),
            "line_extras_json": getattr(li, "line_extras_json", None) or {},
            "invoice_kwh_display": str(_q2(invoice_kwh)),
            "ppa_rate_display": str(_q6(ppa_rate)),
            "revenue_display": str(_q2(revenue)),
            "billing_cycle_warning": (
                warning_message_for_line(
                    asset_code=li.asset_code or "",
                    session_contract_type=ct_sess,
                    billing_month_first=bm_sess,
                    as_of=as_of_pdf,
                )
                if str(_line_kind_safe(li) or "") == "consumption"
                else ""
            ),
        }
        lines_out.append(row)

    # Add combined year label at asset level when one bill spans multiple leasing years.
    by_asset_years: dict[str, list[str]] = {}
    for row in lines_out:
        if str(row.get("line_kind") or "") != "consumption":
            continue
        key = str(row.get("asset_code") or row.get("asset_name") or "").strip()
        label = str(row.get("leasing_year_label") or "").strip()
        if not key or not label:
            continue
        by_asset_years.setdefault(key, [])
        if label not in by_asset_years[key]:
            by_asset_years[key].append(label)
    combined_by_asset = {k: "/".join(v) for k, v in by_asset_years.items() if len(v) > 1}
    for row in lines_out:
        key = str(row.get("asset_code") or row.get("asset_name") or "").strip()
        row["combined_leasing_year_label"] = combined_by_asset.get(key, row.get("leasing_year_label") or "")

    asset_export_kwh = Decimal("0")
    asset_export_payment = Decimal("0")
    for li in line_items:
        if str(getattr(li, "line_kind", "") or "") == "export_excess":
            asset_export_kwh += _as_decimal(getattr(li, "invoice_kwh", None))
            asset_export_payment += _as_decimal(getattr(li, "revenue", None))

    utility_snapshots = []
    for u in util:
        utility_export_kwh = _as_decimal(getattr(u, "export_energy", None))
        utility_recurring = _as_decimal(getattr(u, "recurring_charges_dollars", None))
        # Allocate account-level utility values to this asset invoice using export-kWh share.
        share = _safe_div(asset_export_kwh, utility_export_kwh) if utility_export_kwh > 0 else Decimal("0")
        recurring_alloc = _q2(utility_recurring * share)
        export_cost_alloc = _q2(asset_export_payment + recurring_alloc)
        resulting_rate = _q6(_safe_div(asset_export_payment, asset_export_kwh))
        utility_snapshots.append(
            {
                "id": str(u.id),
                "account_no": u.account_no or "",
                "invoice_number": u.invoice_number or "",
                "invoice_date": _prim(getattr(u, "invoice_date", None)),
                "period_start": _prim(u.period_start),
                "period_end": _prim(u.period_end),
                "export_energy": str(_q2(asset_export_kwh)),
                "export_energy_cost": str(export_cost_alloc),
                "recurring_charges_dollars": str(recurring_alloc),
                "export_payment": str(_q2(asset_export_payment)),
                "net_unit_rate": str(resulting_rate),
                "unit_rate": _prim(getattr(u, "unit_rate", None)),
                "currency_code": u.currency_code or "",
                "export_energy_display": str(_q2(asset_export_kwh)),
                "export_energy_cost_display": str(export_cost_alloc),
                "recurring_charges_dollars_display": str(recurring_alloc),
                "export_payment_display": str(_q2(asset_export_payment)),
                "net_unit_rate_display": str(resulting_rate),
            }
        )

    extras_payload: dict = {}
    raw_extras = getattr(session, "billing_extras_json", None)
    if isinstance(raw_extras, dict):
        extras_payload = dict(raw_extras)

    asset_code = _primary_asset_code_from_line_items(line_items)
    auto_meter_serial = _meter_reading_device_serial_for_asset(asset_code)
    if str(extras_payload.get("meter_reading_source") or "").strip() == "" and auto_meter_serial:
        extras_payload = {**extras_payload, "meter_reading_source": auto_meter_serial}

    totals_out: dict[str, Any] = {
        "invoice_kwh": str(_q2(total_invoice)),
        "export_kwh": str(_q2(total_export)),
        "revenue": str(_q2(total_revenue)),
    }

    contract_party = _contract_party_snapshot_for_lines(session, line_items)

    if _is_maiora_style(session, line_items):
        subtotal = Decimal("0")
        for li in line_items:
            subtotal += _as_decimal(getattr(li, "revenue", None))
        gst_rate = _gst_rate_decimal_for_lines(session, line_items, extras_payload)
        subtotal = _q2(subtotal)
        gst_amount = _q2(subtotal * gst_rate)
        total_incl = _q2(subtotal + gst_amount)
        totals_out["subtotal_excl_gst"] = str(subtotal)
        totals_out["gst_rate"] = str(gst_rate)
        totals_out["gst_percent_display"] = str(_q2(gst_rate * Decimal("100")))
        totals_out["gst_amount"] = str(gst_amount)
        totals_out["total_incl_gst"] = str(total_incl)
        totals_out["current_charges_incl_gst"] = str(total_incl)

    u0 = utility_snapshots[0] if utility_snapshots else {}
    invoice_date_raw = u0.get("invoice_date") or _prim(session.end_date)
    payment_due_date = _plus_days(invoice_date_raw, 29)
    bill_start, bill_end = _resolve_billing_period_span_for_pdf(session, line_items, util)
    if not bill_start or not bill_end:
        bill_start = getattr(session, "start_date", None)
        bill_end = getattr(session, "end_date", None)
    consumption_rows = [r for r in lines_out if str(r.get("line_kind") or "") == "consumption"]
    leasing_year_display = "/".join(
        [str(r.get("leasing_year_label") or "").strip() for r in consumption_rows if str(r.get("leasing_year_label") or "").strip()]
    )
    mre_rate_display = "/".join(
        [str(r.get("ppa_rate_display") or "").strip() for r in consumption_rows if str(r.get("ppa_rate_display") or "").strip()]
    )
    solar_generation = _q2(sum((_as_decimal(r.get("actual_kwh")) for r in consumption_rows), Decimal("0")))
    resulting_consumption = _q2(sum((_as_decimal(r.get("invoice_kwh")) for r in consumption_rows), Decimal("0")))
    our_reference = str(extras_payload.get("contract_reference") or extras_payload.get("our_reference") or "").strip()

    out: dict[str, Any] = {
        "schema_version": 2,
        "billing_session_id": str(session.id),
        "country": session.country or "",
        "portfolio": session.portfolio or "",
        "billing_contract_type": getattr(session, "billing_contract_type", "") or "",
        "billing_month": _prim(getattr(session, "billing_month", None)),
        "session_label": getattr(session, "session_label", "") or "",
        "invoice_template_id": getattr(session, "invoice_template_id", "") or "",
        "session_period": {
            "start": _prim(session.start_date),
            "end": _prim(session.end_date),
        },
        "generated_version": version,
        "generated_at": timezone.now().isoformat(),
        "totals": totals_out,
        "lines": lines_out,
        "utility_invoices": utility_snapshots,
        "extras": extras_payload,
        "contract_party": contract_party,
        "header": {
            "invoice_no": str(extras_payload.get("maiora_invoice_number") or u0.get("invoice_number") or ""),
            "invoice_date": invoice_date_raw,
            "billing_period": f"{_prim(bill_start) or ''} to {_prim(bill_end) or ''}".strip(),
            "total_amount_payable": totals_out.get("current_charges_incl_gst") or totals_out.get("total_incl_gst") or totals_out.get("revenue"),
            "payment_due_date": _prim(payment_due_date),
            "payment_due_date_display": _fmt_date_d_mon_yyyy(payment_due_date),
            "invoice_date_display": _fmt_date_d_mon_yyyy(invoice_date_raw),
            "billing_period_display": (
                f"{_fmt_date_d_mon_yyyy(bill_start)} – {_fmt_date_d_mon_yyyy(bill_end)}"
                if bill_start and bill_end
                else f"{_prim(session.start_date) or ''} to {_prim(session.end_date) or ''}"
            ),
        },
        "our_reference": {
            "contract_reference": our_reference,
        },
        "summary_of_charges": {
            "current_charges_due_on": _fmt_date_d_mon_yyyy(payment_due_date),
            "current_charges_amount": totals_out.get("current_charges_incl_gst") or totals_out.get("total_incl_gst") or totals_out.get("revenue"),
            "total_amount_payable": totals_out.get("current_charges_incl_gst") or totals_out.get("total_incl_gst") or totals_out.get("revenue"),
        },
        "mre_summary": {
            "solar_leasing_year": leasing_year_display or "—",
            "mre_rate": mre_rate_display or "—",
            "solar_generation_kwh": str(solar_generation),
            "meter_reading_source": (
                _meter_reading_source_display_value(extras_payload.get("meter_reading_source")) or "—"
            ),
            "excess_electricity_export_kwh": str(_q2(asset_export_kwh)),
            "resulting_electricity_consumption_kwh": str(resulting_consumption),
        },
        "sp_summary": {
            "sp_invoice_no": str(u0.get("invoice_number") or ""),
            "electricity_account_no": str(u0.get("account_no") or ""),
            "exported_amount_kwh": str(u0.get("export_energy_display") or u0.get("export_energy") or "0.00"),
            "export_of_electricity_excl_gst": str(u0.get("export_energy_cost_display") or u0.get("export_energy_cost") or "0.00"),
            "recurring_charges_excl_gst": str(
                u0.get("recurring_charges_dollars_display") or u0.get("recurring_charges_dollars") or "0.00"
            ),
            "export_payment": str(u0.get("export_payment_display") or u0.get("export_payment") or "0.00"),
            "resulting_export_rate": str(u0.get("net_unit_rate_display") or u0.get("net_unit_rate") or "0.000000"),
        },
        "bank_details": {
            "account_name": contract_party.get("spv_name", ""),
            "account_number": contract_party.get("bank_account_no", ""),
            "bank_name": contract_party.get("bank_name", ""),
            "branch_code": contract_party.get("bank_branch_code", "") or contract_party.get("bank_swift", ""),
        },
        "display": {
            "show_draft_badge": str(session.status or "").upper() != "POSTED",
            "status_badge_text": "DRAFT" if str(session.status or "").upper() != "POSTED" else "POSTED",
        },
    }
    return out
