from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("main", "0070_assets_contracts_columns"),
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
                        WHERE table_name = 'kpis' AND column_name = 'generation_metric'
                    ) THEN
                        ALTER TABLE kpis ADD COLUMN generation_metric VARCHAR(40) NULL;
                    END IF;

                    IF NOT EXISTS (
                        SELECT 1 FROM information_schema.columns
                        WHERE table_name = 'kpis' AND column_name = 'has_anomaly'
                    ) THEN
                        ALTER TABLE kpis ADD COLUMN has_anomaly BOOLEAN NOT NULL DEFAULT FALSE;
                    END IF;

                    IF NOT EXISTS (
                        SELECT 1 FROM information_schema.columns
                        WHERE table_name = 'kpis' AND column_name = 'anomaly_flags'
                    ) THEN
                        ALTER TABLE kpis ADD COLUMN anomaly_flags JSONB NULL;
                    END IF;

                    IF NOT EXISTS (
                        SELECT 1 FROM information_schema.columns
                        WHERE table_name = 'kpis' AND column_name = 'anomaly_notes'
                    ) THEN
                        ALTER TABLE kpis ADD COLUMN anomaly_notes TEXT NULL;
                    END IF;
                END $$;
            """,
            reverse_sql="""
                DO $$
                BEGIN
                    IF to_regclass('public.kpis') IS NULL THEN
                        RETURN;
                    END IF;

                    ALTER TABLE kpis DROP COLUMN IF EXISTS generation_metric;
                    ALTER TABLE kpis DROP COLUMN IF EXISTS has_anomaly;
                    ALTER TABLE kpis DROP COLUMN IF EXISTS anomaly_flags;
                    ALTER TABLE kpis DROP COLUMN IF EXISTS anomaly_notes;
                END $$;
            """,
        ),
    ]
