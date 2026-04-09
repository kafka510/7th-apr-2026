# Billing session discovery, line item segments, utility invoice Maiora fields (SG_PPA_MAIORA_INVOICE_PLAN.md §5.2–5.4)

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("energy_revenue_hub", "0008_utility_invoice_anomaly_flag_json"),
    ]

    operations = [
        migrations.AddField(
            model_name="billingsession",
            name="billing_contract_type",
            field=models.CharField(
                blank=True,
                db_index=True,
                default="",
                help_text="Normalized contract profile key (e.g. sg_ppa_maiora); used for list filters and template routing.",
                max_length=32,
            ),
        ),
        migrations.AddField(
            model_name="billingsession",
            name="billing_month",
            field=models.DateField(
                blank=True,
                db_index=True,
                help_text="First day of the calendar month this session is for (e.g. 2026-02-01).",
                null=True,
            ),
        ),
        migrations.AddField(
            model_name="billingsession",
            name="session_label",
            field=models.CharField(blank=True, default="", max_length=200),
        ),
        migrations.AddIndex(
            model_name="billingsession",
            index=models.Index(fields=["billing_contract_type", "billing_month"], name="billing_sess_ctype_bmonth_idx"),
        ),
        migrations.AddField(
            model_name="billinglineitem",
            name="sort_order",
            field=models.IntegerField(default=0),
        ),
        migrations.AddField(
            model_name="billinglineitem",
            name="line_kind",
            field=models.CharField(blank=True, default="", max_length=32),
        ),
        migrations.AddField(
            model_name="billinglineitem",
            name="segment_index",
            field=models.PositiveSmallIntegerField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="billinglineitem",
            name="period_start",
            field=models.DateField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="billinglineitem",
            name="period_end",
            field=models.DateField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="billinglineitem",
            name="leasing_year_label",
            field=models.CharField(blank=True, default="", max_length=16),
        ),
        migrations.AddField(
            model_name="billinglineitem",
            name="line_extras_json",
            field=models.JSONField(blank=True, default=dict),
        ),
        migrations.AddField(
            model_name="billinglineitem",
            name="amount_excl_gst",
            field=models.DecimalField(blank=True, decimal_places=2, max_digits=18, null=True),
        ),
        migrations.AddField(
            model_name="utilityinvoice",
            name="current_charges_excl_gst",
            field=models.DecimalField(blank=True, decimal_places=2, max_digits=18, null=True),
        ),
        migrations.AddField(
            model_name="utilityinvoice",
            name="net_unit_rate",
            field=models.DecimalField(blank=True, decimal_places=8, max_digits=18, null=True),
        ),
        migrations.AddField(
            model_name="utilityinvoice",
            name="gst_rate",
            field=models.DecimalField(blank=True, decimal_places=6, max_digits=9, null=True),
        ),
    ]
