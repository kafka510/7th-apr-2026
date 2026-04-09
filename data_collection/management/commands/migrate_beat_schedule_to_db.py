"""
Ensure default Celery Beat schedule exists in the DB (django_celery_beat).

Beat schedule is the source of truth in the DB; no hardcoded CELERY_BEAT_SCHEDULE.
Defaults are seeded by data_collection.0005_seed_beat_schedule on migrate.
This command re-applies the same defaults (idempotent: update_or_create by task name).

Run:
  python manage.py migrate_beat_schedule_to_db

Optional:
  python manage.py migrate_beat_schedule_to_db --dry-run
"""

from django.conf import settings
from django.core.management.base import BaseCommand


def _get_timezone_name() -> str:
    return str(
        getattr(settings, "CELERY_TIMEZONE", None)
        or getattr(settings, "TIME_ZONE", None)
        or "UTC"
    )


class Command(BaseCommand):
    help = "Ensure default Beat schedule exists in DB (idempotent). Schedule is stored in DB only."

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Show what would be done, no DB writes.",
        )

    def handle(self, *args, **options):
        dry_run = bool(options.get("dry_run"))

        try:
            from data_collection.beat_schedule_seed import (
                DEFAULT_BEAT_TASKS,
                seed_beat_schedule_to_db,
            )
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Failed to load seed: {e}"))
            return

        tz = _get_timezone_name()
        self.stdout.write(f"Beat schedule source: DB (timezone={tz})")
        if dry_run:
            self.stdout.write(self.style.WARNING("DRY RUN: no database writes.\n"))
            for entry in DEFAULT_BEAT_TASKS:
                name = entry.get("name")
                task = entry.get("task")
                sched = entry.get("schedule_type")
                q = entry.get("queue") or "-"
                if sched == "interval":
                    self.stdout.write(f"  - {name}: interval {entry.get('interval_seconds')}s -> task={task} queue={q}")
                else:
                    self.stdout.write(f"  - {name}: crontab -> task={task} queue={q}")
            self.stdout.write(self.style.SUCCESS("\nDry run complete."))
            return

        created, updated = seed_beat_schedule_to_db(timezone_name=tz, dry_run=False)
        self.stdout.write(self.style.SUCCESS(f"Done. created={created}, updated={updated}"))
