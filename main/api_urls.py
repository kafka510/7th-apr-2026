from django.urls import path

from .api.kpi import KPIMetricsView, KPISummaryView
from .api.yield_report import YieldDataView
from .api.generation_report import generation_report_data_view
from .api.portfolio_map import portfolio_map_data_view
from .api.sales import sales_data_view
from .api.ic_budget import ic_budget_vs_expected_data_view

app_name = 'main_api'

# All API endpoints - included under different prefixes in web_app/urls.py
# KPI: /api/v1/kpi/metrics/, /api/v1/kpi/summary/
# Yield: /api/v1/yield/data/
# Generation: /api/v1/generation/data/
# Portfolio Map: /api/v1/portfolio-map/data/
# NOTE: When the same urlpatterns is included under multiple prefixes,
# Django processes patterns in order. To avoid conflicts, we need to ensure
# that patterns are unique or use separate URL files.
urlpatterns = [
    path('metrics/', KPIMetricsView.as_view(), name='kpi_metrics'),
    path('summary/', KPISummaryView.as_view(), name='kpi_summary'),
    # IMPORTANT: Order matters when same patterns exist - put generation first
    # since it's checked after yield in web_app/urls.py
    path('data/', generation_report_data_view, name='generation_report_data'),
    path('data/', YieldDataView.as_view(), name='yield_data'),
    # Portfolio Map endpoint - using unique path to avoid conflicts with other 'data/' routes
    path('map-data/', portfolio_map_data_view, name='portfolio_map_data'),
    # Sales endpoint - using unique path to avoid conflicts
    path('sales-data/', sales_data_view, name='sales_data'),
    # IC Budget vs Expected endpoint - using unique path to avoid conflicts
    path('ic-budget-data/', ic_budget_vs_expected_data_view, name='ic_budget_data'),
]
