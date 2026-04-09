"""
API URL Configuration
---------------------
URL patterns for all API endpoints
"""

from django.urls import path
from . import views, admin_views

app_name = 'api'

urlpatterns = [
    # API Manual (For API-only users)
    path('manual/', views.api_manual, name='api_manual'),
    
    # API Management Dashboard (User)
    path('dashboard/', views.api_dashboard, name='dashboard'),
    path('keys/generate/', views.generate_api_key, name='generate_key'),
    path('keys/<uuid:key_id>/revoke/', views.revoke_api_key, name='revoke_key'),
    
    # Web API endpoints for React
    path('web/user-info/', views.api_user_info, name='api_user_info'),
    path('web/keys/', views.list_api_keys, name='list_api_keys'),
    
    # API Configuration (Admin Only)
    path('admin/config/', admin_views.api_config_dashboard, name='api_config_dashboard'),
    # User creation now handled in User Management page
    # path('admin/create-user/', admin_views.create_api_user, name='create_api_user'),
    path('admin/setup-permissions/', admin_views.setup_api_permissions, name='setup_api_permissions'),
    path('admin/manage-users/', admin_views.manage_api_users, name='manage_api_users'),
    path('admin/users/<int:user_id>/', admin_views.view_api_user, name='view_api_user'),
    path('admin/generate-key/', admin_views.generate_key_for_user, name='generate_key_for_user'),
    path('admin/grant-table-access/', admin_views.grant_table_access, name='grant_table_access'),
    path('admin/restrict-columns/', admin_views.restrict_columns, name='restrict_columns'),
    path('admin/revoke-key/<uuid:key_id>/', admin_views.revoke_api_key_admin, name='revoke_api_key_admin'),
    path('admin/toggle-status/<int:user_id>/', admin_views.toggle_api_user_status, name='toggle_api_user_status'),
    path('admin/delete-user/<int:api_user_id>/', admin_views.delete_api_user, name='delete_api_user'),
    path('admin/update-rate-limits/<int:user_id>/', admin_views.update_rate_limits, name='update_rate_limits'),
    path('admin/get-table-columns/', admin_views.get_table_columns, name='get_table_columns'),
    path('admin/logs/', admin_views.api_logs, name='api_logs'),
    path('admin/remove-restriction/<int:restriction_id>/', admin_views.remove_column_restriction, name='remove_column_restriction'),
    path('admin/revoke-table/<int:permission_id>/', admin_views.revoke_table_access, name='revoke_table_access'),
    path('admin/blocked-ips/', admin_views.blocked_ips_view, name='blocked_ips'),
    
    # Public Authentication Endpoints
    path('v1/auth/token', views.request_token, name='request_token'),
    
    # Schema Discovery Endpoints
    path('v1/schema/tables', views.list_tables, name='list_tables'),
    path('v1/schema/tables/<str:table_name>', views.get_table_schema, name='get_table_schema'),
    
    # Data Access Endpoints
    path('v1/data/<str:table_name>', views.get_table_data, name='get_table_data'),
    path('v1/data/<str:table_name>/aggregate', views.get_table_aggregate, name='get_table_aggregate'),
]

