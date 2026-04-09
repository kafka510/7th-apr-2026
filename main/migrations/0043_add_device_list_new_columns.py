# Generated manually for device_list new columns
# Since device_list is an unmanaged model, we use raw SQL to add columns

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('main', '0042_yielddata_operational_budget_dollar_and_more'),
    ]

    operations = [
        # Add new columns to device_list table
        migrations.RunSQL(
            # Forward migration - add columns
            sql="""
                DO $$
                BEGIN
                    IF to_regclass('public.device_list') IS NULL THEN
                        RETURN;
                    END IF;

                    ALTER TABLE device_list 
                    ADD COLUMN IF NOT EXISTS ac_capacity DOUBLE PRECISION,
                    ADD COLUMN IF NOT EXISTS equipment_warranty_start_date TIMESTAMP,
                    ADD COLUMN IF NOT EXISTS equipment_warranty_expire_date TIMESTAMP,
                    ADD COLUMN IF NOT EXISTS epc_warranty_start_date TIMESTAMP,
                    ADD COLUMN IF NOT EXISTS epc_warranty_expire_date TIMESTAMP,
                    ADD COLUMN IF NOT EXISTS calibration_frequency VARCHAR(40),
                    ADD COLUMN IF NOT EXISTS pm_frequency VARCHAR(40),
                    ADD COLUMN IF NOT EXISTS visual_inspection_frequency VARCHAR(40),
                    ADD COLUMN IF NOT EXISTS bess_capacity DOUBLE PRECISION,
                    ADD COLUMN IF NOT EXISTS yom VARCHAR(40),
                    ADD COLUMN IF NOT EXISTS nomenclature VARCHAR(120);
                END $$;
            """,
            # Reverse migration - remove columns (for rollback)
            reverse_sql="""
                DO $$
                BEGIN
                    IF to_regclass('public.device_list') IS NULL THEN
                        RETURN;
                    END IF;

                    ALTER TABLE device_list 
                    DROP COLUMN IF EXISTS ac_capacity,
                    DROP COLUMN IF EXISTS equipment_warranty_start_date,
                    DROP COLUMN IF EXISTS equipment_warranty_expire_date,
                    DROP COLUMN IF EXISTS epc_warranty_start_date,
                    DROP COLUMN IF EXISTS epc_warranty_expire_date,
                    DROP COLUMN IF EXISTS calibration_frequency,
                    DROP COLUMN IF EXISTS pm_frequency,
                    DROP COLUMN IF EXISTS visual_inspection_frequency,
                    DROP COLUMN IF EXISTS bess_capacity,
                    DROP COLUMN IF EXISTS yom,
                    DROP COLUMN IF EXISTS nomenclature;
                END $$;
            """
        ),
    ]

