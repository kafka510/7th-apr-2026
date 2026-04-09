from django.contrib import admin

from .models import Capability, Feature, LoginAttempt, Role

# Register your models here.

@admin.register(LoginAttempt)
class LoginAttemptAdmin(admin.ModelAdmin):
    list_display = ['username', 'ip_address', 'attempt_time', 'successful']
    list_filter = ['successful', 'attempt_time']
    search_fields = ['username', 'ip_address']
    readonly_fields = ['username', 'ip_address', 'attempt_time', 'successful']
    
    def has_add_permission(self, request):
        return False
    
    def has_change_permission(self, request, obj=None):
        return False


@admin.register(Feature)
class FeatureAdmin(admin.ModelAdmin):
    list_display = ("key", "name", "category", "is_active", "ordering")
    list_filter = ("is_active", "category")
    search_fields = ("key", "name")
    ordering = ("ordering", "name")


@admin.register(Capability)
class CapabilityAdmin(admin.ModelAdmin):
    list_display = ("key", "name", "category", "is_active")
    list_filter = ("is_active", "category")
    search_fields = ("key", "name", "category")
    ordering = ("category", "name")


@admin.register(Role)
class RoleAdmin(admin.ModelAdmin):
    list_display = ("key", "name", "is_active", "ordering")
    list_filter = ("is_active",)
    search_fields = ("key", "name", "description")
    ordering = ("ordering", "name")
