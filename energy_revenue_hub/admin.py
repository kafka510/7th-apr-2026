from django.contrib import admin

from energy_revenue_hub.models import (
    Adjustment,
    AssetGeneration,
    BankDetail,
    BillingAuditLog,
    BillingInvoicePdf,
    BillingLineItem,
    BillingNotification,
    BillingSession,
    Currency,
    GeneratedInvoice,
    InvoiceEmbedding,
    InvoiceFieldCorrection,
    MeterReading,
    OtherInvoicesMeta,
    Payment,
    ParsedInvoice,
    Penalty,
    UtilityInvoice,
    VendorTemplate,
)


@admin.register(BillingSession)
class BillingSessionAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "country",
        "portfolio",
        "status",
        "billing_contract_type",
        "billing_month",
        "session_label",
        "invoice_template_id",
        "start_date",
        "end_date",
        "created_at",
    )
    list_filter = ("status", "country", "billing_contract_type")
    search_fields = ("country", "portfolio", "invoice_template_id", "session_label", "billing_contract_type")
    readonly_fields = ("id", "created_at", "updated_at")
    fieldsets = (
        (
            None,
            {
                "fields": (
                    "id",
                    "country",
                    "portfolio",
                    "asset_list",
                    "start_date",
                    "end_date",
                    "status",
                    "created_by",
                    "invoice_template_id",
                    "billing_extras_json",
                    "billing_contract_type",
                    "billing_month",
                    "session_label",
                    "created_at",
                    "updated_at",
                )
            },
        ),
    )


@admin.register(ParsedInvoice)
class ParsedInvoiceAdmin(admin.ModelAdmin):
    list_display = ("id", "billing_session", "invoice_number", "invoice_date", "export_energy", "created_at")
    search_fields = ("invoice_number",)


@admin.register(BillingLineItem)
class BillingLineItemAdmin(admin.ModelAdmin):
    list_display = ("id", "billing_session", "asset_name", "actual_kwh", "invoice_kwh", "revenue", "is_frozen")
    list_filter = ("billing_session", "is_frozen")


@admin.register(GeneratedInvoice)
class GeneratedInvoiceAdmin(admin.ModelAdmin):
    list_display = ("id", "billing_session", "file_path", "version", "generated_at")
    list_filter = ("billing_session",)
    readonly_fields = ("invoice_snapshot_json",)


@admin.register(BillingAuditLog)
class BillingAuditLogAdmin(admin.ModelAdmin):
    list_display = ("id", "billing_session", "action", "performed_by", "timestamp")
    list_filter = ("action",)


@admin.register(InvoiceFieldCorrection)
class InvoiceFieldCorrectionAdmin(admin.ModelAdmin):
    list_display = ("id", "vendor", "field_name", "original_value", "corrected_value", "created_at")
    list_filter = ("vendor", "field_name")
    search_fields = ("vendor", "field_name", "corrected_value")


@admin.register(VendorTemplate)
class VendorTemplateAdmin(admin.ModelAdmin):
    list_display = ("id", "vendor_key", "updated_at")


@admin.register(InvoiceEmbedding)
class InvoiceEmbeddingAdmin(admin.ModelAdmin):
    list_display = ("id", "vendor", "created_at")
    list_filter = ("vendor",)


@admin.register(BillingInvoicePdf)
class BillingInvoicePdfAdmin(admin.ModelAdmin):
    list_display = ("id", "billing_session", "original_filename", "transfer_status", "uploaded_at")
    list_filter = ("transfer_status",)
    search_fields = ("original_filename", "sharepoint_remote_path")


@admin.register(UtilityInvoice)
class UtilityInvoiceAdmin(admin.ModelAdmin):
    list_display = ("id", "invoice_record_type", "invoice_number", "asset_code", "total_amount", "created_at")
    list_filter = ("invoice_record_type", "currency_code")
    search_fields = ("invoice_number", "asset_code", "account_no")


@admin.register(MeterReading)
class MeterReadingAdmin(admin.ModelAdmin):
    list_display = ("id", "device_id", "read_at", "cumulative_value", "reading_role")
    list_filter = ("source", "data_quality", "reading_role")
    search_fields = ("device_id", "period_label")


@admin.register(BillingNotification)
class BillingNotificationAdmin(admin.ModelAdmin):
    list_display = ("id", "notification_type", "severity", "asset_code", "created_at", "read_at")
    list_filter = ("severity", "notification_type")


@admin.register(AssetGeneration)
class AssetGenerationAdmin(admin.ModelAdmin):
    list_display = ("id", "asset_number", "month", "grid_export_kwh", "pv_generation_kwh")
    search_fields = ("asset_number", "month")


@admin.register(Penalty)
class PenaltyAdmin(admin.ModelAdmin):
    list_display = ("id", "asset_number", "penalty_type", "penalty_charges")


@admin.register(Adjustment)
class AdjustmentAdmin(admin.ModelAdmin):
    list_display = ("id", "asset_number", "adjustment_type", "adjustment_amount")


@admin.register(BankDetail)
class BankDetailAdmin(admin.ModelAdmin):
    list_display = ("bank_account_number", "bank_name", "bank_swift_code", "beneficiary_name")


@admin.register(Currency)
class CurrencyAdmin(admin.ModelAdmin):
    list_display = ("currency_code", "currency_name", "asset_code", "currency_exchange_rate")


@admin.register(OtherInvoicesMeta)
class OtherInvoicesMetaAdmin(admin.ModelAdmin):
    list_display = ("invoice_no", "asset_number", "month", "recurring_charges_dollars")


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ("payment_id", "asset_number", "invoice", "payment_status", "payment_due", "payment_date")
    list_filter = ("payment_status",)
