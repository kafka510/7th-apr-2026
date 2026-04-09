from __future__ import annotations

from datetime import date

from django.core.management.base import BaseCommand

from energy_revenue_hub.contract_profiles import normalize_contract_type_key
from energy_revenue_hub.models import BillingSession
from main.models import assets_contracts


def _first_day_of_month(d: date) -> date:
    return date(d.year, d.month, 1)


def _first_asset_code(asset_list: list) -> str:
    for raw in asset_list or []:
        if isinstance(raw, dict):
            code = str(raw.get("asset_code") or raw.get("code") or "").strip()
        else:
            code = str(raw).strip()
        if code:
            return code
    return ""


class Command(BaseCommand):
    help = "Backfill missing billing_month, billing_contract_type, and session_label for legacy BillingSession rows."

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Show what would be updated without saving changes.",
        )

    def handle(self, *args, **options):
        dry_run = bool(options.get("dry_run"))

        total = 0
        touched = 0
        updated_month = 0
        updated_contract = 0
        updated_label = 0

        qs = BillingSession.objects.all().order_by("created_at")
        for session in qs.iterator():
            total += 1
            fields: list[str] = []

            if not session.billing_month:
                basis = session.end_date or session.start_date or session.created_at.date()
                session.billing_month = _first_day_of_month(basis)
                fields.append("billing_month")
                updated_month += 1

            if not (session.billing_contract_type or "").strip():
                code = _first_asset_code(session.asset_list or [])
                if code:
                    row = assets_contracts.objects.filter(asset_code=code).first()
                    if row and (row.contract_type or "").strip():
                        session.billing_contract_type = normalize_contract_type_key(row.contract_type)
                        fields.append("billing_contract_type")
                        updated_contract += 1

            if not (session.session_label or "").strip() and (session.billing_contract_type or "").strip():
                bm = session.billing_month or _first_day_of_month(session.created_at.date())
                session.session_label = f"{session.billing_contract_type} · {bm.strftime('%b %Y')}"[:200]
                fields.append("session_label")
                updated_label += 1

            if fields:
                touched += 1
                if not dry_run:
                    session.save(update_fields=fields + ["updated_at"])

        mode = "DRY RUN" if dry_run else "UPDATED"
        self.stdout.write(self.style.SUCCESS(f"{mode}: inspected={total}, changed={touched}"))
        self.stdout.write(
            f"billing_month={updated_month}, billing_contract_type={updated_contract}, session_label={updated_label}"
        )

