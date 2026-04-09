# Add pv_syst_pr to asset_list (unmanaged table → RunSQL)

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("main", "0062_add_device_list_tilt_configs"),
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
                        WHERE table_name = 'asset_list' AND column_name = 'pv_syst_pr'
                    ) THEN
                        ALTER TABLE asset_list ADD COLUMN pv_syst_pr DOUBLE PRECISION NULL;
                    END IF;
                END $$;
            """,
            reverse_sql="""
                DO $$
                BEGIN
                    IF to_regclass('public.asset_list') IS NULL THEN
                        RETURN;
                    END IF;

                    ALTER TABLE asset_list DROP COLUMN IF EXISTS pv_syst_pr;
                END $$;
            """,
        ),
    ]
