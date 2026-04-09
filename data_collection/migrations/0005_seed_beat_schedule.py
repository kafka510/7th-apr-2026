# Placeholder: Beat schedule is managed via Background Jobs page (DB). No seeding on migrate.
# To seed defaults once, run: python manage.py migrate_beat_schedule_to_db

from django.db import migrations


def noop_forward(apps, schema_editor):
    # Schedules are managed in the DB via Background Jobs; do not seed here.
    pass


def noop_reverse(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("data_collection", "0004_staging_timeseries_and_index"),
        ("django_celery_beat", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(noop_forward, noop_reverse),
    ]
