from django.urls import path

from . import api_views
from . import pre_feasibility_api
from . import views

app_name = 'engineering_tools'

urlpatterns = [
    path('', views.index_view, name='index'),
    path('api/solargis-monthly/', api_views.SolargisMonthlyView.as_view(), name='api_solargis_monthly'),
    path('api/manual-dc-yield/', api_views.ManualDCYieldView.as_view(), name='api_manual_dc_yield'),
    path('api/projects/', pre_feasibility_api.ProjectGetOrCreateView.as_view(), name='api_projects'),
    path(
        'api/pre-feasibility/site-orientation/<int:project_id>/',
        pre_feasibility_api.SiteOrientationView.as_view(),
        name='api_site_orientation',
    ),
    path(
        'api/pre-feasibility/module-assumptions/<int:project_id>/',
        pre_feasibility_api.ModuleAssumptionsView.as_view(),
        name='api_module_assumptions',
    ),
    path(
        'api/pre-feasibility/string-configuration/<int:project_id>/',
        pre_feasibility_api.StringConfigurationView.as_view(),
        name='api_string_configuration',
    ),
    path(
        'api/pre-feasibility/module-master/',
        pre_feasibility_api.ModuleMasterListView.as_view(),
        name='api_module_master',
    ),
    path(
        'api/pre-feasibility/inverter-master/',
        pre_feasibility_api.InverterMasterListView.as_view(),
        name='api_inverter_master',
    ),
    path(
        'api/pre-feasibility/export-layout-kml/',
        pre_feasibility_api.ExportLayoutKmlView.as_view(),
        name='api_export_layout_kml',
    ),
]
