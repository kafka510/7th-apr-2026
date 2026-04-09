# Add tilt_configs (tilt/azimuth/panel count per string) to device_list (unmanaged table → RunSQL)

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("main", "0061_alter_bessdata_actual_no_of_cycles_and_more"),
    ]

    operations = [
        migrations.RunSQL(
            sql="""
                DO $$
                BEGIN
                    IF to_regclass('public.device_list') IS NULL THEN
                        RETURN;
                    END IF;

                    IF NOT EXISTS (
                        SELECT 1 FROM information_schema.columns
                        WHERE table_name = 'device_list' AND column_name = 'tilt_configs'
                    ) THEN
                        ALTER TABLE device_list ADD COLUMN tilt_configs JSONB NULL;
                    END IF;
                END $$;
            """,
            reverse_sql="""
                DO $$
                BEGIN
                    IF to_regclass('public.device_list') IS NULL THEN
                        RETURN;
                    END IF;

                    ALTER TABLE device_list DROP COLUMN IF EXISTS tilt_configs;
                END $$;
            """,
        ),
    ]
