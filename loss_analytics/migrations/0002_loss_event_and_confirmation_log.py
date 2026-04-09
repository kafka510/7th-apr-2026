from django.db import migrations, models
from django.conf import settings


class Migration(migrations.Migration):

    dependencies = [
        ("loss_analytics", "0001_scheduled_job_run"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="LossEvent",
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
                    "asset_code",
                    models.CharField(
                        max_length=255,
                        help_text="Asset code for this inverter.",
                        db_index=True,
                    ),
                ),
                (
                    "device_id",
                    models.CharField(
                        max_length=255,
                        help_text="Inverter device_id.",
                        db_index=True,
                    ),
                ),
                (
                    "start_ts",
                    models.DateTimeField(
                        help_text="Start timestamp (UTC) for this loss event window.",
                        db_index=True,
                    ),
                ),
                (
                    "end_ts",
                    models.DateTimeField(
                        help_text="End timestamp (UTC) for this loss event window.",
                        db_index=True,
                    ),
                ),
                (
                    "internal_state",
                    models.CharField(
                        max_length=64,
                        blank=True,
                        null=True,
                        help_text=(
                            "Resolved internal_state during this window "
                            "(from device_operating_state), or null if unknown."
                        ),
                    ),
                ),
                (
                    "oem_state_label",
                    models.CharField(
                        max_length=255,
                        blank=True,
                        null=True,
                        help_text="OEM state label during this window, if available.",
                    ),
                ),
                (
                    "loss_kwh",
                    models.DecimalField(
                        max_digits=18,
                        decimal_places=6,
                        help_text="Integrated loss in kWh over [start_ts, end_ts].",
                    ),
                ),
                (
                    "is_legitimate",
                    models.BooleanField(
                        null=True,
                        blank=True,
                        help_text=(
                            "True = legitimate loss, False = false positive, "
                            "null = not reviewed yet."
                        ),
                    ),
                ),
                (
                    "confirmed_at",
                    models.DateTimeField(
                        null=True,
                        blank=True,
                        help_text=(
                            "When this event was last marked legitimate/false positive."
                        ),
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "confirmed_by",
                    models.ForeignKey(
                        on_delete=models.SET_NULL,
                        blank=True,
                        null=True,
                        to=settings.AUTH_USER_MODEL,
                        help_text=(
                            "User who last confirmed or changed "
                            "legitimacy of this event."
                        ),
                    ),
                ),
            ],
            options={
                "db_table": "loss_event",
                "verbose_name": "Loss event",
                "verbose_name_plural": "Loss events",
                "ordering": ["-start_ts"],
            },
        ),
        migrations.CreateModel(
            name="LossEventConfirmationLog",
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
                    "old_value",
                    models.BooleanField(
                        null=True,
                        blank=True,
                        help_text="Previous is_legitimate value (True / False / null).",
                    ),
                ),
                (
                    "new_value",
                    models.BooleanField(
                        null=True,
                        blank=True,
                        help_text="New is_legitimate value (True / False / null).",
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "loss_event",
                    models.ForeignKey(
                        on_delete=models.CASCADE,
                        related_name="confirmation_logs",
                        to="loss_analytics.lossevent",
                    ),
                ),
                (
                    "user",
                    models.ForeignKey(
                        on_delete=models.SET_NULL,
                        blank=True,
                        null=True,
                        to=settings.AUTH_USER_MODEL,
                        help_text="User who performed this change.",
                    ),
                ),
            ],
            options={
                "db_table": "loss_event_confirmation_log",
                "verbose_name": "Loss event confirmation log",
                "verbose_name_plural": "Loss event confirmation logs",
                "ordering": ["-created_at"],
            },
        ),
        migrations.AddIndex(
            model_name="lossevent",
            index=models.Index(
                fields=["asset_code", "start_ts"],
                name="loss_event_asset_start_idx",
            ),
        ),
        migrations.AddIndex(
            model_name="lossevent",
            index=models.Index(
                fields=["device_id", "start_ts"],
                name="loss_event_device_start_idx",
            ),
        ),
        migrations.AddIndex(
            model_name="lossevent",
            index=models.Index(
                fields=["is_legitimate"],
                name="loss_event_is_legit_idx",
            ),
        ),
    ]

