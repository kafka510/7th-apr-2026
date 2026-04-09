"""
Verify that the data_collection app is installed and fully functional.

Run: python manage.py verify_data_collection

Checks: app in INSTALLED_APPS, models loadable, table exists, migrations applied,
admin registered, Celery task routes and Beat schedule, adapter registry.
"""
import sys

from django.apps import apps
from django.conf import settings
from django.core.management.base import BaseCommand
from django.db import connection


class Command(BaseCommand):
    help = "Verify data_collection app is installed and functional"

    def add_arguments(self, parser):
        parser.add_argument(
            "--quiet",
            action="store_true",
            help="Only print a single line (OK or FAIL).",
        )

    def _ok(self, msg, quiet):
        if not quiet:
            self.stdout.write(self.style.SUCCESS(f"  OK: {msg}"))

    def _fail(self, msg, quiet):
        if quiet:
            self.stdout.write("FAIL")
        else:
            self.stderr.write(self.style.ERROR(f"  FAIL: {msg}"))
        return False

    def handle(self, *args, **options):
        quiet = options["quiet"]
        errors = 0

        if not quiet:
            self.stdout.write("Verifying data_collection app...")

        # 1. App in INSTALLED_APPS
        has_app = any(
            app == "data_collection" or app == "data_collection.apps.DataCollectionConfig"
            for app in settings.INSTALLED_APPS
        )
        if not has_app:
            errors += 1
            self._fail("data_collection not in INSTALLED_APPS", quiet)
        else:
            self._ok("App in INSTALLED_APPS", quiet)

        # 2. App config loadable
        try:
            app_config = apps.get_app_config("data_collection")
        except LookupError as e:
            errors += 1
            self._fail(f"App config not found: {e}", quiet)
        else:
            self._ok(f"App config: {app_config.verbose_name}", quiet)

        # 3. Models loadable
        try:
            from data_collection.models import AssetAdapterConfig
        except Exception as e:
            errors += 1
            self._fail(f"Could not import models: {e}", quiet)
        else:
            self._ok("Models importable (AssetAdapterConfig)", quiet)

        # 4. Table exists
        try:
            with connection.cursor() as cursor:
                cursor.execute(
                    "SELECT 1 FROM data_collection_asset_adapter_config LIMIT 1"
                )
        except Exception as e:
            errors += 1
            self._fail(f"Table data_collection_asset_adapter_config missing or inaccessible: {e}", quiet)
        else:
            self._ok("Table data_collection_asset_adapter_config exists", quiet)

        # 5. Admin registered
        from django.contrib import admin
        if AssetAdapterConfig not in admin.site._registry:
            errors += 1
            self._fail("AssetAdapterConfig not registered in admin", quiet)
        else:
            self._ok("Admin registered for AssetAdapterConfig", quiet)

        # 6. Celery task routes: optional for acquisition (DB PeriodicTask.queue is source of truth)
        routes = getattr(settings, "CELERY_TASK_ROUTES", {}) or {}
        acq_tasks = (
            "data_collection.tasks.run_data_acquisition",
            "data_collection.tasks.run_data_acquisition_30min",
            "data_collection.tasks.run_data_acquisition_hourly",
        )
        configured_routes = [t for t in acq_tasks if routes.get(t, {}).get("queue")]
        bad_routes = [t for t in configured_routes if routes.get(t, {}).get("queue") != "data_acquisition"]
        if bad_routes:
            errors += 1
            self._fail(f"CELERY_TASK_ROUTES: if configured, expected data_acquisition queue for {bad_routes}", quiet)
        elif configured_routes:
            self._ok("CELERY_TASK_ROUTES: acquisition routes configured correctly", quiet)
        else:
            self._ok("CELERY_TASK_ROUTES: acquisition routes not configured (DB queue mode)", quiet)

        # 7. Beat schedule (source of truth: DB via django_celery_beat)
        beat_keys = ["data-acquisition-30min", "data-acquisition-hourly"]
        try:
            from django_celery_beat.models import PeriodicTask
            names = set(PeriodicTask.objects.filter(name__in=beat_keys).values_list("name", flat=True))
            missing = [k for k in beat_keys if k not in names]
            if missing:
                errors += 1
                self._fail(f"Beat schedule (DB) missing periodic tasks: {missing}", quiet)
            else:
                self._ok("Beat schedule (DB) has data_collection entries", quiet)
        except Exception as e:
            errors += 1
            self._fail(f"Beat schedule (DB) check failed: {e}", quiet)

        # 8. Tasks importable
        try:
            from data_collection.tasks import (
                run_data_acquisition,
                run_data_acquisition_30min,
                run_data_acquisition_hourly,
                send_acquisition_timeout_alert,
                run_solargis_daily_ingest,
                run_daily_loss_calculation,
            )
        except Exception as e:
            errors += 1
            self._fail(f"Could not import tasks: {e}", quiet)
        else:
            self._ok("Celery tasks importable", quiet)

        # 9. Adapter registry
        try:
            from data_collection.adapters import get_registered_ids, fetch_and_store
            ids = get_registered_ids()
            if "stub" not in ids:
                errors += 1
                self._fail("Stub adapter not registered", quiet)
            else:
                self._ok(f"Adapter registry has: {ids}", quiet)
            # Quick call to ensure fetch_and_store path works
            out = fetch_and_store("test_asset", "stub", {})
            if not out.get("success"):
                errors += 1
                self._fail(f"fetch_and_store(stub) returned: {out}", quiet)
            else:
                self._ok("fetch_and_store(stub) runs successfully", quiet)
        except Exception as e:
            errors += 1
            self._fail(f"Adapter registry / fetch_and_store: {e}", quiet)

        if errors:
            if quiet:
                self.stdout.write("FAIL")
            else:
                self.stderr.write(self.style.ERROR(f"\nVerification failed ({errors} check(s) failed)."))
            sys.exit(1)
        else:
            if quiet:
                self.stdout.write("OK")
            else:
                self.stdout.write(self.style.SUCCESS("\nAll checks passed. data_collection is installed and functional."))
