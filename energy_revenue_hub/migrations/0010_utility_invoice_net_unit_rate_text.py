from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("energy_revenue_hub", "0009_maiora_schema_fields"),
    ]

    operations = [
        migrations.AlterField(
            model_name="utilityinvoice",
            name="net_unit_rate",
            field=models.TextField(blank=True, default=""),
        ),
    ]

