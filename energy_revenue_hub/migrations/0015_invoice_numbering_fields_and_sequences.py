from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("energy_revenue_hub", "0014_utility_invoice_review_and_parsed_fk"),
    ]

    operations = [
        migrations.AddField(
            model_name="generatedinvoice",
            name="output_invoice_number",
            field=models.CharField(blank=True, db_index=True, default="", max_length=64),
        ),
        migrations.AddField(
            model_name="generatedinvoice",
            name="invoice_asset_code",
            field=models.CharField(blank=True, db_index=True, default="", max_length=255),
        ),
        migrations.AddField(
            model_name="generatedinvoice",
            name="billing_contract_type",
            field=models.CharField(blank=True, db_index=True, default="", max_length=64),
        ),
        migrations.AddField(
            model_name="generatedinvoice",
            name="invoice_sequence_ledger",
            field=models.CharField(blank=True, db_index=True, default="", max_length=16),
        ),
        migrations.RunSQL(
            sql="""
            CREATE SEQUENCE IF NOT EXISTS erh_output_invoice_seq START WITH 1 INCREMENT BY 1;
            CREATE SEQUENCE IF NOT EXISTS erh_output_invoice_seq_test START WITH 1 INCREMENT BY 1;
            """,
            reverse_sql="""
            DROP SEQUENCE IF EXISTS erh_output_invoice_seq;
            DROP SEQUENCE IF EXISTS erh_output_invoice_seq_test;
            """,
        ),
    ]
