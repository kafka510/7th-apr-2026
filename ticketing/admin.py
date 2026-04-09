from django.contrib import admin
from .models import (
    Ticket, TicketCategory, TicketSubCategory, LossCategory, TicketActivity,
    TicketComment, TicketAttachment, TicketMaterial, TicketManpower,
    TicketFieldDefinition, TicketEmailNotification
)


@admin.register(TicketCategory)
class TicketCategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'display_order', 'is_active', 'created_at']
    list_filter = ['is_active', 'created_at']
    search_fields = ['name', 'description']
    ordering = ['display_order', 'name']


@admin.register(LossCategory)
class LossCategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'display_order', 'is_active', 'created_at']
    list_filter = ['is_active', 'created_at']
    search_fields = ['name', 'description']
    ordering = ['display_order', 'name']


@admin.register(TicketSubCategory)
class TicketSubCategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'category', 'display_order', 'is_active', 'created_at']
    list_filter = ['category', 'is_active']
    search_fields = ['name', 'description', 'category__name']
    ordering = ['category', 'display_order', 'name']
    autocomplete_fields = ['category']


class TicketMaterialInline(admin.TabularInline):
    model = TicketMaterial
    extra = 0
    readonly_fields = ['created_at', 'updated_at']


class TicketManpowerInline(admin.TabularInline):
    model = TicketManpower
    extra = 0
    readonly_fields = ['created_at', 'updated_at']


@admin.register(Ticket)
class TicketAdmin(admin.ModelAdmin):
    list_display = [
        'ticket_number', 'title', 'status', 'priority', 
        'category', 'sub_category', 'asset_code', 'created_by', 'assigned_to', 'updated_by',
        'created_at', 'is_active'
    ]
    list_filter = [
        'status', 'priority', 'category', 'loss_category',
        'is_active', 'created_at', 'asset_code'
    ]
    search_fields = [
        'ticket_number', 'title', 'description',
        'asset_code__asset_name', 'asset_code__asset_code'
    ]
    readonly_fields = [
        'ticket_number', 'created_at', 'updated_at',
        'created_by', 'updated_by', 'closed_at', 'closed_by'
    ]
    raw_id_fields = ['asset_code', 'device_id', 'created_by', 'updated_by', 'assigned_to', 'closed_by']
    inlines = [TicketMaterialInline, TicketManpowerInline]
    date_hierarchy = 'created_at'
    ordering = ['-created_at']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('ticket_number', 'title', 'description', 'category', 'sub_category', 'loss_category')
        }),
        ('Status', {
            'fields': ('status', 'priority', 'is_active')
        }),
        ('Relationships', {
            'fields': ('asset_code', 'device_id')
        }),
        ('User Assignments', {
            'fields': ('created_by', 'updated_by', 'assigned_to', 'closed_by')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at', 'closed_at')
        }),
        ('Resolution', {
            'fields': ('resolution_notes',)
        }),
        ('Metadata', {
            'fields': ('metadata',),
            'classes': ('collapse',)
        }),
    )


@admin.register(TicketActivity)
class TicketActivityAdmin(admin.ModelAdmin):
    list_display = [
        'ticket', 'user', 'action_type', 'field_changed',
        'timestamp'
    ]
    list_filter = ['action_type', 'timestamp']
    search_fields = [
        'ticket__ticket_number', 'ticket__title',
        'user__username', 'user__email'
    ]
    readonly_fields = ['ticket', 'user', 'action_type', 'timestamp', 'ip_address']
    raw_id_fields = ['ticket', 'user']
    date_hierarchy = 'timestamp'
    ordering = ['-timestamp']


@admin.register(TicketComment)
class TicketCommentAdmin(admin.ModelAdmin):
    list_display = ['ticket', 'user', 'is_internal', 'created_at']
    list_filter = ['is_internal', 'created_at']
    search_fields = [
        'ticket__ticket_number', 'comment',
        'user__username'
    ]
    raw_id_fields = ['ticket', 'user']
    date_hierarchy = 'created_at'
    ordering = ['-created_at']


@admin.register(TicketAttachment)
class TicketAttachmentAdmin(admin.ModelAdmin):
    list_display = [
        'ticket', 'file_name', 'file_size', 
        'uploaded_by', 'uploaded_at'
    ]
    list_filter = ['uploaded_at', 'file_type']
    search_fields = [
        'ticket__ticket_number', 'file_name',
        'uploaded_by__username'
    ]
    raw_id_fields = ['ticket', 'uploaded_by']
    date_hierarchy = 'uploaded_at'
    ordering = ['-uploaded_at']


@admin.register(TicketFieldDefinition)
class TicketFieldDefinitionAdmin(admin.ModelAdmin):
    list_display = [
        'field_label', 'field_name', 'field_type',
        'is_required', 'display_order', 'is_active'
    ]
    list_filter = ['field_type', 'is_required', 'is_active']
    search_fields = ['field_name', 'field_label']
    ordering = ['display_order', 'field_label']


@admin.register(TicketEmailNotification)
class TicketEmailNotificationAdmin(admin.ModelAdmin):
    list_display = [
        'ticket', 'recipient', 'notification_type',
        'status', 'sent_at'
    ]
    list_filter = ['notification_type', 'status', 'sent_at']
    search_fields = [
        'ticket__ticket_number',
        'recipient__username', 'recipient__email'
    ]
    readonly_fields = ['ticket', 'recipient', 'sent_at']
    raw_id_fields = ['ticket', 'recipient']
    date_hierarchy = 'sent_at'
    ordering = ['-sent_at']
