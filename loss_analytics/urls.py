"""
URL configuration for loss_analytics API.

Mount under e.g. path('api/loss/', include('loss_analytics.urls')) in root urlconf.
"""
from django.urls import path
from . import views

app_name = "loss_analytics"

urlpatterns = [
    path("transpose/", views.api_transpose_trigger, name="transpose_trigger"),
    path("asset/range/", views.api_asset_range_trigger, name="asset_range_trigger"),
    path("inverter/expected-power/", views.api_inverter_expected_power_trigger, name="inverter_expected_power_trigger"),
    path("task/<str:task_id>/", views.api_task_status, name="task_status"),
    path("results/", views.api_get_loss_results, name="results"),
    path("summary/", views.api_get_loss_summary, name="summary"),
    path("metric-mappings/", views.api_get_metric_mappings, name="metric_mappings"),
    path("events/", views.api_loss_events_list, name="loss_events_list"),
    path("events/update-legitimacy/", views.api_loss_event_update_legitimacy, name="loss_event_update_legitimacy"),
    path("events/<int:event_id>/logs/", views.api_loss_event_logs, name="loss_event_logs"),
]
