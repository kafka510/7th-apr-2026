from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("energy_revenue_hub", "0012_upload_summary_and_merge_flags"),
    ]

    operations = [
        migrations.AddField(
            model_name="billinginvoicepdf",
            name="parse_completed_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="billinginvoicepdf",
            name="parse_elapsed_seconds",
            field=models.DecimalField(blank=True, decimal_places=3, max_digits=12, null=True),
        ),
        migrations.AddField(
            model_name="billinginvoicepdf",
            name="parse_started_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
    ]
