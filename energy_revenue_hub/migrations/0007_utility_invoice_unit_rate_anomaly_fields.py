from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("energy_revenue_hub", "0006_billing_session_billing_extras_json"),
    ]

    operations = [
        migrations.AddField(
            model_name="utilityinvoice",
            name="calculated_unit_rate",
            field=models.DecimalField(blank=True, decimal_places=6, max_digits=18, null=True),
        ),
        migrations.AddField(
            model_name="utilityinvoice",
            name="unit_rate_anomaly_flag",
            field=models.BooleanField(default=False),
        ),
    ]

