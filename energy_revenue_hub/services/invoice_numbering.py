from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone as dt_timezone
from typing import Literal

from django.db import connection

from energy_revenue_hub.contract_profiles import normalize_contract_type_key
from energy_revenue_hub.models import BillingSession, GeneratedInvoice
from main.models import AssetList, assets_contracts

InvoiceLedger = Literal["production", "test"]

LIVE_SEQUENCE_NAME = "erh_output_invoice_seq"
TEST_SEQUENCE_NAME = "erh_output_invoice_seq_test"


def normalize_contract_key(value: str | None) -> str:
    return normalize_contract_type_key(value or "")


def parse_live_sequence_allowed() -> bool:
    return (os.getenv("ERH_INVOICE_LIVE_SEQUENCE_ALLOWED") or "").strip() == "true"


def parse_test_ledger_contract_types() -> set[str]:
    raw = (os.getenv("ERH_INVOICE_TEST_LEDGER_CONTRACT_TYPES") or "").strip()
    if not raw:
        return set()
    out: set[str] = set()
    for item in raw.split(","):
        key = normalize_contract_key(item)
        if key:
            out.add(key)
    return out


def parse_live_ledger_contract_types() -> set[str]:
    raw = (os.getenv("ERH_INVOICE_LIVE_LEDGER_CONTRACT_TYPES") or "").strip()
    if not raw:
        return set()
    out: set[str] = set()
    for item in raw.split(","):
        key = normalize_contract_key(item)
        if key:
            out.add(key)
    return out


def resolve_invoice_sequence_ledger(contract_type_key: str) -> InvoiceLedger:
    if not parse_live_sequence_allowed():
        return "test"
    live_allowlist = parse_live_ledger_contract_types()
    return "production" if contract_type_key in live_allowlist else "test"


def format_global_seq(n: int) -> str:
    if n < 1:
        raise ValueError("Sequence value must be >= 1")
    if n <= 999:
        return str(n).zfill(3)
    if n <= 9999:
        return str(n).zfill(4)
    if n <= 99999:
        return str(n).zfill(5)
    return str(n)


def next_sequence_value(ledger: InvoiceLedger) -> int:
    seq_name = LIVE_SEQUENCE_NAME if ledger == "production" else TEST_SEQUENCE_NAME
    with connection.cursor() as cursor:
        cursor.execute("SELECT nextval(%s)", [seq_name])
        row = cursor.fetchone()
    if not row:
        raise RuntimeError(f"Failed to allocate nextval from {seq_name}")
    return int(row[0])


def build_output_invoice_number(country: str, yyyymm: str, seq: int, ledger: InvoiceLedger) -> str:
    body = f"{country}-{yyyymm}-{format_global_seq(seq)}"
    return body if ledger == "production" else f"TEST-{body}"


def _parse_asset_timezone_offset(raw: str | None) -> dt_timezone | None:
    value = (raw or "").strip()
    if not value:
        return None
    if len(value) == 6 and value[0] in ("+", "-") and value[3] == ":":
        try:
            sign = 1 if value[0] == "+" else -1
            hh = int(value[1:3])
            mm = int(value[4:6])
            return dt_timezone(sign * timedelta(hours=hh, minutes=mm))
        except ValueError:
            return None
    return None


def compute_invoice_dates(asset_code: str, contract_type_key: str) -> tuple[str, str, list[str]]:
    warnings: list[str] = []
    invoice_date = ""
    due_date = ""

    asset = AssetList.objects.filter(asset_code=asset_code).only("timezone").first()
    tz = _parse_asset_timezone_offset(getattr(asset, "timezone", "") if asset else "")
    if tz is None:
        warnings.append("Missing or invalid asset timezone; invoice_date/payment_due_date left empty.")
        return invoice_date, due_date, warnings

    local_today = datetime.now(tz=tz).date()
    invoice_date = local_today.isoformat()

    due_days = 0
    contract_row = assets_contracts.objects.filter(
        asset_code=asset_code,
        contract_type=contract_type_key,
    ).first()
    if contract_row is None:
        warnings.append("No assets_contracts row matched asset_code+contract_type; using due_days=0.")
    else:
        raw_due_days = getattr(contract_row, "due_days", None)
        if raw_due_days in (None, ""):
            warnings.append("assets_contracts.due_days is empty; using due_days=0.")
        else:
            try:
                due_days = int(raw_due_days)
            except (TypeError, ValueError):
                warnings.append("assets_contracts.due_days is invalid; using due_days=0.")
                due_days = 0

    due_date = (local_today + timedelta(days=due_days)).isoformat()
    return invoice_date, due_date, warnings


def get_or_allocate_output_invoice_number(
    *,
    session: BillingSession,
    asset_code: str,
    country: str,
    yyyymm: str,
) -> tuple[str, InvoiceLedger, str]:
    contract_type_key = normalize_contract_key(session.billing_contract_type)
    if not contract_type_key:
        raise ValueError("billing_contract_type is required for invoice generation")

    target_ledger = resolve_invoice_sequence_ledger(contract_type_key)
    existing_rows = (
        GeneratedInvoice.objects.filter(
            billing_session=session,
            invoice_asset_code=asset_code,
            billing_contract_type=contract_type_key,
        )
        .exclude(output_invoice_number="")
        .order_by("generated_at")
    )
    for existing in existing_rows:
        if not existing.output_invoice_number:
            continue
        existing_ledger: InvoiceLedger = (
            "test" if str(existing.invoice_sequence_ledger or "").strip().lower() == "test" else "production"
        )
        if existing_ledger == target_ledger:
            return existing.output_invoice_number, existing_ledger, contract_type_key

    seq = next_sequence_value(target_ledger)
    number = build_output_invoice_number(country=country, yyyymm=yyyymm, seq=seq, ledger=target_ledger)
    return number, target_ledger, contract_type_key
