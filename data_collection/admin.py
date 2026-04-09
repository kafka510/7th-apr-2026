from django.contrib import admin

from data_collection.models import AdapterAccount, AssetAdapterConfig, DeviceOperatingState


@admin.register(AdapterAccount)
class AdapterAccountAdmin(admin.ModelAdmin):
    """
    Adapter account: one credential set per logical account. Many assets can link to the same account.
    """

    list_display = ("id", "adapter_id", "name", "enabled", "updated_at")
    list_filter = ("adapter_id", "enabled")
    search_fields = ("name", "adapter_id")
    readonly_fields = ("created_at", "updated_at")

    def has_module_permission(self, request):
        return request.user.is_superuser

    def has_add_permission(self, request):
        return request.user.is_superuser

    def has_change_permission(self, request, obj=None):
        return request.user.is_superuser

    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser


@admin.register(AssetAdapterConfig)
class AssetAdapterConfigAdmin(admin.ModelAdmin):
    """
    Asset adapter config: which adapter runs for each asset and at what interval.
    When adapter_account is set, credentials come from that account; config is per-asset overrides only.
    Restricted to superusers only because config can store API keys/credentials.
    """

    list_display = (
        "asset_code",
        "adapter_id",
        "adapter_account_display",
        "interval_display",
        "enabled",
        "updated_at",
    )
    list_filter = ("adapter_id", "acquisition_interval_minutes", "enabled")
    search_fields = ("asset_code", "adapter_id")
    readonly_fields = ("created_at", "updated_at")

    def adapter_account_display(self, obj):
        if obj.adapter_account_id:
            return f"#{obj.adapter_account_id}"
        return "—"

    adapter_account_display.short_description = "Account"

    def interval_display(self, obj):
        return f"{obj.acquisition_interval_minutes} min"

    interval_display.short_description = "Interval"

    def has_module_permission(self, request):
        return request.user.is_superuser

    def has_add_permission(self, request):
        return request.user.is_superuser

    def has_change_permission(self, request, obj=None):
        return request.user.is_superuser

    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser


@admin.register(DeviceOperatingState)
class DeviceOperatingStateAdmin(admin.ModelAdmin):
    """
    Device operating state mappings per adapter and device type.

    Restricted to superusers only, as state mappings affect loss categorization.
    """

    list_display = (
        "adapter_id",
        "device_type",
        "state_value",
        "oem_state_label",
        "internal_state",
        "is_normal",
        "updated_at",
    )
    list_filter = ("adapter_id", "device_type", "internal_state", "is_normal")
    search_fields = ("adapter_id", "device_type", "state_value", "oem_state_label", "internal_state")
    readonly_fields = ("created_at", "updated_at")

    def has_module_permission(self, request):
        return request.user.is_superuser

    def has_add_permission(self, request):
        return request.user.is_superuser

    def has_change_permission(self, request, obj=None):
        return request.user.is_superuser

    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser
