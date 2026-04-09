from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils import timezone
from .models import (
    UserProfile, UserActivityLog, ActiveUserSession, SecurityAlert,
    Feedback, FeedbackImage, IPBlockingLog, UserBlockingLog, 
    BlockedIP, BlockedUser
)

@admin.register(UserProfile)
class MainUserProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'role', 'created_at')
    list_filter = ('role', 'created_at')
    search_fields = ('user__username', 'role')
    readonly_fields = ('created_at',)


@admin.register(UserActivityLog)
class UserActivityLogAdmin(admin.ModelAdmin):
    list_display = (
        'user', 'action', 'resource', 'ip_address', 'peer_ip', 'client_ip', 'timestamp', 'is_suspicious',
    )
    list_filter = ('action', 'is_suspicious', 'risk_level', 'timestamp')
    search_fields = ('user__username', 'ip_address', 'client_ip', 'peer_ip', 'forwarded_for', 'resource')
    readonly_fields = ('timestamp',)
    date_hierarchy = 'timestamp'
    
    def has_add_permission(self, request):
        return False  # Don't allow manual creation
    
    def has_change_permission(self, request, obj=None):
        return False  # Don't allow editing


@admin.register(ActiveUserSession)
class ActiveUserSessionAdmin(admin.ModelAdmin):
    list_display = ('user', 'ip_address', 'last_activity', 'is_active')
    list_filter = ('is_active', 'last_activity')
    search_fields = ('user__username', 'ip_address')
    readonly_fields = ('created_at', 'last_activity')
    
    def has_add_permission(self, request):
        return False  # Don't allow manual creation


@admin.register(SecurityAlert)
class SecurityAlertAdmin(admin.ModelAdmin):
    list_display = ('title', 'alert_type', 'severity', 'status', 'user', 'ip_address', 'created_at')
    list_filter = ('alert_type', 'severity', 'status', 'created_at')
    search_fields = ('title', 'user__username', 'ip_address')
    readonly_fields = ('created_at', 'updated_at')
    date_hierarchy = 'created_at'
    
    fieldsets = (
        ('Alert Information', {
            'fields': ('alert_type', 'severity', 'status', 'title', 'description')
        }),
        ('Source Information', {
            'fields': ('user', 'ip_address', 'user_agent')
        }),
        ('Resolution', {
            'fields': ('resolved_by', 'resolved_at', 'resolution_notes')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(Feedback)
class FeedbackAdmin(admin.ModelAdmin):
    list_display = ('user', 'subject', 'attended_status', 'created_at')
    list_filter = ('attended_status', 'created_at')
    search_fields = ('user__username', 'subject', 'message')
    readonly_fields = ('created_at',)


@admin.register(FeedbackImage)
class FeedbackImageAdmin(admin.ModelAdmin):
    list_display = ('feedback', 'created_at')
    readonly_fields = ('created_at',)


@admin.register(IPBlockingLog)
class IPBlockingLogAdmin(admin.ModelAdmin):
    list_display = ('ip_address', 'block_reason', 'block_type', 'status', 'blocked_at', 'is_active_display')
    list_filter = ('block_type', 'block_reason', 'status', 'blocked_at', 'country')
    search_fields = ('ip_address', 'reason_details', 'user_agent')
    readonly_fields = ('blocked_at', 'unblocked_at')
    date_hierarchy = 'blocked_at'
    
    fieldsets = (
        ('Blocking Information', {
            'fields': ('ip_address', 'block_type', 'block_reason', 'reason_details', 'status')
        }),
        ('Context Information', {
            'fields': ('user_agent', 'country', 'city', 'region')
        }),
        ('Blocking Details', {
            'fields': ('blocked_by', 'blocked_at', 'expires_at', 'failed_attempts', 'suspicious_activities')
        }),
        ('Resolution', {
            'fields': ('unblocked_by', 'unblocked_at', 'unblock_reason'),
            'classes': ('collapse',)
        }),
        ('Metadata', {
            'fields': ('metadata',),
            'classes': ('collapse',)
        }),
    )
    
    def is_active_display(self, obj):
        if obj.is_active:
            return format_html('<span style="color: red;">● Active</span>')
        else:
            return format_html('<span style="color: green;">● Inactive</span>')
    is_active_display.short_description = 'Status'
    
    def has_add_permission(self, request):
        return False  # Don't allow manual creation of logs


@admin.register(UserBlockingLog)
class UserBlockingLogAdmin(admin.ModelAdmin):
    list_display = ('user', 'block_reason', 'block_type', 'status', 'blocked_at', 'is_active_display')
    list_filter = ('block_type', 'block_reason', 'status', 'blocked_at', 'country')
    search_fields = ('user__username', 'reason_details', 'user_agent', 'ip_address')
    readonly_fields = ('blocked_at', 'unblocked_at')
    date_hierarchy = 'blocked_at'
    
    fieldsets = (
        ('Blocking Information', {
            'fields': ('user', 'block_type', 'block_reason', 'reason_details', 'status')
        }),
        ('Context Information', {
            'fields': ('ip_address', 'user_agent', 'country', 'city')
        }),
        ('Blocking Details', {
            'fields': ('blocked_by', 'blocked_at', 'expires_at', 'failed_attempts', 'suspicious_activities')
        }),
        ('Resolution', {
            'fields': ('unblocked_by', 'unblocked_at', 'unblock_reason'),
            'classes': ('collapse',)
        }),
        ('Metadata', {
            'fields': ('metadata',),
            'classes': ('collapse',)
        }),
    )
    
    def is_active_display(self, obj):
        if obj.is_active:
            return format_html('<span style="color: red;">● Active</span>')
        else:
            return format_html('<span style="color: green;">● Inactive</span>')
    is_active_display.short_description = 'Status'
    
    def has_add_permission(self, request):
        return False  # Don't allow manual creation of logs


@admin.register(BlockedIP)
class BlockedIPAdmin(admin.ModelAdmin):
    list_display = ('ip_address', 'reason', 'status', 'priority', 'created_at', 'is_active_display', 'block_count')
    list_filter = ('status', 'priority', 'created_at', 'expires_at')
    search_fields = ('ip_address', 'reason', 'description')
    readonly_fields = ('created_at', 'updated_at', 'block_count')
    date_hierarchy = 'created_at'
    
    fieldsets = (
        ('IP Information', {
            'fields': ('ip_address', 'status', 'priority')
        }),
        ('Blocking Details', {
            'fields': ('reason', 'description', 'blocked_by', 'expires_at')
        }),
        ('Statistics', {
            'fields': ('block_count', 'last_seen'),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
        ('Metadata', {
            'fields': ('metadata',),
            'classes': ('collapse',)
        }),
    )
    
    def is_active_display(self, obj):
        if obj.is_active:
            return format_html('<span style="color: red;">● Active</span>')
        else:
            return format_html('<span style="color: green;">● Inactive</span>')
    is_active_display.short_description = 'Status'
    
    actions = ['unblock_ips', 'extend_block', 'whitelist_ips']
    
    def unblock_ips(self, request, queryset):
        updated = queryset.update(status='inactive', updated_at=timezone.now())
        # Clear failed login attempts from blocked IPs
        from accounts.models import LoginAttempt
        ip_addresses = list(queryset.values_list('ip_address', flat=True))
        cleared_count = 0
        if ip_addresses:
            deleted = LoginAttempt.objects.filter(
                ip_address__in=ip_addresses,
                successful=False
            ).delete()[0]
            cleared_count = deleted
        self.message_user(
            request, 
            f'{updated} IP(s) have been unblocked and {cleared_count} failed login attempt(s) cleared.'
        )
    unblock_ips.short_description = "Unblock selected IPs (clears failed attempts)"
    
    def extend_block(self, request, queryset):
        # Extend block by 24 hours
        new_expiry = timezone.now() + timezone.timedelta(hours=24)
        updated = queryset.update(expires_at=new_expiry)
        self.message_user(request, f'{updated} IP block(s) have been extended by 24 hours.')
    extend_block.short_description = "Extend block by 24 hours"
    
    def whitelist_ips(self, request, queryset):
        updated = queryset.update(status='whitelisted', updated_at=timezone.now())
        self.message_user(request, f'{updated} IP(s) have been whitelisted.')
    whitelist_ips.short_description = "Whitelist selected IPs"


@admin.register(BlockedUser)
class BlockedUserAdmin(admin.ModelAdmin):
    list_display = ('user', 'reason', 'status', 'priority', 'created_at', 'is_active_display', 'block_count')
    list_filter = ('status', 'priority', 'created_at', 'expires_at')
    search_fields = ('user__username', 'reason', 'description')
    readonly_fields = ('created_at', 'updated_at', 'block_count')
    date_hierarchy = 'created_at'
    
    fieldsets = (
        ('User Information', {
            'fields': ('user', 'status', 'priority')
        }),
        ('Blocking Details', {
            'fields': ('reason', 'description', 'blocked_by', 'expires_at')
        }),
        ('Statistics', {
            'fields': ('block_count', 'last_seen'),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
        ('Metadata', {
            'fields': ('metadata',),
            'classes': ('collapse',)
        }),
    )
    
    def is_active_display(self, obj):
        if obj.is_active:
            return format_html('<span style="color: red;">● Active</span>')
        else:
            return format_html('<span style="color: green;">● Inactive</span>')
    is_active_display.short_description = 'Status'
    
    actions = ['unblock_users', 'extend_block', 'whitelist_users']
    
    def unblock_users(self, request, queryset):
        updated = queryset.update(status='inactive', updated_at=timezone.now())
        # Also reactivate the user accounts and clear failed login attempts
        from accounts.models import LoginAttempt
        from main.middleware.realtime_ip_blocker import realtime_blocker
        cleared_count = 0
        for blocked_user in queryset:
            username = blocked_user.user.username
            blocked_user.user.is_active = True
            blocked_user.user.save()
            # Invalidate cache to force reload
            realtime_blocker._invalidate_cache()
            # Clear all failed login attempts for this user
            deleted = LoginAttempt.objects.filter(
                username=username,
                successful=False
            ).delete()[0]
            cleared_count += deleted
        self.message_user(
            request, 
            f'{updated} user(s) have been unblocked, accounts reactivated, cache cleared, and {cleared_count} failed login attempt(s) cleared.'
        )
    unblock_users.short_description = "Unblock selected users (clears failed attempts and cache)"
    
    def extend_block(self, request, queryset):
        # Extend block by 24 hours
        new_expiry = timezone.now() + timezone.timedelta(hours=24)
        updated = queryset.update(expires_at=new_expiry)
        self.message_user(request, f'{updated} user block(s) have been extended by 24 hours.')
    extend_block.short_description = "Extend block by 24 hours"
    
    def whitelist_users(self, request, queryset):
        updated = queryset.update(status='whitelisted', updated_at=timezone.now())
        # Also reactivate the user accounts and clear failed login attempts
        from accounts.models import LoginAttempt
        from main.middleware.realtime_ip_blocker import realtime_blocker
        cleared_count = 0
        for blocked_user in queryset:
            username = blocked_user.user.username
            blocked_user.user.is_active = True
            blocked_user.user.save()
            # Invalidate cache to force reload
            realtime_blocker._invalidate_cache()
            # Clear all failed login attempts for this user
            deleted = LoginAttempt.objects.filter(
                username=username,
                successful=False
            ).delete()[0]
            cleared_count += deleted
        self.message_user(
            request, 
            f'{updated} user(s) have been whitelisted, accounts reactivated, cache cleared, and {cleared_count} failed login attempt(s) cleared.'
        )
    whitelist_users.short_description = "Whitelist selected users (clears failed attempts and cache)"