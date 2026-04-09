from django.urls import path
from . import views

app_name = 'ticketing'

urlpatterns = [
    # Dashboard (must come before <uuid:pk>/ to avoid conflict)
    path('dashboard/', views.TicketDashboardView.as_view(), name='ticket_dashboard'),
    path('dashboard/react/', views.ticket_dashboard_react_view, name='ticket_dashboard_react'),
    path('dashboard/api/', views.DashboardAPIView.as_view(), name='dashboard_api'),
    path('ajax/analytics-widget/', views.analytics_widget, name='analytics_widget'),
    path('ajax/filter/', views.ajax_filter_dashboard, name='ajax_filter_dashboard'),
    path('export/widget/csv/', views.export_widget_csv, name='export_widget_csv'),
    path('export/widget/excel/', views.export_widget_excel, name='export_widget_excel'),
    
    # Ticket Management
    path('', views.TicketListView.as_view(), name='ticket_list'),
    path('my-tickets/', views.MyTicketsView.as_view(), name='my_tickets'),
    path('create/', views.TicketCreateView.as_view(), name='ticket_create'),
    
    # Admin/Settings (must come before <uuid:pk>/ to avoid conflict)
    path('admin/', views.ticketing_admin_view, name='ticketing_admin'),
    path('admin/ticket-category/create/', views.create_ticket_category, name='create_ticket_category'),
    path('admin/ticket-category/<int:pk>/edit/', views.edit_ticket_category, name='edit_ticket_category'),
    path('admin/ticket-category/<int:pk>/delete/', views.delete_ticket_category, name='delete_ticket_category'),
    path('admin/loss-category/create/', views.create_loss_category, name='create_loss_category'),
    path('admin/loss-category/<int:pk>/edit/', views.edit_loss_category, name='edit_loss_category'),
    path('admin/loss-category/<int:pk>/delete/', views.delete_loss_category, name='delete_loss_category'),
    
    # Preventive Maintenance Rules
    path('admin/pm-rule/create/', views.create_pm_rule, name='create_pm_rule'),
    path('admin/pm-rule/<int:pk>/edit/', views.edit_pm_rule, name='edit_pm_rule'),
    path('admin/pm-rule/<int:pk>/delete/', views.delete_pm_rule, name='delete_pm_rule'),
    path('admin/pm-rule/<int:pk>/toggle/', views.toggle_pm_rule, name='toggle_pm_rule'),
    path('admin/pm-rule/trigger/', views.trigger_pm_processing, name='trigger_pm_processing'),
    
    # API Endpoints (must come before <uuid:pk>/ to avoid conflict)
    path('api/sites/', views.api_get_sites, name='api_sites'),
    path('api/device-types/', views.api_get_device_types, name='api_device_types'),
    path('api/device-sub-groups/', views.api_get_device_sub_groups, name='api_device_sub_groups'),
    path('api/devices/', views.api_get_devices, name='api_devices'),
    path('api/stats/', views.api_get_ticket_stats, name='api_stats'),
    path('api/field-definitions/', views.api_get_field_definitions, name='api_field_definitions'),
    path('api/categories/', views.api_get_categories, name='api_categories'),
    path('api/loss-categories/', views.api_get_loss_categories, name='api_loss_categories'),
    path('quickview/<uuid:pk>/', views.ticket_quickview, name='ticket_quickview'),
    
    # Ticket Detail and Actions (must come LAST due to <uuid:pk>/ catch-all pattern)
    path('<uuid:pk>/', views.TicketDetailView.as_view(), name='ticket_detail'),
    path('<uuid:pk>/edit/', views.TicketUpdateView.as_view(), name='ticket_edit'),
    path('<uuid:pk>/delete/', views.delete_ticket, name='ticket_delete'),
    path('<uuid:pk>/watchers/', views.update_watchers, name='ticket_update_watchers'),
    path('<uuid:pk>/close/', views.close_ticket, name='ticket_close'),
    path('<uuid:pk>/reopen/', views.reopen_ticket, name='ticket_reopen'),
    path('<uuid:pk>/comment/', views.add_comment, name='ticket_comment'),
    path('<uuid:pk>/attachment/', views.upload_attachment, name='ticket_attachment_upload'),
    path('<uuid:pk>/attachment/<int:attachment_id>/delete/', views.delete_attachment, name='ticket_attachment_delete'),
    path('<uuid:pk>/assign/', views.assign_ticket, name='ticket_assign'),
    path('<uuid:pk>/status-change/', views.change_ticket_status, name='ticket_status_change'),
    path('<uuid:pk>/scheduled-times/', views.update_scheduled_times, name='ticket_update_scheduled_times'),
    path('<uuid:pk>/analytics/', views.update_analytics, name='ticket_update_analytics'),
]

