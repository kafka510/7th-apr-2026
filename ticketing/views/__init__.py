# Views package for ticketing app
# Import order matters to avoid circular dependencies
from .admin_views import (
    ticketing_admin_view,
    create_ticket_category, edit_ticket_category, delete_ticket_category,
    create_loss_category, edit_loss_category, delete_loss_category,
    create_pm_rule, edit_pm_rule, delete_pm_rule, toggle_pm_rule,
    trigger_pm_processing
)
from .api_views import (
    api_get_sites, api_get_device_types, api_get_device_sub_groups,
    api_get_devices, api_get_ticket_stats, api_get_field_definitions,
    api_get_categories, api_get_loss_categories, ticket_quickview
)
from .dashboard_views import TicketDashboardView, DashboardAPIView, analytics_widget, ajax_filter_dashboard, export_widget_csv, export_widget_excel, ticket_dashboard_react_view
from .ticket_views import (
    TicketListView, MyTicketsView, TicketCreateView, TicketDetailView, TicketUpdateView,
    add_comment, assign_ticket, close_ticket, reopen_ticket, change_ticket_status,
    upload_attachment, delete_attachment, delete_ticket, update_watchers, update_scheduled_times, update_analytics
)

