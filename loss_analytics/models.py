"""
Loss analytics models.

- ScheduledJobRun: generic DB-backed deduplication for scheduled jobs so that
  expensive tasks don't re-run repeatedly during long windows or after restarts.
"""
from django.db import models


class ScheduledJobRun(models.Model):
    """
    Generic record that a scheduled job was triggered for a given (job_name, run_date, scope_key).

    Intended use: when a Beat task runs frequently (e.g. hourly) but should only trigger once
    per asset/day (or per portfolio/day, etc.), write a row with a unique constraint so it is
    deduplicated at the database level (survives restarts).
    """
    job_name = models.CharField(max_length=100, db_index=True)
    run_date = models.DateField(null=True, blank=True, db_index=True)
    scope_key = models.CharField(max_length=255, db_index=True)
    triggered_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        db_table = "scheduled_job_run"
        ordering = ["-triggered_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["job_name", "run_date", "scope_key"],
                name="scheduled_job_run_uniq",
            )
        ]

    def __str__(self):
        return f"{self.job_name} {self.run_date} {self.scope_key}"


class LossEvent(models.Model):
    """
    Aggregated loss event for a single inverter over a continuous time window.

    Created by the loss pipeline when inverter state is non-normal or unknown.
    """

    asset_code = models.CharField(
        max_length=255,
        help_text="Asset code for this inverter.",
        db_index=True,
    )
    device_id = models.CharField(
        max_length=255,
        help_text="Inverter device_id.",
        db_index=True,
    )
    start_ts = models.DateTimeField(
        help_text="Start timestamp (UTC) for this loss event window.",
        db_index=True,
    )
    end_ts = models.DateTimeField(
        help_text="End timestamp (UTC) for this loss event window.",
        db_index=True,
    )
    internal_state = models.CharField(
        max_length=64,
        blank=True,
        null=True,
        help_text="Resolved internal_state during this window (from device_operating_state), or null if unknown.",
    )
    oem_state_label = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        help_text="OEM state label during this window, if available.",
    )
    loss_kwh = models.DecimalField(
        max_digits=18,
        decimal_places=6,
        help_text="Integrated loss in kWh over [start_ts, end_ts].",
    )
    is_legitimate = models.BooleanField(
        null=True,
        blank=True,
        help_text="True = legitimate loss, False = false positive, null = not reviewed yet.",
    )
    confirmed_by = models.ForeignKey(
        "auth.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        help_text="User who last confirmed or changed legitimacy of this event.",
    )
    confirmed_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When this event was last marked legitimate/false positive.",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "loss_event"
        verbose_name = "Loss event"
        verbose_name_plural = "Loss events"
        ordering = ["-start_ts"]
        indexes = [
            models.Index(fields=["asset_code", "start_ts"]),
            models.Index(fields=["device_id", "start_ts"]),
            models.Index(fields=["is_legitimate"]),
        ]

    def __str__(self) -> str:
        return f"{self.asset_code}/{self.device_id} {self.start_ts}–{self.end_ts} loss={self.loss_kwh}"


class LossEventConfirmationLog(models.Model):
    """
    Audit log of legitimacy changes for loss events.
    """

    loss_event = models.ForeignKey(
        LossEvent,
        on_delete=models.CASCADE,
        related_name="confirmation_logs",
    )
    user = models.ForeignKey(
        "auth.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        help_text="User who performed this change.",
    )
    old_value = models.BooleanField(
        null=True,
        blank=True,
        help_text="Previous is_legitimate value (True / False / null).",
    )
    new_value = models.BooleanField(
        null=True,
        blank=True,
        help_text="New is_legitimate value (True / False / null).",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "loss_event_confirmation_log"
        verbose_name = "Loss event confirmation log"
        verbose_name_plural = "Loss event confirmation logs"
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"LossEvent {self.loss_event_id}: {self.old_value} -> {self.new_value}"
