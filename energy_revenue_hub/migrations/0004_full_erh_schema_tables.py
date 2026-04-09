import django.db.models.deletion
import uuid
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("energy_revenue_hub", "0003_generated_invoice_sharepoint_fields"),
    ]

    operations = [
        migrations.CreateModel(
            name="Adjustment",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("asset_number", models.CharField(max_length=255)),
                ("adjustment_type", models.CharField(blank=True, default="", max_length=100)),
                ("adjustment_amount", models.DecimalField(blank=True, decimal_places=2, max_digits=18, null=True)),
                ("adjustment_reason", models.TextField(blank=True, default="")),
            ],
            options={"db_table": "adjustments"},
        ),
        migrations.CreateModel(
            name="AssetGeneration",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("asset_number", models.CharField(max_length=255)),
                ("sp_account_no", models.CharField(blank=True, default="", max_length=64)),
                ("month", models.CharField(max_length=7)),
                ("grid_export_kwh", models.DecimalField(blank=True, decimal_places=4, max_digits=18, null=True)),
                ("pv_generation_kwh", models.DecimalField(blank=True, decimal_places=4, max_digits=18, null=True)),
                ("rooftop_self_consumption_kwh", models.DecimalField(blank=True, decimal_places=4, max_digits=18, null=True)),
                ("net_metering_consumption_kwh", models.DecimalField(blank=True, decimal_places=4, max_digits=18, null=True)),
                ("bess_dispatch_kwh", models.DecimalField(blank=True, decimal_places=4, max_digits=18, null=True)),
                ("hybrid_solar_bess_kwh", models.DecimalField(blank=True, decimal_places=4, max_digits=18, null=True)),
                ("generation_based_ppa_kwh", models.DecimalField(blank=True, decimal_places=4, max_digits=18, null=True)),
                ("peak_tariff_kwh", models.DecimalField(blank=True, decimal_places=4, max_digits=18, null=True)),
                ("merchant_market_kwh", models.DecimalField(blank=True, decimal_places=4, max_digits=18, null=True)),
            ],
            options={"db_table": "asset_generation", "ordering": ["month", "asset_number"]},
        ),
        migrations.CreateModel(
            name="BankDetail",
            fields=[
                ("bank_account_number", models.CharField(max_length=64, primary_key=True, serialize=False)),
                ("bank_name", models.CharField(blank=True, default="", max_length=255)),
                ("bank_swift_code", models.CharField(blank=True, default="", max_length=32)),
                ("beneficiary_name", models.CharField(blank=True, default="", max_length=255)),
            ],
            options={"db_table": "bank_details"},
        ),
        migrations.CreateModel(
            name="BillingInvoicePdf",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("original_filename", models.CharField(blank=True, default="", max_length=512)),
                ("local_temp_path", models.TextField(blank=True, default="")),
                ("sharepoint_remote_path", models.TextField(blank=True, default="")),
                ("sharepoint_site_id", models.CharField(blank=True, default="", max_length=255)),
                ("sharepoint_drive_id", models.CharField(blank=True, default="", max_length=255)),
                ("sharepoint_item_id", models.CharField(blank=True, default="", max_length=255)),
                ("file_sha256", models.CharField(blank=True, default="", max_length=64)),
                (
                    "transfer_status",
                    models.CharField(
                        choices=[
                            ("pending_local", "Pending Local"),
                            ("parsing", "Parsing"),
                            ("pending_sharepoint", "Pending SharePoint"),
                            ("on_sharepoint", "On SharePoint"),
                            ("failed", "Failed"),
                        ],
                        default="pending_local",
                        max_length=32,
                    ),
                ),
                ("parse_task_id", models.CharField(blank=True, default="", max_length=255)),
                ("upload_task_id", models.CharField(blank=True, default="", max_length=255)),
                ("uploaded_at", models.DateTimeField(auto_now_add=True)),
                ("display_order", models.IntegerField(default=0)),
                (
                    "billing_session",
                    models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="billing_invoice_pdfs", to="energy_revenue_hub.billingsession"),
                ),
            ],
            options={"db_table": "billing_invoice_pdf", "ordering": ["uploaded_at"]},
        ),
        migrations.CreateModel(
            name="BillingNotification",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("notification_type", models.CharField(blank=True, default="", max_length=64)),
                ("severity", models.CharField(blank=True, default="", max_length=16)),
                ("asset_code", models.CharField(blank=True, default="", max_length=255)),
                ("device_id", models.CharField(blank=True, default="", max_length=120)),
                ("payload", models.JSONField(blank=True, default=dict)),
                ("read_at", models.DateTimeField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
            ],
            options={"db_table": "billing_notification", "ordering": ["-created_at"]},
        ),
        migrations.CreateModel(
            name="Currency",
            fields=[
                ("currency_code", models.CharField(max_length=8, primary_key=True, serialize=False)),
                ("asset_code", models.CharField(blank=True, default="", max_length=255)),
                ("currency_name", models.CharField(blank=True, default="", max_length=128)),
                ("currency_exchange_rate", models.DecimalField(blank=True, decimal_places=8, max_digits=18, null=True)),
            ],
            options={"db_table": "currencies"},
        ),
        migrations.CreateModel(
            name="MeterReading",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("device_id", models.CharField(max_length=120)),
                ("read_at", models.DateTimeField()),
                ("cumulative_value", models.DecimalField(decimal_places=6, max_digits=24)),
                ("source", models.CharField(blank=True, default="", max_length=32)),
                ("data_quality", models.CharField(blank=True, default="", max_length=32)),
                ("reading_role", models.CharField(blank=True, default="", max_length=16)),
                ("period_label", models.CharField(blank=True, default="", max_length=32)),
                ("delta_kwh_for_period", models.DecimalField(blank=True, decimal_places=6, max_digits=24, null=True)),
                ("calculation_notes", models.TextField(blank=True, default="")),
                ("notes", models.TextField(blank=True, default="")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
            ],
            options={"db_table": "meter_reading", "ordering": ["-read_at"]},
        ),
        migrations.CreateModel(
            name="OtherInvoicesMeta",
            fields=[
                ("invoice_no", models.CharField(max_length=100, primary_key=True, serialize=False)),
                ("asset_number", models.CharField(blank=True, default="", max_length=255)),
                ("month", models.CharField(blank=True, default="", max_length=7)),
                ("recurring_charges_dollars", models.DecimalField(blank=True, decimal_places=2, max_digits=18, null=True)),
                ("account_no", models.CharField(blank=True, default="", max_length=64)),
                ("billing_cycle", models.CharField(blank=True, default="", max_length=64)),
                ("optional", models.CharField(blank=True, default="", max_length=255)),
            ],
            options={"db_table": "other_invoices_meta"},
        ),
        migrations.CreateModel(
            name="Penalty",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("asset_number", models.CharField(max_length=255)),
                ("penalty_type", models.CharField(blank=True, default="", max_length=100)),
                ("penalty_rate", models.DecimalField(blank=True, decimal_places=6, max_digits=18, null=True)),
                ("penalty_charges", models.DecimalField(blank=True, decimal_places=2, max_digits=18, null=True)),
            ],
            options={"db_table": "penalties"},
        ),
        migrations.CreateModel(
            name="UtilityInvoice",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("invoice_record_type", models.CharField(blank=True, default="utility_parsed", max_length=32)),
                ("account_no", models.CharField(blank=True, default="", max_length=64)),
                ("asset_code", models.CharField(blank=True, default="", max_length=255)),
                ("invoice_number", models.CharField(blank=True, default="", max_length=100)),
                ("vendor_key", models.CharField(blank=True, default="", max_length=100)),
                ("invoice_date", models.DateField(blank=True, null=True)),
                ("period_start", models.DateField(blank=True, null=True)),
                ("period_end", models.DateField(blank=True, null=True)),
                ("currency_code", models.CharField(blank=True, default="", max_length=8)),
                ("total_amount", models.DecimalField(blank=True, decimal_places=2, max_digits=18, null=True)),
                ("export_energy", models.DecimalField(blank=True, decimal_places=2, max_digits=18, null=True)),
                ("export_energy_cost", models.DecimalField(blank=True, decimal_places=2, max_digits=18, null=True)),
                ("recurring_charges_dollars", models.DecimalField(blank=True, decimal_places=2, max_digits=18, null=True)),
                ("unit_rate", models.DecimalField(blank=True, decimal_places=6, max_digits=18, null=True)),
                ("raw_text", models.TextField(blank=True, default="")),
                ("parse_extraction_path", models.CharField(blank=True, default="", max_length=16)),
                ("parse_document_confidence_score", models.DecimalField(blank=True, decimal_places=2, max_digits=5, null=True)),
                ("parse_document_confidence_level", models.CharField(blank=True, default="", max_length=16)),
                ("parse_page_scores_json", models.JSONField(blank=True, default=dict)),
                ("parse_block_confidence_json", models.JSONField(blank=True, default=dict)),
                ("loss_calculation_task_id", models.BigIntegerField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "billing_invoice_pdf",
                    models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="utility_invoices", to="energy_revenue_hub.billinginvoicepdf"),
                ),
                (
                    "billing_session",
                    models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="utility_invoices", to="energy_revenue_hub.billingsession"),
                ),
            ],
            options={"db_table": "utility_invoice", "ordering": ["-created_at"]},
        ),
        migrations.CreateModel(
            name="Payment",
            fields=[
                ("payment_id", models.CharField(max_length=64, primary_key=True, serialize=False)),
                ("asset_number", models.CharField(blank=True, default="", max_length=255)),
                ("invoice_date", models.DateField(blank=True, null=True)),
                ("payment_due_condition", models.IntegerField(blank=True, null=True)),
                ("payment_due", models.DateField(blank=True, null=True)),
                ("payment_date", models.DateField(blank=True, null=True)),
                ("payment_paid", models.DecimalField(blank=True, decimal_places=2, max_digits=18, null=True)),
                ("payment_reference", models.CharField(blank=True, default="", max_length=255)),
                ("payment_pending", models.DecimalField(blank=True, decimal_places=2, max_digits=18, null=True)),
                ("payment_status", models.CharField(blank=True, default="", max_length=32)),
                (
                    "invoice",
                    models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="payments", to="energy_revenue_hub.utilityinvoice"),
                ),
            ],
            options={"db_table": "payments"},
        ),
    ]

