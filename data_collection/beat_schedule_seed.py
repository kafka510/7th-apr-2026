"""
Default Celery Beat schedule: seed data for django_celery_beat (DB as source of truth).

Used by:
- data_collection.0005_seed_beat_schedule migration (on migrate)
- manage.py migrate_beat_schedule_to_db (idempotent re-apply of defaults)

At runtime Beat reads only from the DB (DatabaseScheduler); no hardcoded CELERY_BEAT_SCHEDULE.
"""

import json
from typing import Any, Dict, List, Optional, Tuple

# Default periodic tasks to seed into django_celery_beat (DB-backed Beat schedule).
#
# IMPORTANT: Beat reads only from DB at runtime (DatabaseScheduler). If you add entries here,
# apply them by running: `python manage.py migrate_beat_schedule_to_db`
DEFAULT_BEAT_TASKS: List[Dict[str, Any]] = [
    {
        "name": "data-acquisition-30min",
        "task": "data_collection.tasks.run_data_acquisition_30min",
        "schedule_type": "interval",
        "interval_seconds": 1800,
        "queue": "data_acquisition",
        "kwargs": {"sun_hours_check": False},
        "args": [],
    },
    {
        "name": "data-acquisition-hourly",
        "task": "data_collection.tasks.run_data_acquisition_hourly",
        "schedule_type": "interval",
        "interval_seconds": 3600,
        "queue": "data_acquisition",
        "kwargs": {"sun_hours_check": False},
        "args": [],
    },
    {
        "name": "kpi.update_real_time_kpi_10min",
        "task": "main.tasks.update_real_time_kpi_10min",
        "schedule_type": "interval",
        "interval_seconds": 600,
        "queue": "default",
        "kwargs": {},
        "args": [],
    },
]


def seed_beat_schedule_to_db(
    timezone_name: str = "UTC",
    dry_run: bool = False,
) -> Tuple[int, int]:
    """
    Create or update default periodic tasks in django_celery_beat (idempotent).

    Returns (created_count, updated_count). If dry_run, no DB writes and returns (0, 0).
    """
    try:
        from django_celery_beat.models import CrontabSchedule, IntervalSchedule, PeriodicTask
    except Exception:
        raise RuntimeError(
            "django_celery_beat is not installed or not migrated. "
            "Add 'django_celery_beat' to INSTALLED_APPS and run: python manage.py migrate"
        )

    created = 0
    updated = 0

    for entry in DEFAULT_BEAT_TASKS:
        name = entry.get("name")
        task = entry.get("task")
        if not name or not task:
            continue
        queue = entry.get("queue")
        kwargs = entry.get("kwargs") or {}
        args = entry.get("args") or []

        interval_obj = None
        crontab_obj = None

        if entry.get("schedule_type") == "interval":
            sec = entry.get("interval_seconds")
            if sec and sec > 0 and not dry_run:
                interval_obj, _ = IntervalSchedule.objects.get_or_create(
                    every=sec,
                    period=IntervalSchedule.SECONDS,
                )
        elif entry.get("schedule_type") == "crontab":
            crontab_kw = entry.get("crontab") or {}
            if not dry_run:
                crontab_fields = dict(
                    minute=crontab_kw.get("minute", "*"),
                    hour=crontab_kw.get("hour", "*"),
                    day_of_week=crontab_kw.get("day_of_week", "*"),
                    day_of_month=crontab_kw.get("day_of_month", "*"),
                    month_of_year=crontab_kw.get("month_of_year", "*"),
                )
                if hasattr(CrontabSchedule, "timezone"):
                    crontab_fields["timezone"] = timezone_name
                crontab_obj, _ = CrontabSchedule.objects.get_or_create(**crontab_fields)

        if dry_run:
            continue

        payload = dict(
            task=task,
            enabled=True,
            one_off=False,
            args=json.dumps(args),
            kwargs=json.dumps(kwargs),
        )
        if queue:
            payload["queue"] = str(queue)
        if interval_obj is not None:
            payload["interval"] = interval_obj
            payload["crontab"] = None
        if crontab_obj is not None:
            payload["crontab"] = crontab_obj
            payload["interval"] = None

        obj, was_created = PeriodicTask.objects.update_or_create(
            name=name,
            defaults=payload,
        )
        if was_created:
            created += 1
        else:
            updated += 1

    return (created, updated)
