from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("data_collection", "0005_seed_beat_schedule"),
    ]

    operations = [
        migrations.CreateModel(
            name="DeviceOperatingState",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "adapter_id",
                    models.CharField(
                        max_length=64,
                        help_text=(
                            "Adapter registry key (e.g. 'fusion_solar'). "
                            "Matches data_collection_asset_adapter_config.adapter_id."
                        ),
                    ),
                ),
                (
                    "device_type",
                    models.CharField(
                        max_length=80,
                        help_text="Device type within the adapter (e.g. inverter model/category).",
                    ),
                ),
                (
                    "state_value",
                    models.CharField(
                        max_length=64,
                        help_text="Raw OEM state value as string (e.g. '0', '512', 'RUN').",
                    ),
                ),
                (
                    "oem_state_label",
                    models.CharField(
                        max_length=255,
                        help_text="OEM-provided label/description for this state.",
                    ),
                ),
                (
                    "internal_state",
                    models.CharField(
                        max_length=64,
                        help_text=(
                            "Normalized internal state, e.g. NORMAL, SHUTDOWN, FAULT, COMM_LOST."
                        ),
                    ),
                ),
                (
                    "is_normal",
                    models.BooleanField(
                        default=False,
                        help_text="True when this state is considered normal operation (no loss).",
                    ),
                ),
                (
                    "fault_code",
                    models.CharField(
                        max_length=50,
                        blank=True,
                        null=True,
                        help_text="Optional internal fault or condition code for this state.",
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={
                "db_table": "device_operating_state",
                "verbose_name": "Device operating state",
                "verbose_name_plural": "Device operating states",
                "ordering": ["adapter_id", "device_type", "state_value"],
                "unique_together": {("adapter_id", "device_type", "state_value")},
            },
        ),
        migrations.AddIndex(
            model_name="deviceoperatingstate",
            index=models.Index(
                fields=["adapter_id", "device_type"],
                name="device_operating_state_adapter_device_idx",
            ),
        ),
        migrations.AddIndex(
            model_name="deviceoperatingstate",
            index=models.Index(
                fields=["internal_state"],
                name="device_operating_state_internal_idx",
            ),
        ),
    ]

