"""
Shared app URL Configuration
"""
from django.urls import path
from . import views

app_name = 'shared'

urlpatterns = [
    # Dashboard Export (Server-side screenshot - Async)
    # IMPORTANT: More specific patterns must come first
    # Support both with and without trailing slash
    path('export/dashboard/status/<str:task_id>/', views.export_dashboard_status, name='export_dashboard_status'),
    path('export/dashboard/status/<str:task_id>', views.export_dashboard_status, name='export_dashboard_status_no_slash'),
    path('export/dashboard/download/<str:task_id>/', views.export_dashboard_download, name='export_dashboard_download'),
    path('export/dashboard/download/<str:task_id>', views.export_dashboard_download, name='export_dashboard_download_no_slash'),
    path('export/dashboard/', views.export_dashboard, name='export_dashboard'),
]

