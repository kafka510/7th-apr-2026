from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("energy_revenue_hub", "0007_utility_invoice_unit_rate_anomaly_fields"),
    ]

    operations = [
        migrations.RenameField(
            model_name="utilityinvoice",
            old_name="unit_rate_anomaly_flag",
            new_name="anomaly_flag",
        ),
        migrations.AlterField(
            model_name="utilityinvoice",
            name="anomaly_flag",
            field=models.TextField(blank=True, default="{}"),
        ),
        migrations.AlterField(
            model_name="utilityinvoice",
            name="calculated_unit_rate",
            field=models.TextField(blank=True, default=""),
        ),
    ]

