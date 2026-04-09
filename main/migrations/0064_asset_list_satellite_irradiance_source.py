# Add satellite_irradiance_source_asset_code to asset_list (unmanaged table → RunSQL)
# For linked assets: use satellite irradiance from another asset's _sat device.

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("main", "0063_asset_list_pv_syst_pr"),
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
                        WHERE table_name = 'asset_list' AND column_name = 'satellite_irradiance_source_asset_code'
                    ) THEN
                        ALTER TABLE asset_list ADD COLUMN satellite_irradiance_source_asset_code VARCHAR(255) NULL;
                    END IF;
                END $$;
            """,
            reverse_sql="""
                DO $$
                BEGIN
                    IF to_regclass('public.asset_list') IS NULL THEN
                        RETURN;
                    END IF;

                    ALTER TABLE asset_list DROP COLUMN IF EXISTS satellite_irradiance_source_asset_code;
                END $$;
            """,
        ),
    ]
