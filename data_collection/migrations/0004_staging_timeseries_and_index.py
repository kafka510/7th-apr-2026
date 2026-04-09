# Index for Solargis write path (DELETE by device_id + ts range).
# Staging uses a TEMP table per connection, created in the adapter (no migration).

from django.db import migrations


def create_index(apps, schema_editor):
    with schema_editor.connection.cursor() as cursor:
        # In clean test databases, this table may not exist yet (or is managed externally).
        # Skip index creation instead of failing migrations.
        cursor.execute("SELECT to_regclass('public.timeseries_data');")
        table_name = cursor.fetchone()[0]
        if not table_name:
            return

        cursor.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_timeseries_replace
            ON timeseries_data (device_id, metric, ts);
            """
        )


def drop_index(apps, schema_editor):
    with schema_editor.connection.cursor() as cursor:
        cursor.execute("DROP INDEX IF EXISTS idx_timeseries_replace;")


class Migration(migrations.Migration):

    dependencies = [
        ("data_collection", "0002_add_last_written_reading"),
    ]

    operations = [
        migrations.RunPython(create_index, drop_index),
    ]
