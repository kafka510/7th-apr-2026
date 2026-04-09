# Adapter-account–centric redesign: one credential row per account, assets link to account.
# Migration creates AdapterAccount, adds adapter_account_id to AssetAdapterConfig,
# and backfills one account per existing config so behavior is unchanged.

from django.db import migrations, models


def create_accounts_from_configs(apps, schema_editor):
    """For each AssetAdapterConfig, create an AdapterAccount and set adapter_account_id."""
    AssetAdapterConfig = apps.get_model("data_collection", "AssetAdapterConfig")
    AdapterAccount = apps.get_model("data_collection", "AdapterAccount")
    for row in AssetAdapterConfig.objects.all():
        account = AdapterAccount.objects.create(
            adapter_id=row.adapter_id,
            name=f"{row.asset_code} (migrated)",
            config=dict(row.config or {}),
            enabled=True,
        )
        row.adapter_account_id = account.id
        row.save(update_fields=["adapter_account_id"])


def noop_reverse(apps, schema_editor):
    """Reverse: clear adapter_account_id only; do not delete accounts (config still has copy)."""
    AssetAdapterConfig = apps.get_model("data_collection", "AssetAdapterConfig")
    AssetAdapterConfig.objects.all().update(adapter_account_id=None)


class Migration(migrations.Migration):

    dependencies = [
        ("data_collection", "0006_device_operating_state"),
    ]

    operations = [
        migrations.CreateModel(
            name="AdapterAccount",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                (
                    "adapter_id",
                    models.CharField(
                        db_index=True,
                        help_text="Adapter registry key (e.g. 'solargis', 'fusion_solar')",
                        max_length=64,
                    ),
                ),
                (
                    "name",
                    models.CharField(
                        blank=True,
                        help_text="Optional label (e.g. 'Solargis Production', 'Fusion Solar Account B')",
                        max_length=255,
                    ),
                ),
                (
                    "config",
                    models.JSONField(
                        blank=True,
                        default=dict,
                        help_text="Adapter-specific credentials and options (API URL, username, password, etc.). "
                        "May contain secrets; do not log or expose in APIs.",
                    ),
                ),
                (
                    "enabled",
                    models.BooleanField(
                        default=True,
                        help_text="If False, skip all assets linked to this account during acquisition",
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={
                "verbose_name": "Adapter account",
                "verbose_name_plural": "Adapter accounts",
                "db_table": "data_collection_adapter_account",
                "ordering": ["adapter_id", "name"],
            },
        ),
        migrations.AddField(
            model_name="assetadapterconfig",
            name="adapter_account",
            field=models.ForeignKey(
                blank=True,
                help_text="When set, credentials come from this account; config is per-asset overrides only.",
                null=True,
                on_delete=models.SET_NULL,
                related_name="asset_configs",
                to="data_collection.adapteraccount",
            ),
        ),
        migrations.RunPython(create_accounts_from_configs, noop_reverse),
    ]
