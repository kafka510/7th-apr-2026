# Maiora / ERH: escalation type, grace years, GST, bank fields (SG_PPA_MAIORA_INVOICE_PLAN.md §5.1)

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("main", "0074_assets_contracts_requires_utility_invoice"),
    ]

    operations = [
        migrations.AddField(
            model_name="assets_contracts",
            name="escalation_type",
            field=models.CharField(
                blank=True,
                default="",
                help_text="Escalation model for rooftop/MRE rate: multiplicative, additive, etc.",
                max_length=24,
            ),
        ),
        migrations.AddField(
            model_name="assets_contracts",
            name="escalation_grace_years",
            field=models.PositiveSmallIntegerField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="assets_contracts",
            name="gst_rate",
            field=models.DecimalField(
                blank=True,
                decimal_places=6,
                help_text="GST as decimal fraction e.g. 0.09 for 9%.",
                max_digits=9,
                null=True,
            ),
        ),
        migrations.AddField(
            model_name="assets_contracts",
            name="bank_name",
            field=models.CharField(blank=True, default="", max_length=255),
        ),
        migrations.AddField(
            model_name="assets_contracts",
            name="bank_account_no",
            field=models.CharField(blank=True, default="", max_length=64),
        ),
        migrations.AddField(
            model_name="assets_contracts",
            name="bank_swift",
            field=models.CharField(blank=True, default="", max_length=32),
        ),
        migrations.AddField(
            model_name="assets_contracts",
            name="bank_branch_code",
            field=models.CharField(blank=True, default="", max_length=64),
        ),
    ]
