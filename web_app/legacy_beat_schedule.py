"""
Legacy Beat schedule definitions.

We keep these OUTSIDE settings.py so production config stays DB-backed (django-celery-beat)
without shipping a large in-settings schedule that can accidentally be merged and cause
duplicate triggers.

Used by:
  python manage.py migrate_beat_schedule_to_db
"""

"""
Legacy Beat schedule definitions.

This project uses DB-backed schedules (`django-celery-beat`). Keep this module
empty to avoid accidental in-code scheduling reintroduction.
"""

LEGACY_CELERY_BEAT_SCHEDULE = {}

