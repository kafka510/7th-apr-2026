"""
Seed AssetAdapterConfig from gis_list.csv for SolarGIS adapter.

Run: python manage.py seed_solargis_config path/to/gis_list.csv

Requires asset_list rows for each SiteId. api_url and api_key from env
SOLARGIS_API_URL and SOLARGIS_API_KEY (or defaults).
"""
import csv
import os

from django.core.management.base import BaseCommand
from django.db import transaction

from data_collection.models import AssetAdapterConfig
from main.models import AssetList


def _normalize_summarization(val):
    """Map gis_list summarization (e.g. min5, MIN_5) to SolarGIS format."""
    if not val or not str(val).strip():
        return "MIN_5"
    s = str(val).strip().upper().replace(" ", "_")
    if s.startswith("MIN"):
        return s if "_" in s else f"MIN_{s.replace('MIN', '')}"
    return "MIN_5"


def _parse_bool(val):
    if val is None:
        return False
    s = str(val).strip().lower()
    return s in ("1", "true", "yes", "y", "t")


class Command(BaseCommand):
    help = "Seed AssetAdapterConfig for SolarGIS from gis_list.csv"

    def add_arguments(self, parser):
        parser.add_argument(
            "csv_path",
            type=str,
            help="Path to gis_list.csv",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Print what would be created without writing.",
        )
        parser.add_argument(
            "--overwrite",
            action="store_true",
            help="Update existing configs instead of skipping.",
        )

    def handle(self, *args, **options):
        csv_path = options["csv_path"]
        dry_run = options["dry_run"]
        overwrite = options["overwrite"]
        api_url = os.environ.get(
            "SOLARGIS_API_URL",
            "https://solargis.info/ws/rest/datadelivery/request",
        )
        api_key = os.environ.get("SOLARGIS_API_KEY", "")

        if not os.path.isfile(csv_path):
            self.stderr.write(self.style.ERROR(f"File not found: {csv_path}"))
            return

        seen_assets = set(AssetList.objects.values_list("asset_code", flat=True))

        rows = []
        with open(csv_path, newline="", encoding="utf-8-sig", errors="replace") as f:
            reader = csv.DictReader(f)
            for r in reader:
                rows.append(r)

        created = 0
        updated = 0
        skipped = 0
        for row in rows:
            site_id = (row.get("SiteId") or row.get("siteId") or "").strip()
            if not site_id:
                continue
            if site_id not in seen_assets:
                self.stdout.write(self.style.WARNING(f"Skip {site_id}: not in asset_list"))
                skipped += 1
                continue

            summarization = _normalize_summarization(
                row.get("summarization") or row.get("Summarization", "")
            )
            processing_keys = (
                row.get("processingKeys") or row.get("processing_keys") or ""
            ).strip()
            if not processing_keys:
                processing_keys = "GHI DNI DIF GTI SE SA PVOUT TMOD TEMP WS WD RH CI_FLAG"
            time_stamp_type = (
                row.get("timeStampType") or row.get("time_stamp_type") or "CENTER"
            ).strip().upper()
            terrain_shading = _parse_bool(
                row.get("terrainShading") or row.get("terrain_shading")
            )
            try:
                tilt = float(row.get("tilt") or row.get("Tilt") or 0)
            except (ValueError, TypeError):
                tilt = 0
            try:
                azimuth = float(row.get("azimuth") or row.get("Azimuth") or 180)
            except (ValueError, TypeError):
                azimuth = 180

            config = {
                "api_url": api_url,
                "api_key": api_key,
                "summarization": summarization,
                "processing_keys": processing_keys,
                "terrain_shading": terrain_shading,
                "time_stamp_type": time_stamp_type,
                "tilt": tilt,
                "azimuth": azimuth,
            }

            existing = AssetAdapterConfig.objects.filter(asset_code=site_id).first()
            if existing:
                if overwrite:
                    if not dry_run:
                        existing.config = config
                        existing.adapter_id = "solargis"
                        existing.save()
                    updated += 1
                else:
                    skipped += 1
            else:
                if not dry_run:
                    with transaction.atomic():
                        AssetAdapterConfig.objects.create(
                            asset_code=site_id,
                            adapter_id="solargis",
                            config=config,
                            acquisition_interval_minutes=5,
                            enabled=True,
                        )
                created += 1

        msg = f"Created: {created}, Updated: {updated}, Skipped: {skipped}"
        if dry_run:
            self.stdout.write(self.style.WARNING(f"[DRY RUN] {msg}"))
        else:
            self.stdout.write(self.style.SUCCESS(msg))
