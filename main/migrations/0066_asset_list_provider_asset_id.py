# Add provider_asset_id to asset_list (unmanaged table → RunSQL).
# Stores API plant/station ID (e.g. Fusion Solar station code) for data collection adapters.

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("main", "0065_add_loss_calculation_enabled_to_device_list"),
    ]

    operations = [
        migrations.RunSQL(
            sql="""
                DO $$
                BEGIN
                    IF to_regclass('public.asset_list') IS NULL THEN
                        RETURN;
                    END IF;

                    IF NOT EXISTS (
                        SELECT 1 FROM information_schema.columns
                        WHERE table_name = 'asset_list' AND column_name = 'provider_asset_id'
                    ) THEN
                        ALTER TABLE asset_list ADD COLUMN provider_asset_id VARCHAR(255) NULL;
                    END IF;
                END $$;
            """,
            reverse_sql="""
                DO $$
                BEGIN
                    IF to_regclass('public.asset_list') IS NULL THEN
                        RETURN;
                    END IF;

                    ALTER TABLE asset_list DROP COLUMN IF EXISTS provider_asset_id;
                END $$;
            """,
        ),
    ]
