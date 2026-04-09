# Add loss_calculation_enabled to device_list (Site Onboarding → PV Module → Device Configuration).
# When True or null (default), device is included in daily loss and test page device list.

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("main", "0064_asset_list_satellite_irradiance_source"),
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
                        WHERE table_name = 'device_list' AND column_name = 'loss_calculation_enabled'
                    ) THEN
                        ALTER TABLE device_list
                        ADD COLUMN loss_calculation_enabled BOOLEAN NULL DEFAULT true;
                        COMMENT ON COLUMN device_list.loss_calculation_enabled IS
                        'Enable loss calculation for this device. Default true when null (backward compatibility).';
                    END IF;
                END $$;
            """,
            reverse_sql="""
                DO $$
                BEGIN
                    IF to_regclass('public.device_list') IS NULL THEN
                        RETURN;
                    END IF;

                    ALTER TABLE device_list DROP COLUMN IF EXISTS loss_calculation_enabled;
                END $$;
            """,
        ),
    ]
