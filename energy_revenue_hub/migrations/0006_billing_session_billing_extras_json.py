from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("energy_revenue_hub", "0005_billing_freeze_and_invoice_snapshot"),
    ]

    operations = [
        migrations.AddField(
            model_name="billingsession",
            name="billing_extras_json",
            field=models.JSONField(
                blank=True,
                default=dict,
                help_text="Customer PDF extras (GST rate, notes, line adjustments) merged into invoice_snapshot_json on generate.",
            ),
        ),
    ]
