"""
API Admin Interface
-------------------
Django admin interface for API management
"""

from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils import timezone
from .models import (
    APIUser, APIKey, ActiveToken, TablePermission, 
    ColumnRestriction, APIRequestLog, RateLimitTracker
)


@admin.register(APIUser)
class APIUserAdmin(admin.ModelAdmin):
    list_display = ['name', 'user', 'status', 'total_requests', 'last_request_at', 'created_at', 'is_active_display']
    list_filter = ['status', 'created_at']
    search_fields = ['name', 'user__username', 'description']
    readonly_fields = ['total_requests', 'last_request_at', 'created_at', 'updated_at']
    
    fieldsets = [
        ('Basic Information', {
            'fields': ['user', 'name', 'description', 'status']
        }),
        ('Rate Limiting', {
            'fields': ['rate_limit_per_minute', 'rate_limit_per_hour', 'rate_limit_per_day']
        }),
        ('Security', {
            'fields': ['allowed_ips', 'expires_at']
        }),
        ('Usage Statistics', {
            'fields': ['total_requests', 'last_request_at', 'created_at', 'updated_at']
        })
    ]
    
    def is_active_display(self, obj):
        if obj.is_active:
            return format_html('<span style="color: green;">✓ Active</span>')
        return format_html('<span style="color: red;">✗ Inactive</span>')
    is_active_display.short_description = 'Status'


@admin.register(APIKey)
class APIKeyAdmin(admin.ModelAdmin):
    list_display = ['name', 'api_user', 'key_prefix', 'status', 'total_requests', 'last_used_at', 'created_at', 'is_active_display']
    list_filter = ['status', 'created_at', 'last_used_at']
    search_fields = ['name', 'key_prefix', 'api_user__name']
    readonly_fields = ['id', 'key_prefix', 'key_hash', 'total_requests', 'last_used_at', 'created_at']
    
    fieldsets = [
        ('Key Information', {
            'fields': ['id', 'api_user', 'name', 'status']
        }),
        ('Key Data', {
            'fields': ['key_prefix', 'key_hash'],
            'description': 'The actual API key is never stored. Only the hash is kept for verification.'
        }),
        ('Lifecycle', {
            'fields': ['created_at', 'expires_at', 'last_used_at']
        }),
        ('Usage', {
            'fields': ['total_requests']
        }),
        ('Metadata', {
            'fields': ['metadata'],
            'classes': ['collapse']
        })
    ]
    
    def is_active_display(self, obj):
        if obj.is_active:
            return format_html('<span style="color: green;">✓ Active</span>')
        return format_html('<span style="color: red;">✗ Inactive</span>')
    is_active_display.short_description = 'Active'


@admin.register(ActiveToken)
class ActiveTokenAdmin(admin.ModelAdmin):
    list_display = ['token_short', 'api_key', 'ip_address', 'request_count', 'max_uses', 'created_at', 'expires_at', 'is_valid_display']
    list_filter = ['is_revoked', 'created_at', 'expires_at']
    search_fields = ['token', 'ip_address', 'api_key__name']
    readonly_fields = ['token', 'created_at', 'ip_address', 'user_agent', 'request_count']
    
    fieldsets = [
        ('Token Information', {
            'fields': ['token', 'api_key', 'is_revoked']
        }),
        ('Security', {
            'fields': ['ip_address', 'user_agent']
        }),
        ('Lifecycle', {
            'fields': ['created_at', 'expires_at', 'last_used_at']
        }),
        ('Usage Limits', {
            'fields': ['request_count', 'max_uses']
        })
    ]
    
    def token_short(self, obj):
        return f"{obj.token[:20]}..."
    token_short.short_description = 'Token'
    
    def is_valid_display(self, obj):
        if obj.is_valid:
            return format_html('<span style="color: green;">✓ Valid</span>')
        return format_html('<span style="color: red;">✗ Invalid</span>')
    is_valid_display.short_description = 'Valid'


class ColumnRestrictionInline(admin.TabularInline):
    model = ColumnRestriction
    extra = 1


@admin.register(TablePermission)
class TablePermissionAdmin(admin.ModelAdmin):
    list_display = ['api_user', 'table_name', 'can_read', 'can_filter', 'can_aggregate', 'max_records_per_request', 'created_at']
    list_filter = ['can_read', 'can_filter', 'can_aggregate', 'created_at']
    search_fields = ['api_user__name', 'table_name']
    inlines = [ColumnRestrictionInline]
    
    fieldsets = [
        ('Permission', {
            'fields': ['api_user', 'table_name']
        }),
        ('Access Control', {
            'fields': ['can_read', 'can_filter', 'can_aggregate']
        }),
        ('Limits', {
            'fields': ['max_records_per_request']
        }),
        ('Timestamps', {
            'fields': ['created_at', 'updated_at'],
            'classes': ['collapse']
        })
    ]
    
    readonly_fields = ['created_at', 'updated_at']


@admin.register(ColumnRestriction)
class ColumnRestrictionAdmin(admin.ModelAdmin):
    list_display = ['table_permission', 'column_name', 'restriction_type', 'created_at']
    list_filter = ['restriction_type', 'created_at']
    search_fields = ['table_permission__table_name', 'column_name']
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related('table_permission__api_user')


@admin.register(APIRequestLog)
class APIRequestLogAdmin(admin.ModelAdmin):
    list_display = ['timestamp', 'api_key_name', 'endpoint', 'method', 'status_code', 'response_time_ms', 'records_returned', 'is_suspicious']
    list_filter = ['status_code', 'method', 'is_suspicious', 'timestamp']
    search_fields = ['endpoint', 'ip_address', 'api_key__name']
    readonly_fields = ['id', 'api_key', 'active_token', 'endpoint', 'method', 'ip_address', 'user_agent', 
                       'query_params', 'request_body', 'status_code', 'response_time_ms', 
                       'response_size_bytes', 'records_returned', 'error_message', 'is_suspicious', 
                       'security_flags', 'timestamp']
    
    fieldsets = [
        ('Request Information', {
            'fields': ['id', 'api_key', 'active_token', 'endpoint', 'method', 'timestamp']
        }),
        ('Client Information', {
            'fields': ['ip_address', 'user_agent']
        }),
        ('Request Data', {
            'fields': ['query_params', 'request_body'],
            'classes': ['collapse']
        }),
        ('Response Data', {
            'fields': ['status_code', 'response_time_ms', 'response_size_bytes', 'records_returned']
        }),
        ('Error Information', {
            'fields': ['error_message'],
            'classes': ['collapse']
        }),
        ('Security', {
            'fields': ['is_suspicious', 'security_flags'],
            'classes': ['collapse']
        })
    ]
    
    def api_key_name(self, obj):
        return obj.api_key.name if obj.api_key else 'Unknown'
    api_key_name.short_description = 'API Key'
    
    def has_add_permission(self, request):
        return False
    
    def has_change_permission(self, request, obj=None):
        return False


@admin.register(RateLimitTracker)
class RateLimitTrackerAdmin(admin.ModelAdmin):
    list_display = ['api_key', 'period', 'period_start', 'request_count', 'last_request_at']
    list_filter = ['period', 'period_start']
    search_fields = ['api_key__name']
    readonly_fields = ['api_key', 'period', 'period_start', 'request_count', 'last_request_at']
    
    def has_add_permission(self, request):
        return False
    
    def has_change_permission(self, request, obj=None):
        return False
