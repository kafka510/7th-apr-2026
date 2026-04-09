"""
Models for data collection: adapter accounts and per-asset mapping.

AdapterAccount: one row per logical account (one set of credentials per adapter).
E.g. one Solargis account, two Fusion Solar accounts. Many assets can share one account.

AssetAdapterConfig: links an asset to an adapter account (or legacy: direct adapter + config).
When adapter_account_id is set, credentials come from the account; config is per-asset overrides
(e.g. plant_id). When adapter_account_id is null, config holds the full credentials (legacy).
acquisition_interval_minutes determines 5-min, 30-min, hourly, or daily schedule.
"""
from django.db import models


class AdapterAccount(models.Model):
    """
    One logical adapter account (one set of credentials). Many assets can use the same account.

    E.g. one Solargis account serving 30 sites; one Fusion Solar account serving 30 plants.
    Acquisition groups by account: Fusion Solar can batch multiple assets in one API call;
    Solargis still calls one site at a time but shares the same credential row.
    """
    adapter_id = models.CharField(
        max_length=64,
        db_index=True,
        help_text="Adapter registry key (e.g. 'solargis', 'fusion_solar')",
    )
    name = models.CharField(
        max_length=255,
        blank=True,
        help_text="Optional label (e.g. 'Solargis Production', 'Fusion Solar Account B')",
    )
    config = models.JSONField(
        default=dict,
        blank=True,
        help_text="Adapter-specific credentials and options (API URL, username, password, etc.). "
                  "May contain secrets; do not log or expose in APIs.",
    )
    enabled = models.BooleanField(
        default=True,
        help_text="If False, skip all assets linked to this account during acquisition",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "data_collection_adapter_account"
        ordering = ["adapter_id", "name"]
        verbose_name = "Adapter account"
        verbose_name_plural = "Adapter accounts"

    def __str__(self):
        return f"{self.adapter_id}: {self.name or 'Account #%s' % self.id}"


class AssetAdapterConfig(models.Model):
    """
    Links an asset (site) to an adapter account or to an adapter with inline config.

    When adapter_account_id is set: credentials come from AdapterAccount.config;
    config here is per-asset overrides (e.g. plant_id for Fusion Solar).
    When adapter_account_id is null (legacy): config holds the full credentials.
    """
    asset_code = models.CharField(
        max_length=255,
        db_index=True,
        help_text="Asset code (matches asset_list.asset_code)",
    )
    adapter_id = models.CharField(
        max_length=64,
        help_text="Adapter registry key (e.g. 'stub', 'sungrow', 'solargis')",
    )
    adapter_account = models.ForeignKey(
        "AdapterAccount",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="asset_configs",
        help_text="When set, credentials come from this account; config is per-asset overrides only.",
    )
    config = models.JSONField(
        default=dict,
        blank=True,
        help_text="When adapter_account is set: per-asset overrides (e.g. plant_id). "
                  "Otherwise: full adapter config (API URL, credentials, etc.). May contain secrets.",
    )
    acquisition_interval_minutes = models.PositiveSmallIntegerField(
        default=5,
        choices=[(5, "5 minutes"), (30, "30 minutes"), (60, "Hourly (60 min)"), (1440, "Daily (24h)")],
        help_text="Run this asset on 5-min, 30-min, hourly, or daily acquisition schedule",
    )
    enabled = models.BooleanField(
        default=True,
        help_text="If False, skip this asset during acquisition runs",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "data_collection_asset_adapter_config"
        ordering = ["asset_code"]
        verbose_name = "Asset adapter config"
        verbose_name_plural = "Asset adapter configs"
        constraints = [
            models.UniqueConstraint(fields=["asset_code", "adapter_id"], name="uq_asset_adapter_config_asset_code_adapter_id"),
        ]

    def __str__(self):
        return f"{self.asset_code} → {self.adapter_id} ({self.acquisition_interval_minutes} min)"

    # Keys that should prefer account over asset when account has a value (avoids wrong default URLs)
    _ACCOUNT_PREFERRED_KEYS = ("api_base_url", "username", "password")

    def get_effective_config(self):
        """
        Return config to use for this asset: account config merged with per-asset overrides.

        When adapter_account is set and loaded:
        - account.config is the base (typically holds credentials, URLs, etc.)
        - self.config contains per-asset overrides (e.g. plant_id, rate_limit)
        - For api_base_url, username, password: account value wins when non-empty, so
          asset-level defaults (e.g. intl.fusionsolar.huawei.com) do not override the
          correct account URL/creds.
        - For other keys: non-empty asset overrides are applied (e.g. plant_id, interval).

        When adapter_account is null or missing (legacy/deleted), self.config is the full config.
        """
        account = getattr(self, "adapter_account", None)
        if self.adapter_account_id and account is not None:
            base = dict(account.config or {})
            overrides = dict(self.config or {})
            for key, value in overrides.items():
                if value in (None, ""):
                    continue
                # Prefer account for credential/URL keys: only use asset value when account has none
                if key in self._ACCOUNT_PREFERRED_KEYS:
                    if (base.get(key) or "").strip():
                        continue  # keep account value
                base[key] = value
            return base
        return dict(self.config or {})


class LastWrittenReading(models.Model):
    """
    Last written reading per (asset_code, adapter_id, series_key, interval_minutes)
    for write policy: outside solar window we write only when value changed.

    Used by should_write_reading() to avoid duplicate idle readings at night.
    Adapters that use write policy call record_written_reading() after a successful write.

    Also used for Solargis daily API call count: sentinel rows with asset_code="_daily",
    adapter_id="solargis", series_key="api_calls_YYYY-MM-DD", interval_minutes=0 store
    the daily total in value (see data_collection.services.solargis_daily_calls).
    """
    asset_code = models.CharField(max_length=255, db_index=True)
    adapter_id = models.CharField(max_length=64, db_index=True)
    series_key = models.CharField(
        max_length=255,
        default="default",
        help_text="Logical series (e.g. metric name or 'default')",
    )
    interval_minutes = models.PositiveSmallIntegerField(
        default=5,
        help_text="Acquisition interval (5, 30, 1440).",
    )
    value = models.CharField(
        max_length=512,
        help_text="Last written value (string for comparison).",
    )
    ts = models.DateTimeField(help_text="Timestamp of the last written reading.")
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "data_collection_last_written_reading"
        unique_together = [["asset_code", "adapter_id", "series_key", "interval_minutes"]]
        ordering = ["asset_code", "adapter_id", "series_key"]
        verbose_name = "Last written reading"
        verbose_name_plural = "Last written readings"

    def __str__(self):
        return f"{self.asset_code}/{self.adapter_id}/{self.series_key} @ {self.ts}"


class DeviceOperatingState(models.Model):
    """
    Normalized mapping of OEM device operating states per adapter and device type.

    Used to resolve raw inverter state values (from timeseries_data.metric='inv_state')
    into internal_state values for loss categorization.
    """

    adapter_id = models.CharField(
        max_length=64,
        help_text="Adapter registry key (e.g. 'fusion_solar'). "
                  "Matches data_collection_asset_adapter_config.adapter_id.",
    )
    device_type = models.CharField(
        max_length=80,
        help_text="Device type within the adapter (e.g. inverter model/category).",
    )
    state_value = models.CharField(
        max_length=64,
        help_text="Raw OEM state value as string (e.g. '0', '512', 'RUN').",
    )
    oem_state_label = models.CharField(
        max_length=255,
        help_text="OEM-provided label/description for this state.",
    )
    internal_state = models.CharField(
        max_length=64,
        help_text="Normalized internal state, e.g. NORMAL, SHUTDOWN, FAULT, COMM_LOST.",
    )
    is_normal = models.BooleanField(
        default=False,
        help_text="True when this state is considered normal operation (no loss).",
    )
    fault_code = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        help_text="Optional internal fault or condition code for this state.",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "device_operating_state"
        verbose_name = "Device operating state"
        verbose_name_plural = "Device operating states"
        ordering = ["adapter_id", "device_type", "state_value"]
        unique_together = [["adapter_id", "device_type", "state_value"]]
        indexes = [
            models.Index(fields=["adapter_id", "device_type"]),
            models.Index(fields=["internal_state"]),
        ]

    def __str__(self) -> str:
        return f"{self.adapter_id}/{self.device_type} state={self.state_value} ({self.internal_state})"
