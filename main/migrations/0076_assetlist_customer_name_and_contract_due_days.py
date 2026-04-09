from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("main", "0075_assets_contracts_maiora_fields"),
    ]

    operations = [
        migrations.RunSQL(
            sql="""
            ALTER TABLE asset_list
            ADD COLUMN IF NOT EXISTS customer_name varchar(255);

            ALTER TABLE assets_contracts
            ADD COLUMN IF NOT EXISTS due_days integer;
            """,
            reverse_sql="""
            ALTER TABLE asset_list
            DROP COLUMN IF EXISTS customer_name;

            ALTER TABLE assets_contracts
            DROP COLUMN IF EXISTS due_days;
            """,
        ),
    ]
