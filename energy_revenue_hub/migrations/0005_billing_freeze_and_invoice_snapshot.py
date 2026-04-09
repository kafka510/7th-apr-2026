from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("energy_revenue_hub", "0004_full_erh_schema_tables"),
    ]

    operations = [
        migrations.AddField(
            model_name="billingsession",
            name="invoice_template_id",
            field=models.CharField(
                blank=True,
                default="",
                help_text="Optional template key for customer PDF routing (server may also derive from contract_type).",
                max_length=64,
            ),
        ),
        migrations.AddField(
            model_name="billinglineitem",
            name="frozen_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="billinglineitem",
            name="frozen_by",
            field=models.CharField(blank=True, default="", max_length=100),
        ),
        migrations.AddField(
            model_name="billinglineitem",
            name="is_frozen",
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name="generatedinvoice",
            name="invoice_snapshot_json",
            field=models.JSONField(
                blank=True,
                default=dict,
                help_text="Frozen snapshot for PDF: utility header copy, tax totals, extras, template id, party strings.",
            ),
        ),
    ]
