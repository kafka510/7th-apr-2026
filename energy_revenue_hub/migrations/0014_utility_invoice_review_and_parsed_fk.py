import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("energy_revenue_hub", "0013_billinginvoicepdf_parse_timing_fields"),
    ]

    operations = [
        migrations.AddField(
            model_name="utilityinvoice",
            name="parsed_invoice",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="utility_invoices",
                to="energy_revenue_hub.parsedinvoice",
            ),
        ),
        migrations.AddField(
            model_name="utilityinvoice",
            name="parse_review_status",
            field=models.CharField(blank=True, default="pending", max_length=16),
        ),
        migrations.AddField(
            model_name="utilityinvoice",
            name="parse_review_passed_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="utilityinvoice",
            name="parse_review_passed_by",
            field=models.CharField(blank=True, default="", max_length=100),
        ),
    ]

