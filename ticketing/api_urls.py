from django.urls import path

from .api.dashboard import (
    TicketDashboardAnalyticsView,
    TicketDashboardFiltersView,
    TicketDashboardRecentView,
    TicketDashboardSummaryView,
)
from .api.detail import (
    TicketAssignAPIView,
    TicketAttachmentsAPIView,
    TicketCommentsAPIView,
    TicketDeleteAPIView,
    TicketDetailAPIView,
    TicketMaterialsAPIView,
    TicketMaterialDetailAPIView,
    TicketManpowerAPIView,
    TicketManpowerDetailAPIView,
    TicketStatusChangeAPIView,
    TicketTimelineAPIView,
    TicketWatchersAPIView,
)
from .api.form import (
    TicketCreateAPIView,
    TicketDeviceOptionsAPIView,
    TicketFormOptionsAPIView,
    TicketLocationOptionsAPIView,
    TicketUpdateAPIView,
)
from .api.list import TicketListAPIView
from .api.admin import (
    loss_categories_list,
    loss_category_create,
    loss_category_delete,
    loss_category_update,
    pm_rule_create,
    pm_rule_delete,
    pm_rule_detail,
    pm_rule_toggle,
    pm_rule_trigger,
    pm_rules_list,
    pm_rule_update,
    ticket_categories_list,
    ticket_category_create,
    ticket_category_delete,
    ticket_category_update,
    ticket_subcategories_list,
    ticket_subcategory_create,
    ticket_subcategory_delete,
    ticket_subcategory_update,
)

app_name = "ticketing_api"

urlpatterns = [
    path("dashboard/", TicketDashboardSummaryView.as_view(), name="dashboard"),
    path("dashboard/filters/", TicketDashboardFiltersView.as_view(), name="dashboard_filters"),
    path("dashboard/recent/", TicketDashboardRecentView.as_view(), name="dashboard_recent"),
    path("dashboard/analytics/", TicketDashboardAnalyticsView.as_view(), name="dashboard_analytics"),
    path("tickets/", TicketListAPIView.as_view(), name="tickets"),
    path("tickets/<uuid:pk>/", TicketDetailAPIView.as_view(), name="ticket_detail"),
    path("tickets/<uuid:pk>/timeline/", TicketTimelineAPIView.as_view(), name="ticket_timeline"),
    path("tickets/<uuid:pk>/comments/", TicketCommentsAPIView.as_view(), name="ticket_comments"),
    path("tickets/<uuid:pk>/attachments/", TicketAttachmentsAPIView.as_view(), name="ticket_attachments"),
    path("tickets/<uuid:pk>/materials/", TicketMaterialsAPIView.as_view(), name="ticket_materials"),
    path("tickets/<uuid:pk>/materials/<uuid:material_id>/", TicketMaterialDetailAPIView.as_view(), name="ticket_material_detail"),
    path("tickets/<uuid:pk>/manpower/", TicketManpowerAPIView.as_view(), name="ticket_manpower"),
    path("tickets/<uuid:pk>/manpower/<uuid:manpower_id>/", TicketManpowerDetailAPIView.as_view(), name="ticket_manpower_detail"),
    path("tickets/<uuid:pk>/assign/", TicketAssignAPIView.as_view(), name="ticket_assign"),
    path("tickets/<uuid:pk>/watchers/", TicketWatchersAPIView.as_view(), name="ticket_watchers"),
    path("tickets/<uuid:pk>/status/", TicketStatusChangeAPIView.as_view(), name="ticket_status_change"),
    path("tickets/<uuid:pk>/delete/", TicketDeleteAPIView.as_view(), name="ticket_delete"),
    path("tickets/form/options/", TicketFormOptionsAPIView.as_view(), name="form_options"),
    path("tickets/form/devices/", TicketDeviceOptionsAPIView.as_view(), name="device_options"),
    path("tickets/form/locations/", TicketLocationOptionsAPIView.as_view(), name="location_options"),
    path("tickets/create/", TicketCreateAPIView.as_view(), name="ticket_create"),
    path("tickets/<uuid:pk>/update/", TicketUpdateAPIView.as_view(), name="ticket_update"),
    # Admin endpoints
    path("admin/ticket-categories/", ticket_categories_list, name="admin_ticket_categories"),
    path("admin/ticket-categories/create/", ticket_category_create, name="admin_ticket_category_create"),
    path("admin/ticket-categories/<int:pk>/", ticket_category_update, name="admin_ticket_category_update"),
    path("admin/ticket-categories/<int:pk>/delete/", ticket_category_delete, name="admin_ticket_category_delete"),
    path("admin/ticket-sub-categories/", ticket_subcategories_list, name="admin_ticket_subcategories"),
    path("admin/ticket-sub-categories/create/", ticket_subcategory_create, name="admin_ticket_subcategory_create"),
    path("admin/ticket-sub-categories/<int:pk>/", ticket_subcategory_update, name="admin_ticket_subcategory_update"),
    path("admin/ticket-sub-categories/<int:pk>/delete/", ticket_subcategory_delete, name="admin_ticket_subcategory_delete"),
    path("admin/loss-categories/", loss_categories_list, name="admin_loss_categories"),
    path("admin/loss-categories/create/", loss_category_create, name="admin_loss_category_create"),
    path("admin/loss-categories/<int:pk>/", loss_category_update, name="admin_loss_category_update"),
    path("admin/loss-categories/<int:pk>/delete/", loss_category_delete, name="admin_loss_category_delete"),
    path("admin/pm-rules/", pm_rules_list, name="admin_pm_rules"),
    path("admin/pm-rules/<int:pk>/", pm_rule_detail, name="admin_pm_rule_detail"),
    path("admin/pm-rules/create/", pm_rule_create, name="admin_pm_rule_create"),
    path("admin/pm-rules/<int:pk>/update/", pm_rule_update, name="admin_pm_rule_update"),
    path("admin/pm-rules/<int:pk>/delete/", pm_rule_delete, name="admin_pm_rule_delete"),
    path("admin/pm-rules/<int:pk>/toggle/", pm_rule_toggle, name="admin_pm_rule_toggle"),
    path("admin/pm-rules/trigger/", pm_rule_trigger, name="admin_pm_rule_trigger"),
]



