from django.db import migrations, models


def freeze_existing_utility_rows(apps, schema_editor):
    UtilityInvoice = apps.get_model("energy_revenue_hub", "UtilityInvoice")
    UtilityInvoice.objects.filter(is_frozen=False).update(is_frozen=True)


class Migration(migrations.Migration):

    dependencies = [
        ("energy_revenue_hub", "0010_utility_invoice_net_unit_rate_text"),
    ]

    operations = [
        migrations.AddField(
            model_name="utilityinvoice",
            name="frozen_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="utilityinvoice",
            name="frozen_by",
            field=models.CharField(blank=True, default="", max_length=100),
        ),
        migrations.AddField(
            model_name="utilityinvoice",
            name="is_frozen",
            field=models.BooleanField(default=True),
        ),
        migrations.RunPython(freeze_existing_utility_rows, migrations.RunPython.noop),
    ]
