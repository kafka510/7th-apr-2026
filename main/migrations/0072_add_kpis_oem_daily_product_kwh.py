from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("main", "0071_add_kpis_generation_anomaly_fields"),
    ]

    operations = [
        migrations.RunSQL(
            sql="""
                DO $$
                BEGIN
                    IF to_regclass('public.kpis') IS NULL THEN
                        RETURN;
                    END IF;

                    IF NOT EXISTS (
                        SELECT 1 FROM information_schema.columns
                        WHERE table_name = 'kpis' AND column_name = 'oem_daily_product_kwh'
                    ) THEN
                        ALTER TABLE kpis ADD COLUMN oem_daily_product_kwh DOUBLE PRECISION NULL;
                    END IF;
                END $$;
            """,
            reverse_sql="""
                DO $$
                BEGIN
                    IF to_regclass('public.kpis') IS NULL THEN
                        RETURN;
                    END IF;

                    ALTER TABLE kpis DROP COLUMN IF EXISTS oem_daily_product_kwh;
                END $$;
            """,
        ),
    ]
