from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("main", "0076_assetlist_customer_name_and_contract_due_days"),
    ]

    operations = [
        migrations.RunSQL(
            sql="""
            DO $$
            BEGIN
                IF to_regclass('public.yielddata') IS NOT NULL THEN
                    ALTER TABLE public.yielddata
                    ADD COLUMN IF NOT EXISTS budgeted_grid_curtailment double precision;
                ELSIF to_regclass('public.main_yielddata') IS NOT NULL THEN
                    ALTER TABLE public.main_yielddata
                    ADD COLUMN IF NOT EXISTS budgeted_grid_curtailment double precision;
                ELSE
                    RAISE EXCEPTION 'Neither public.yielddata nor public.main_yielddata exists';
                END IF;
            END
            $$;
            """,
            reverse_sql="""
            DO $$
            BEGIN
                IF to_regclass('public.yielddata') IS NOT NULL THEN
                    ALTER TABLE public.yielddata
                    DROP COLUMN IF EXISTS budgeted_grid_curtailment;
                ELSIF to_regclass('public.main_yielddata') IS NOT NULL THEN
                    ALTER TABLE public.main_yielddata
                    DROP COLUMN IF EXISTS budgeted_grid_curtailment;
                END IF;
            END
            $$;
            """,
        ),
    ]
