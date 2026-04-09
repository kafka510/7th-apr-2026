"""
Energy Revenue Hub – billing engine models (ported from `peakpulse/energy_revenue_hub`).

Workflow states: DRAFT → FILTER_VALIDATED → PDF_UPLOADED → PARSED → REVIEWED → GENERATED → POSTED
Forward transitions (see `workflow.py`; includes pragmatic shortcuts for services).

**`parsed_invoices` vs `utility_invoice` (decision)**

- **`parsed_invoices`** — **kept**. Canonical persisted header for OCR/parse results **per billing session**
  (Peakpulse design). `InvoiceFieldCorrection` references `ParsedInvoice`.

- **`utility_invoice`** — **`UtilityInvoice`** model holds the full mapped parse output (amounts,
  periods, confidence, JSON snapshot of the parser dict). Populated alongside **`parsed_invoices`**
  when invoices are parsed in a billing session workflow.

**`billing_line_items`** — **kept** (per-asset line grid for the session workflow).
"""

import uuid

from django.db import models


class BillingSession(models.Model):
    """Billing session – one per filter validation; drives the workflow."""

    class Status(models.TextChoices):
        DRAFT = "DRAFT", "Draft"
        FILTER_VALIDATED = "FILTER_VALIDATED", "Filter Validated"
        PDF_UPLOADED = "PDF_UPLOADED", "PDF Uploaded"
        PARSED = "PARSED", "Parsed"
        REVIEWED = "REVIEWED", "Reviewed"
        GENERATED = "GENERATED", "Generated"
        POSTED = "POSTED", "Posted"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    country = models.CharField(max_length=50, blank=True)
    portfolio = models.CharField(max_length=100, blank=True)
    asset_list = models.JSONField(default=list)  # List of asset codes
    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=30, choices=Status.choices, default=Status.DRAFT)
    created_by = models.CharField(max_length=100, blank=True)
    invoice_template_id = models.CharField(
        max_length=64,
        blank=True,
        default="",
        help_text="Optional template key for customer PDF routing (server may also derive from contract_type).",
    )
    billing_extras_json = models.JSONField(
        default=dict,
        blank=True,
        help_text="Customer PDF extras (GST rate, notes, line adjustments) merged into invoice_snapshot_json on generate.",
    )
    billing_contract_type = models.CharField(
        max_length=32,
        blank=True,
        default="",
        db_index=True,
        help_text="Normalized contract profile key (e.g. sg_ppa_maiora); used for list filters and template routing.",
    )
    billing_month = models.DateField(
        null=True,
        blank=True,
        db_index=True,
        help_text="First day of the calendar month this session is for (e.g. 2026-02-01).",
    )
    session_label = models.CharField(max_length=200, blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "billing_sessions"
        ordering = ["-created_at"]

    def __str__(self):
        return f"BillingSession {self.id} ({self.status})"


class ParsedInvoice(models.Model):
    """Parsed invoice header – OCR result for one invoice (per session)."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    billing_session = models.ForeignKey(
        BillingSession,
        on_delete=models.CASCADE,
        related_name="parsed_invoices",
    )
    invoice_number = models.CharField(max_length=100, blank=True)
    invoice_date = models.DateField(null=True, blank=True)
    export_energy = models.DecimalField(max_digits=18, decimal_places=2, null=True, blank=True)
    raw_text = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "parsed_invoices"
        ordering = ["-created_at"]

    def __str__(self):
        return f"ParsedInvoice {self.invoice_number or self.id}"


class BillingLineItem(models.Model):
    """Line item per asset – actual, export, invoice energy, PPA rate, revenue."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    billing_session = models.ForeignKey(
        BillingSession,
        on_delete=models.CASCADE,
        related_name="line_items",
    )
    asset_name = models.CharField(max_length=100)
    asset_code = models.CharField(max_length=50, blank=True)
    actual_kwh = models.DecimalField(max_digits=18, decimal_places=2, default=0)
    export_kwh = models.DecimalField(max_digits=18, decimal_places=2, null=True, blank=True)
    invoice_kwh = models.DecimalField(max_digits=18, decimal_places=2, default=0)
    ppa_rate = models.DecimalField(max_digits=12, decimal_places=6, null=True, blank=True)
    revenue = models.DecimalField(max_digits=18, decimal_places=2, null=True, blank=True)
    is_frozen = models.BooleanField(default=False)
    frozen_at = models.DateTimeField(null=True, blank=True)
    frozen_by = models.CharField(max_length=100, blank=True, default="")
    sort_order = models.IntegerField(default=0)
    line_kind = models.CharField(max_length=32, blank=True, default="")
    segment_index = models.PositiveSmallIntegerField(null=True, blank=True)
    period_start = models.DateField(null=True, blank=True)
    period_end = models.DateField(null=True, blank=True)
    leasing_year_label = models.CharField(max_length=16, blank=True, default="")
    line_extras_json = models.JSONField(default=dict, blank=True)
    amount_excl_gst = models.DecimalField(max_digits=18, decimal_places=2, null=True, blank=True)

    class Meta:
        db_table = "billing_line_items"
        ordering = ["sort_order", "asset_name", "id"]

    def __str__(self):
        return f"{self.asset_name}: {self.invoice_kwh} kWh"


class GeneratedInvoice(models.Model):
    """Generated PDF invoice – stored file path, version."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    billing_session = models.ForeignKey(
        BillingSession,
        on_delete=models.CASCADE,
        related_name="generated_invoices",
    )
    file_path = models.TextField()
    version = models.IntegerField(default=1)
    output_invoice_number = models.CharField(max_length=64, blank=True, default="", db_index=True)
    invoice_asset_code = models.CharField(max_length=255, blank=True, default="", db_index=True)
    billing_contract_type = models.CharField(max_length=64, blank=True, default="", db_index=True)
    invoice_sequence_ledger = models.CharField(max_length=16, blank=True, default="", db_index=True)
    sharepoint_remote_path = models.TextField(blank=True, default="")
    sharepoint_item_id = models.CharField(max_length=255, blank=True, default="")
    sharepoint_web_url = models.TextField(blank=True, default="")
    sharepoint_upload_status = models.CharField(max_length=32, blank=True, default="pending_local")
    sharepoint_upload_error = models.TextField(blank=True, default="")
    invoice_snapshot_json = models.JSONField(
        default=dict,
        blank=True,
        help_text="Frozen snapshot for PDF: utility header copy, tax totals, extras, template id, party strings.",
    )
    generated_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "generated_invoices"
        ordering = ["-generated_at"]

    def __str__(self):
        return f"GeneratedInvoice v{self.version} ({self.file_path})"


class BillingInvoicePdf(models.Model):
    """Uploaded utility PDF metadata and transfer lifecycle tracking."""

    class TransferStatus(models.TextChoices):
        PENDING_LOCAL = "pending_local", "Pending Local"
        PARSING = "parsing", "Parsing"
        PENDING_SHAREPOINT = "pending_sharepoint", "Pending SharePoint"
        ON_SHAREPOINT = "on_sharepoint", "On SharePoint"
        FAILED = "failed", "Failed"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    billing_session = models.ForeignKey(
        BillingSession,
        on_delete=models.CASCADE,
        related_name="billing_invoice_pdfs",
    )
    original_filename = models.CharField(max_length=512, blank=True, default="")
    local_temp_path = models.TextField(blank=True, default="")
    sharepoint_remote_path = models.TextField(blank=True, default="")
    sharepoint_site_id = models.CharField(max_length=255, blank=True, default="")
    sharepoint_drive_id = models.CharField(max_length=255, blank=True, default="")
    sharepoint_item_id = models.CharField(max_length=255, blank=True, default="")
    file_sha256 = models.CharField(max_length=64, blank=True, default="")
    transfer_status = models.CharField(max_length=32, choices=TransferStatus.choices, default=TransferStatus.PENDING_LOCAL)
    parse_status = models.CharField(max_length=32, blank=True, default="pending")
    parse_error = models.TextField(blank=True, default="")
    parse_started_at = models.DateTimeField(null=True, blank=True)
    parse_completed_at = models.DateTimeField(null=True, blank=True)
    parse_elapsed_seconds = models.DecimalField(max_digits=12, decimal_places=3, null=True, blank=True)
    parse_summary_status = models.CharField(max_length=32, blank=True, default="pending")
    billing_cycle_aligned = models.BooleanField(default=True)
    billing_cycle_warning_message = models.TextField(blank=True, default="")
    pending_utility_patch_json = models.JSONField(default=dict, blank=True)
    frozen_data_changed = models.BooleanField(default=False)
    local_file_exists = models.BooleanField(default=False)
    local_file_size_bytes = models.BigIntegerField(null=True, blank=True)
    security_status = models.CharField(max_length=32, blank=True, default="passed")
    security_reason_code = models.CharField(max_length=64, blank=True, default="")
    security_reason_message = models.TextField(blank=True, default="")
    parse_task_id = models.CharField(max_length=255, blank=True, default="")
    upload_task_id = models.CharField(max_length=255, blank=True, default="")
    uploaded_at = models.DateTimeField(auto_now_add=True)
    display_order = models.IntegerField(default=0)

    class Meta:
        db_table = "billing_invoice_pdf"
        ordering = ["uploaded_at"]

    def __str__(self):
        return f"BillingInvoicePdf {self.id} ({self.transfer_status})"


class UtilityInvoice(models.Model):
    """Canonical utility/AR invoice row, optionally sourced from parsed ERH workflow."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    invoice_record_type = models.CharField(max_length=32, blank=True, default="utility_parsed")
    billing_session = models.ForeignKey(
        BillingSession,
        on_delete=models.SET_NULL,
        related_name="utility_invoices",
        null=True,
        blank=True,
    )
    billing_invoice_pdf = models.ForeignKey(
        BillingInvoicePdf,
        on_delete=models.SET_NULL,
        related_name="utility_invoices",
        null=True,
        blank=True,
    )
    parsed_invoice = models.ForeignKey(
        "ParsedInvoice",
        on_delete=models.SET_NULL,
        related_name="utility_invoices",
        null=True,
        blank=True,
    )
    account_no = models.CharField(max_length=64, blank=True, default="")
    asset_code = models.CharField(max_length=255, blank=True, default="")
    invoice_number = models.CharField(max_length=100, blank=True, default="")
    vendor_key = models.CharField(max_length=100, blank=True, default="")
    invoice_date = models.DateField(null=True, blank=True)
    period_start = models.DateField(null=True, blank=True)
    period_end = models.DateField(null=True, blank=True)
    currency_code = models.CharField(max_length=8, blank=True, default="")
    total_amount = models.DecimalField(max_digits=18, decimal_places=2, null=True, blank=True)
    export_energy = models.DecimalField(max_digits=18, decimal_places=2, null=True, blank=True)
    export_energy_cost = models.DecimalField(max_digits=18, decimal_places=2, null=True, blank=True)
    recurring_charges_dollars = models.DecimalField(max_digits=18, decimal_places=2, null=True, blank=True)
    unit_rate = models.DecimalField(max_digits=18, decimal_places=6, null=True, blank=True)
    calculated_unit_rate = models.TextField(blank=True, default="")
    anomaly_flag = models.TextField(blank=True, default="{}")
    current_charges_excl_gst = models.DecimalField(max_digits=18, decimal_places=2, null=True, blank=True)
    net_unit_rate = models.TextField(blank=True, default="")
    gst_rate = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    raw_text = models.TextField(blank=True, default="")
    parse_extraction_path = models.CharField(max_length=16, blank=True, default="")
    parse_document_confidence_score = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    parse_document_confidence_level = models.CharField(max_length=16, blank=True, default="")
    parse_page_scores_json = models.JSONField(default=dict, blank=True)
    parse_block_confidence_json = models.JSONField(default=dict, blank=True)
    loss_calculation_task_id = models.BigIntegerField(null=True, blank=True)
    is_frozen = models.BooleanField(default=True)
    has_pending_merge = models.BooleanField(default=False)
    frozen_at = models.DateTimeField(null=True, blank=True)
    frozen_by = models.CharField(max_length=100, blank=True, default="")
    parse_review_status = models.CharField(max_length=16, blank=True, default="pending")
    parse_review_passed_at = models.DateTimeField(null=True, blank=True)
    parse_review_passed_by = models.CharField(max_length=100, blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "utility_invoice"
        ordering = ["-created_at"]

    def __str__(self):
        return self.invoice_number or str(self.id)


class BillingAuditLog(models.Model):
    """Audit log for billing actions."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    billing_session = models.ForeignKey(
        BillingSession,
        on_delete=models.CASCADE,
        related_name="audit_logs",
        null=True,
        blank=True,
    )
    action = models.CharField(max_length=100)
    performed_by = models.CharField(max_length=100, blank=True)
    details = models.JSONField(default=dict, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "billing_audit_logs"
        ordering = ["-timestamp"]

    def __str__(self):
        return f"{self.action} by {self.performed_by or 'system'}"


# --- Level 3: Invoice Intelligence ---


class InvoiceFieldCorrection(models.Model):
    """Human correction of an extracted field; used by learning engine per vendor."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    invoice = models.ForeignKey(
        "ParsedInvoice",
        on_delete=models.CASCADE,
        related_name="field_corrections",
        null=True,
        blank=True,
    )
    field_name = models.CharField(max_length=100)
    original_value = models.TextField(blank=True)
    corrected_value = models.TextField(blank=True)
    vendor = models.CharField(max_length=100)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "invoice_field_corrections"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.vendor}.{self.field_name}"


class VendorTemplate(models.Model):
    """Optional: store vendor-specific extraction hints or rules (JSON)."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    vendor_key = models.CharField(max_length=100, unique=True)
    config = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "vendor_templates"

    def __str__(self):
        return self.vendor_key


class InvoiceEmbedding(models.Model):
    """Vector memory: embedding of invoice text per vendor (for similarity / future rules)."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    vendor = models.CharField(max_length=100)
    embedding_json = models.JSONField(default=list)  # list of floats
    text_preview = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "invoice_embeddings"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.vendor} ({len(self.embedding_json)}d)"


class MeterReading(models.Model):
    """Cumulative billing register readings per device."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    device_id = models.CharField(max_length=120)
    read_at = models.DateTimeField()
    cumulative_value = models.DecimalField(max_digits=24, decimal_places=6)
    source = models.CharField(max_length=32, blank=True, default="")
    data_quality = models.CharField(max_length=32, blank=True, default="")
    reading_role = models.CharField(max_length=16, blank=True, default="")
    period_label = models.CharField(max_length=32, blank=True, default="")
    delta_kwh_for_period = models.DecimalField(max_digits=24, decimal_places=6, null=True, blank=True)
    calculation_notes = models.TextField(blank=True, default="")
    notes = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "meter_reading"
        ordering = ["-read_at"]


class BillingNotification(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    notification_type = models.CharField(max_length=64, blank=True, default="")
    severity = models.CharField(max_length=16, blank=True, default="")
    asset_code = models.CharField(max_length=255, blank=True, default="")
    device_id = models.CharField(max_length=120, blank=True, default="")
    payload = models.JSONField(default=dict, blank=True)
    read_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "billing_notification"
        ordering = ["-created_at"]


class AssetGeneration(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    asset_number = models.CharField(max_length=255)
    sp_account_no = models.CharField(max_length=64, blank=True, default="")
    month = models.CharField(max_length=7)
    grid_export_kwh = models.DecimalField(max_digits=18, decimal_places=4, null=True, blank=True)
    pv_generation_kwh = models.DecimalField(max_digits=18, decimal_places=4, null=True, blank=True)
    rooftop_self_consumption_kwh = models.DecimalField(max_digits=18, decimal_places=4, null=True, blank=True)
    net_metering_consumption_kwh = models.DecimalField(max_digits=18, decimal_places=4, null=True, blank=True)
    bess_dispatch_kwh = models.DecimalField(max_digits=18, decimal_places=4, null=True, blank=True)
    hybrid_solar_bess_kwh = models.DecimalField(max_digits=18, decimal_places=4, null=True, blank=True)
    generation_based_ppa_kwh = models.DecimalField(max_digits=18, decimal_places=4, null=True, blank=True)
    peak_tariff_kwh = models.DecimalField(max_digits=18, decimal_places=4, null=True, blank=True)
    merchant_market_kwh = models.DecimalField(max_digits=18, decimal_places=4, null=True, blank=True)

    class Meta:
        db_table = "asset_generation"
        ordering = ["month", "asset_number"]


class Penalty(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    asset_number = models.CharField(max_length=255)
    penalty_type = models.CharField(max_length=100, blank=True, default="")
    penalty_rate = models.DecimalField(max_digits=18, decimal_places=6, null=True, blank=True)
    penalty_charges = models.DecimalField(max_digits=18, decimal_places=2, null=True, blank=True)

    class Meta:
        db_table = "penalties"


class Adjustment(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    asset_number = models.CharField(max_length=255)
    adjustment_type = models.CharField(max_length=100, blank=True, default="")
    adjustment_amount = models.DecimalField(max_digits=18, decimal_places=2, null=True, blank=True)
    adjustment_reason = models.TextField(blank=True, default="")

    class Meta:
        db_table = "adjustments"


class BankDetail(models.Model):
    bank_account_number = models.CharField(max_length=64, primary_key=True)
    bank_name = models.CharField(max_length=255, blank=True, default="")
    bank_swift_code = models.CharField(max_length=32, blank=True, default="")
    beneficiary_name = models.CharField(max_length=255, blank=True, default="")

    class Meta:
        db_table = "bank_details"


class Currency(models.Model):
    currency_code = models.CharField(max_length=8, primary_key=True)
    asset_code = models.CharField(max_length=255, blank=True, default="")
    currency_name = models.CharField(max_length=128, blank=True, default="")
    currency_exchange_rate = models.DecimalField(max_digits=18, decimal_places=8, null=True, blank=True)

    class Meta:
        db_table = "currencies"


class OtherInvoicesMeta(models.Model):
    invoice_no = models.CharField(max_length=100, primary_key=True)
    asset_number = models.CharField(max_length=255, blank=True, default="")
    month = models.CharField(max_length=7, blank=True, default="")
    recurring_charges_dollars = models.DecimalField(max_digits=18, decimal_places=2, null=True, blank=True)
    account_no = models.CharField(max_length=64, blank=True, default="")
    billing_cycle = models.CharField(max_length=64, blank=True, default="")
    optional = models.CharField(max_length=255, blank=True, default="")

    class Meta:
        db_table = "other_invoices_meta"


class Payment(models.Model):
    payment_id = models.CharField(max_length=64, primary_key=True)
    asset_number = models.CharField(max_length=255, blank=True, default="")
    invoice = models.ForeignKey(
        UtilityInvoice,
        on_delete=models.SET_NULL,
        related_name="payments",
        null=True,
        blank=True,
    )
    invoice_date = models.DateField(null=True, blank=True)
    payment_due_condition = models.IntegerField(null=True, blank=True)
    payment_due = models.DateField(null=True, blank=True)
    payment_date = models.DateField(null=True, blank=True)
    payment_paid = models.DecimalField(max_digits=18, decimal_places=2, null=True, blank=True)
    payment_reference = models.CharField(max_length=255, blank=True, default="")
    payment_pending = models.DecimalField(max_digits=18, decimal_places=2, null=True, blank=True)
    payment_status = models.CharField(max_length=32, blank=True, default="")

    class Meta:
        db_table = "payments"
