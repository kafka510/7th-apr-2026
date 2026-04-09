"""
Prune django-celery-beat PeriodicTasks to a known allowlist.

Use case: Keep only `celery.backend_cleanup` and remove everything else so the
DB schedule cannot trigger legacy jobs.

Run:
  python manage.py prune_beat_schedule

Dry run:
  python manage.py prune_beat_schedule --dry-run

Keep additional tasks (repeatable):
  python manage.py prune_beat_schedule --keep task_name --keep other_task
"""

from __future__ import annotations

from typing import List

from django.core.management.base import BaseCommand


DEFAULT_KEEP: List[str] = ["celery.backend_cleanup"]


class Command(BaseCommand):
    help = "Prune django-celery-beat PeriodicTasks to an allowlist (default: keep celery.backend_cleanup only)."

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Show what would be deleted, but do not modify the DB.",
        )
        parser.add_argument(
            "--keep",
            action="append",
            default=[],
            help="PeriodicTask.name to keep (repeatable). Default keep-list already includes celery.backend_cleanup.",
        )
        parser.add_argument(
            "--ensure-backend-cleanup",
            action="store_true",
            help="If celery.backend_cleanup is missing, create it (crontab 04:00 UTC).",
        )

    def handle(self, *args, **options):
        dry_run = bool(options.get("dry_run"))
        keep_extra = options.get("keep") or []
        ensure_backend_cleanup = bool(options.get("ensure_backend_cleanup"))

        keep_names = set(DEFAULT_KEEP)
        for n in keep_extra:
            n = (n or "").strip()
            if n:
                keep_names.add(n)

        from django_celery_beat.models import PeriodicTask, CrontabSchedule

        # Optional: ensure celery.backend_cleanup exists
        if ensure_backend_cleanup and "celery.backend_cleanup" in keep_names:
            cron_kw = {"minute": "0", "hour": "4", "day_of_week": "*", "day_of_month": "*", "month_of_year": "*"}
            if hasattr(CrontabSchedule, "timezone"):
                cron_kw["timezone"] = "UTC"
            cron, _ = CrontabSchedule.objects.get_or_create(**cron_kw)
            PeriodicTask.objects.get_or_create(
                name="celery.backend_cleanup",
                defaults={
                    "task": "celery.backend_cleanup",
                    "enabled": True,
                    "one_off": False,
                    "crontab": cron,
                    "args": "[]",
                    "kwargs": "{}",
                },
            )

        all_tasks = list(PeriodicTask.objects.all().order_by("name"))
        self.stdout.write(f"Found {len(all_tasks)} PeriodicTask(s) in DB.\n")
        for t in all_tasks:
            self.stdout.write(
                f"  - {t.name} -> task={t.task} enabled={t.enabled} "
                f"schedule={(str(t.interval) if t.interval_id else str(t.crontab) if t.crontab_id else str(t.solar) if t.solar_id else str(t.clocked) if t.clocked_id else 'none')}"
            )

        to_delete = [t for t in all_tasks if t.name not in keep_names]
        self.stdout.write(f"\nKeeping {len(keep_names)} name(s): {sorted(keep_names)}")
        self.stdout.write(f"Will delete {len(to_delete)} PeriodicTask(s).")

        if dry_run:
            self.stdout.write(self.style.WARNING("\nDRY RUN: no database changes made."))
            return

        if to_delete:
            PeriodicTask.objects.filter(name__in=[t.name for t in to_delete]).delete()

        remaining = list(PeriodicTask.objects.all().order_by("name").values_list("name", flat=True))
        self.stdout.write(self.style.SUCCESS(f"\nDone. Remaining PeriodicTask(s): {remaining}"))

