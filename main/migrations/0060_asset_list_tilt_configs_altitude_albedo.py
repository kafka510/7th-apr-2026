# Add tilt_configs, altitude_m, albedo to asset_list (unmanaged table → RunSQL)

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('main', '0059_locationmaster_sparemaster_stockentry_stockissue_and_more'),
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
                        WHERE table_name = 'asset_list' AND column_name = 'tilt_configs'
                    ) THEN
                        ALTER TABLE asset_list ADD COLUMN tilt_configs JSONB NULL;
                    END IF;

                    IF NOT EXISTS (
                        SELECT 1 FROM information_schema.columns
                        WHERE table_name = 'asset_list' AND column_name = 'altitude_m'
                    ) THEN
                        ALTER TABLE asset_list ADD COLUMN altitude_m DOUBLE PRECISION NULL;
                    END IF;

                    IF NOT EXISTS (
                        SELECT 1 FROM information_schema.columns
                        WHERE table_name = 'asset_list' AND column_name = 'albedo'
                    ) THEN
                        ALTER TABLE asset_list ADD COLUMN albedo DOUBLE PRECISION NULL;
                    END IF;
                END $$;
            """,
            reverse_sql="""
                DO $$
                BEGIN
                    IF to_regclass('public.asset_list') IS NULL THEN
                        RETURN;
                    END IF;

                    ALTER TABLE asset_list DROP COLUMN IF EXISTS tilt_configs;
                    ALTER TABLE asset_list DROP COLUMN IF EXISTS altitude_m;
                    ALTER TABLE asset_list DROP COLUMN IF EXISTS albedo;
                END $$;
            """,
        ),
    ]
