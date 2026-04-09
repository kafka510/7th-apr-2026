from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("energy_revenue_hub", "0011_utility_invoice_freeze_fields"),
    ]

    operations = [
        migrations.AddField(
            model_name="billinginvoicepdf",
            name="billing_cycle_aligned",
            field=models.BooleanField(default=True),
        ),
        migrations.AddField(
            model_name="billinginvoicepdf",
            name="billing_cycle_warning_message",
            field=models.TextField(blank=True, default=""),
        ),
        migrations.AddField(
            model_name="billinginvoicepdf",
            name="frozen_data_changed",
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name="billinginvoicepdf",
            name="local_file_exists",
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name="billinginvoicepdf",
            name="local_file_size_bytes",
            field=models.BigIntegerField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="billinginvoicepdf",
            name="parse_error",
            field=models.TextField(blank=True, default=""),
        ),
        migrations.AddField(
            model_name="billinginvoicepdf",
            name="parse_status",
            field=models.CharField(blank=True, default="pending", max_length=32),
        ),
        migrations.AddField(
            model_name="billinginvoicepdf",
            name="parse_summary_status",
            field=models.CharField(blank=True, default="pending", max_length=32),
        ),
        migrations.AddField(
            model_name="billinginvoicepdf",
            name="pending_utility_patch_json",
            field=models.JSONField(blank=True, default=dict),
        ),
        migrations.AddField(
            model_name="billinginvoicepdf",
            name="security_reason_code",
            field=models.CharField(blank=True, default="", max_length=64),
        ),
        migrations.AddField(
            model_name="billinginvoicepdf",
            name="security_reason_message",
            field=models.TextField(blank=True, default=""),
        ),
        migrations.AddField(
            model_name="billinginvoicepdf",
            name="security_status",
            field=models.CharField(blank=True, default="passed", max_length=32),
        ),
        migrations.AddField(
            model_name="utilityinvoice",
            name="has_pending_merge",
            field=models.BooleanField(default=False),
        ),
    ]
