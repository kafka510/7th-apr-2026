# Loss analytics admin (optional: task run log, defaults)
from django.contrib import admin

from loss_analytics.models import LossEvent, LossEventConfirmationLog


@admin.register(LossEvent)
class LossEventAdmin(admin.ModelAdmin):
    list_display = (
        "asset_code",
        "device_id",
        "start_ts",
        "end_ts",
        "internal_state",
        "loss_kwh",
        "is_legitimate",
        "confirmed_by",
        "confirmed_at",
    )
    list_filter = ("is_legitimate", "internal_state")
    search_fields = ("asset_code", "device_id")
    readonly_fields = ("created_at", "updated_at")


@admin.register(LossEventConfirmationLog)
class LossEventConfirmationLogAdmin(admin.ModelAdmin):
    list_display = (
        "loss_event",
        "user",
        "old_value",
        "new_value",
        "created_at",
    )
    list_filter = ("new_value",)
    search_fields = ("loss_event__asset_code", "loss_event__device_id", "user__username")
