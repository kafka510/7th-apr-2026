# Generated for Phase 3 write policy: last written reading store

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("data_collection", "0003_alter_assetadapterconfig_acquisition_interval_minutes"),
    ]

    operations = [
        migrations.CreateModel(
            name="LastWrittenReading",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("asset_code", models.CharField(db_index=True, max_length=255)),
                ("adapter_id", models.CharField(db_index=True, max_length=64)),
                (
                    "series_key",
                    models.CharField(
                        default="default",
                        help_text="Logical series (e.g. metric name or 'default')",
                        max_length=255,
                    ),
                ),
                (
                    "interval_minutes",
                    models.PositiveSmallIntegerField(
                        default=5,
                        help_text="Acquisition interval (5, 30, 1440).",
                    ),
                ),
                (
                    "value",
                    models.CharField(
                        help_text="Last written value (string for comparison).",
                        max_length=512,
                    ),
                ),
                ("ts", models.DateTimeField(help_text="Timestamp of the last written reading.")),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={
                "verbose_name": "Last written reading",
                "verbose_name_plural": "Last written readings",
                "db_table": "data_collection_last_written_reading",
                "ordering": ["asset_code", "adapter_id", "series_key"],
                "unique_together": {("asset_code", "adapter_id", "series_key", "interval_minutes")},
            },
        ),
    ]
