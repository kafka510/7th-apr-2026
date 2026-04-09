from django.urls import path, include

#from .views import api_views
from . import views
from loss_analytics import views as loss_analytics_views
from .api.yield_report import YieldDataView
from django.contrib.auth.views import LogoutView
from django.contrib.auth import views as auth_views

app_name = 'main'

urlpatterns = [
        
    # Main views
    path('', views.home_view, name='home'),
    #path('csrf-test/', views.csrf_test_view, name='csrf_test'),
    path('simple-csrf-test/', views.simple_csrf_test_view, name='simple_csrf_test'),
    path('dashboard/', views.dashboard_view, name='dashboard'),
    path('unified-operations-dashboard/', views.unified_operations_dashboard_view, name='unified_operations_dashboard'),
    path('api/unified-dashboard/data/', views.api_unified_dashboard_data, name='api_unified_dashboard_data'),
    path('portfolio-map/', views.portfolio_map_view, name='portfolio_map'),
    path('yield-report/', views.yield_report_view, name='yield_report'),
    path('yield-drilldown/<str:category>/', views.yield_drilldown_view, name='yield_drilldown'),
    #path('yield-report-edited/', views.yield_report_edited_view, name='yield_report_edited'),
    path('react-demo/', views.react_demo_view, name='react_demo'),
    path('pr-gap/', views.pr_gap_view, name='pr_gap'),
    path('revenue-loss/', views.revenue_loss_view, name='revenue_loss'),
    path('areas-of-concern/', views.areas_of_concern_view, name='areas_of_concern'),
    path('bess-performance/', views.bess_performance_view, name='bess_performance'),
    path('bess-v1-performance/', views.bess_v1_performance_view, name='bess_v1_performance'),
    path('minamata-typhoon-damage/', views.minamata_typhoon_damage_view, name='minamata_typhoon_damage'),
    path('ic-budget-vs-expected/', views.ic_budget_vs_expected_view, name='ic_budget_vs_expected'),
    path('kpi-dashboard/', views.kpi_dashboard_view, name='kpi_dashboard'),
    path('sales/', views.sales_dashboard_view, name='sales'),
    path('generation-report/', views.generation_report_view, name='generation_report'),
    #path('main-dashboard/', views.main_dashboard_view, name='main_dashboard'),
    path('data-upload/', views.data_upload_view, name='data_upload'),
    path('data-upload-help/', views.data_upload_help_view, name='data_upload_help'),
    path('time-series-dashboard/', views.time_series_dashboard_view, name='time_series_dashboard'),
    path('analytics/', views.analytics_view, name='analytics'),
    path('calculation-test/', views.calculation_test_view, name='calculation_test'),
    path('user-management/', views.user_management_view, name='user_management'),
    path('api/user-management/data/', views.api_user_management_data, name='api_user_management_data'),
    path('api/user-management/create/', views.api_create_user, name='api_create_user'),
    # Flag management endpoints (superuser only)
    path('user-management/flags/create/', views.create_flag, name='create_flag'),
    path('user-management/flags/<int:flag_id>/update/', views.update_flag, name='update_flag'),
    path('user-management/flags/<int:flag_id>/delete/', views.delete_flag, name='delete_flag'),
    path('user-management/flags/export-csv/', views.export_flags_csv, name='export_flags_csv'),
    path('user-management/flags/import-csv/', views.import_flags_csv, name='import_flags_csv'),
    path('user-management/flags/assign-to-user/', views.assign_flags_to_user, name='assign_flags_to_user'),
    path('edit-user-access/<int:user_id>/', views.edit_user_access, name='edit_user_access'),
    path('send-password-reset/<int:user_id>/', views.send_password_reset, name='send_password_reset'),
    path('api/user-activity/', views.user_activity_api, name='user_activity_api'),
    path('download-user-activity/', views.download_user_activity, name='download_user_activity'),
    path('download-user-activity-auto/', views.download_user_activity_auto, name='download_user_activity_auto'),
    path('download-page/', views.download_page, name='download_page'),
    path('security-alerts/', views.security_alerts_view, name='security_alerts'),
    path('security/delete-user/', views.delete_user_permanent, name='delete_user_permanent'),
    path('security/deactivate-user/', views.deactivate_user, name='deactivate_user'),
    path('security/reactivate-user/', views.reactivate_user, name='reactivate_user'),
    path('user-management/logs/', views.user_management_logs, name='user_management_logs'),
    path('user-management/blocking-logs/', views.user_blocking_logs_view, name='user_blocking_logs'),
    
    # Background Jobs (django-celery-beat, superuser only)
    path('background-jobs/', views.background_jobs_view, name='background_jobs'),
    path('api/background-jobs/', views.api_background_jobs_data, name='api_background_jobs_data'),
    path('api/background-jobs/export/', views.api_background_jobs_export, name='api_background_jobs_export'),
    path('api/background-jobs/import/', views.api_background_jobs_import, name='api_background_jobs_import'),
    path('api/background-jobs/create/', views.api_create_background_job, name='api_create_background_job'),
    path('api/background-jobs/update/', views.api_update_background_job, name='api_update_background_job'),
    path('api/background-jobs/delete/<int:job_id>/', views.api_delete_background_job, name='api_delete_background_job'),
    path('api/background-jobs/run-now/<int:job_id>/', views.api_run_background_job_now, name='api_run_background_job_now'),
    path('api/background-jobs/run-task/', views.api_run_task_on_demand, name='api_run_task_on_demand'),
    path('api/background-jobs/solargis-source-assets/', views.api_solargis_source_assets, name='api_solargis_source_assets'),
    path('api/background-jobs/solargis-daily-api-calls/', views.api_solargis_daily_api_calls, name='api_solargis_daily_api_calls'),
    path('api/background-jobs/laplace-backfill-assets/', views.api_laplace_backfill_assets, name='api_laplace_backfill_assets'),
    path('api/background-jobs/fusion-solar-backfill-assets/', views.api_fusion_solar_backfill_assets, name='api_fusion_solar_backfill_assets'),
    path('api/background-jobs/fusion-solar-backfill-run/', views.api_fusion_solar_backfill_run, name='api_fusion_solar_backfill_run'),
    path('api/background-jobs/fusion-solar-oem-daily-kpi-run/', views.api_fusion_solar_oem_daily_kpi_run, name='api_fusion_solar_oem_daily_kpi_run'),
    path('api/background-jobs/tasks/', views.api_background_job_tasks, name='api_background_job_tasks'),
       
    # Site Onboarding URLs (Admin Only)
    path('site-onboarding/', views.site_onboarding_view, name='site_onboarding'),
    path('site-onboarding/wizard/', views.site_onboarding_wizard_view, name='site_onboarding_wizard'),
    path('api/site-onboarding/debug/', views.api_site_onboarding_debug, name='api_site_onboarding_debug'),
    path('api/budget-values/debug/', views.api_budget_values_debug, name='api_budget_values_debug'),
    
    
    # API endpoints
    
    # Analytics API endpoints
    path('api/analytics/devices/', views.api_analytics_devices, name='api_analytics_devices'),
    path('api/analytics/measurement-points/', views.api_analytics_measurement_points, name='api_analytics_measurement_points'),
    path('api/analytics/timeseries-data/', views.api_analytics_timeseries_data, name='api_analytics_timeseries_data'),
    path('api/analytics/device-types/', views.api_analytics_device_types, name='api_analytics_device_types'),
    path('api/analytics/download-csv/', views.api_analytics_download_csv, name='api_analytics_download_csv'),
        
    path('api/yield-data/', views.api_yield_data, name='api_yield_data'),
    path('api/yield-data-sales/', views.api_yield_data_sales, name='api_yield_data_sales'),
    # DRF API endpoint for React yield report
    path('api/v1/yield/data/', YieldDataView.as_view(), name='api_v1_yield_data'),
    path('api/bess-data/', views.api_bess_data, name='api_bess_data'),
    path('api/bess-v1-data/', views.api_bess_v1_data, name='api_bess_v1_data'),
    path('api/aoc-data/', views.api_aoc_data, name='api_aoc_data'),
    path('api/ice-data/', views.api_ice_data, name='api_ice_data'),
    path('api/map-data/', views.api_map_data, name='api_map_data'),
    path('api/minamata-string-loss-data/', views.api_minamata_string_loss_data, name='api_minamata_string_loss_data'),
    path('api/ic-approved-budget-daily/', views.api_ic_approved_budget_daily, name='api_ic_approved_budget_daily'),
    path('api/upload-csv/', views.api_upload_csv, name='api_upload_csv'),
    path('api/time-series-data/', views.api_time_series_data, name='api_time_series_data'),
    path('api/devices/', views.api_devices, name='api_devices'),
    path('api/metrics/', views.api_metrics, name='api_metrics'),
    path('api/sites/', views.api_sites, name='api_sites'),
    path('api/actual-generation-daily/', views.api_actual_generation_daily, name='api_actual_generation_daily'),
    path('api/expected-budget-daily/', views.api_expected_budget_daily, name='api_expected_budget_daily'),
    path('api/budget-gii-daily/', views.api_budget_gii_daily, name='api_budget_gii_daily'),
    path('api/actual-gii-daily/', views.api_actual_gii_daily, name='api_actual_gii_daily'),
    path('api/real-time-kpi-data/', views.api_real_time_kpi_data, name='api_real_time_kpi_data'),
    path('api/asset-options/', views.api_asset_options, name='api_asset_options'),
    
    # Site Onboarding API endpoints
    path('api/site-onboarding/asset-list/', views.api_asset_list_data, name='api_asset_list_data'),
    path('api/site-onboarding/device-list/', views.api_device_list_data, name='api_device_list_data'),
    path('api/site-onboarding/device-list-including-gii/', views.api_device_list_including_gii, name='api_device_list_including_gii'),
    path('api/site-onboarding/device-mapping/', views.api_device_mapping_data, name='api_device_mapping_data'),
    path('api/site-onboarding/device-operating-state/', views.api_device_operating_state_data, name='api_device_operating_state_data'),
    path('api/site-onboarding/budget-values/', views.api_budget_values_data, name='api_budget_values_data'),
    path('api/site-onboarding/upload/', views.upload_site_onboarding_data, name='upload_site_onboarding_data'),
    path('site-onboarding/download/<str:table_name>/', views.download_site_onboarding_data, name='download_site_onboarding_data'),
    path('site-onboarding/template/<str:table_name>/', views.download_site_onboarding_template, name='download_site_onboarding_template'),
    # Diagnostic endpoints (disabled for production - uncomment if needed for troubleshooting)
    # path('api/site-onboarding/find-corrupted/', views.api_find_corrupted_data, name='api_find_corrupted_data'),
    # path('api/site-onboarding/test-unicode/', views.api_test_unicode, name='api_test_unicode'),
    
    # CRUD API endpoints
    path('api/site-onboarding/asset-list/update/', views.api_update_asset_list, name='api_update_asset_list'),
    path('api/site-onboarding/asset-list/create/', views.api_create_asset_list, name='api_create_asset_list'),
    path('api/site-onboarding/asset-list/delete/<str:asset_code>/', views.api_delete_asset_list, name='api_delete_asset_list'),
    path('api/site-onboarding/api-names/', views.api_get_unique_api_names, name='api_get_unique_api_names'),
    
    path('api/site-onboarding/device-list/update/', views.api_update_device_list, name='api_update_device_list'),
    path('api/site-onboarding/parent-codes/', views.api_get_unique_parent_codes, name='api_get_unique_parent_codes'),
    path('api/site-onboarding/device-list/create/', views.api_create_device_list, name='api_create_device_list'),
    path('api/site-onboarding/device-list/delete/<str:device_id>/', views.api_delete_device_list, name='api_delete_device_list'),
    
    # PV Module Datasheet Management APIs
    path('api/site-onboarding/pv-modules/', views.api_pv_modules_list, name='api_pv_modules_list'),
    path('api/site-onboarding/pv-modules/<int:module_id>/', views.api_pv_module_detail, name='api_pv_module_detail'),
    path('api/site-onboarding/pv-modules/create/', views.api_create_pv_module, name='api_create_pv_module'),
    path('api/site-onboarding/pv-modules/update/<int:module_id>/', views.api_update_pv_module, name='api_update_pv_module'),
    path('api/site-onboarding/pv-modules/delete/<int:module_id>/', views.api_delete_pv_module, name='api_delete_pv_module'),
    path('api/site-onboarding/pv-modules/import/', views.api_import_pv_modules, name='api_import_pv_modules'),
    path('api/site-onboarding/pv-modules/export/', views.api_export_pv_modules, name='api_export_pv_modules'),
    
    # Device PV Configuration APIs
    path('api/site-onboarding/device-pv-config/', views.api_device_pv_config_list, name='api_device_pv_config_list'),
    path('api/site-onboarding/device-pv-config/get/', views.api_device_pv_config_get, name='api_device_pv_config_get'),
    path('api/site-onboarding/weather-devices/', views.api_weather_devices_list, name='api_weather_devices_list'),
    path('api/site-onboarding/weather-metrics/', views.api_weather_metrics_list, name='api_weather_metrics_list'),
    path('api/site-onboarding/device-pv-config/update/', views.api_update_device_pv_config, name='api_update_device_pv_config'),
    path('api/site-onboarding/device-pv-config/bulk-assign/', views.api_bulk_assign_modules, name='api_bulk_assign_modules'),
    path('api/site-onboarding/device-pv-config/import/', views.api_import_device_pv_config, name='api_import_device_pv_config'),
    path('api/site-onboarding/device-pv-config/export/', views.api_export_device_pv_config, name='api_export_device_pv_config'),
    path('api/site-onboarding/device-pv-config/download-template/', views.api_download_device_pv_config_template, name='api_download_device_pv_config_template'),
    path('api/site-onboarding/pv-hierarchy/', views.api_get_pv_hierarchy, name='api_get_pv_hierarchy'),
    
    # Power Model APIs
    path('api/power-models/list/', views.api_list_power_models, name='api_list_power_models'),
    
    # Loss Calculation APIs (legacy paths; handlers in loss_analytics so main.views does not depend on main.calculations)
    path('api/loss-calculation/string/', loss_analytics_views.api_trigger_string_calculation, name='api_trigger_string_calculation'),
    path('api/calculation-test/devices/', views.api_calculation_test_devices, name='api_calculation_test_devices'),
    path('api/calculation-test/transpose/', views.api_calculation_test_transpose, name='api_calculation_test_transpose'),
    path('api/calculation-test/inverter-expected-power/', views.api_calculation_test_inverter_expected_power, name='api_calculation_test_inverter_expected_power'),
    path('api/calculation-test/upload-satellite-csv/', views.api_calculation_test_upload_satellite_csv, name='api_calculation_test_upload_satellite_csv'),
    path('api/loss-calculation/strings/batch/', loss_analytics_views.api_trigger_strings_batch, name='api_trigger_strings_batch'),
    path('api/loss-calculation/asset/', loss_analytics_views.api_trigger_asset_calculation, name='api_trigger_asset_calculation'),
    path('api/loss-calculation/asset/range/', loss_analytics_views.api_asset_range_trigger, name='api_trigger_asset_range_calculation'),
    path('api/loss-calculation/results/', loss_analytics_views.api_get_loss_results, name='api_get_loss_results'),
    path('api/loss-calculation/summary/', loss_analytics_views.api_get_loss_summary, name='api_get_loss_summary'),
    path('api/loss-calculation/metric-mappings/', loss_analytics_views.api_get_metric_mappings, name='api_get_metric_mappings'),
    
    path('api/site-onboarding/device-mapping/update/', views.api_update_device_mapping, name='api_update_device_mapping'),
    path('api/site-onboarding/device-mapping/create/', views.api_create_device_mapping, name='api_create_device_mapping'),
    path('api/site-onboarding/device-mapping/delete/<int:mapping_id>/', views.api_delete_device_mapping, name='api_delete_device_mapping'),
    path('api/site-onboarding/device-operating-state/create/', views.api_create_device_operating_state, name='api_create_device_operating_state'),
    path('api/site-onboarding/device-operating-state/update/', views.api_update_device_operating_state, name='api_update_device_operating_state'),
    path('api/site-onboarding/device-operating-state/delete/<int:state_id>/', views.api_delete_device_operating_state, name='api_delete_device_operating_state'),
    
    path('api/site-onboarding/budget-values/update/', views.api_update_budget_values, name='api_update_budget_values'),
    path('api/site-onboarding/budget-values/create/', views.api_create_budget_values, name='api_create_budget_values'),
    path('api/site-onboarding/budget-values/delete/<int:budget_id>/', views.api_delete_budget_values, name='api_delete_budget_values'),
    
    # IC Budget API endpoints
    path('api/site-onboarding/ic-budget/', views.api_ic_budget_data, name='api_ic_budget_data'),
    path('api/site-onboarding/ic-budget/update/', views.api_update_ic_budget, name='api_update_ic_budget'),
    path('api/site-onboarding/ic-budget/create/', views.api_create_ic_budget, name='api_create_ic_budget'),
    path('api/site-onboarding/ic-budget/delete/<int:ic_budget_id>/', views.api_delete_ic_budget, name='api_delete_ic_budget'),
    path('api/site-onboarding/asset-contracts/', views.api_asset_contracts_data, name='api_asset_contracts_data'),
    path('api/site-onboarding/asset-contracts/create/', views.api_create_asset_contract, name='api_create_asset_contract'),
    path('api/site-onboarding/asset-contracts/update/', views.api_update_asset_contract, name='api_update_asset_contract'),
    path('api/site-onboarding/asset-contracts/delete/<int:contract_id>/', views.api_delete_asset_contract, name='api_delete_asset_contract'),
    path('api/site-onboarding/budget-values/calculate/', views.api_calculate_budget_values, name='api_calculate_budget_values'),
    # Data Collection / AssetAdapterConfig (SolarGIS, Fusion Solar, etc.)
    path('api/site-onboarding/data-collection-adapters/', views.api_data_collection_adapter_ids, name='api_data_collection_adapter_ids'),
    path('api/site-onboarding/fusion-solar-fetch-plants/', views.api_fusion_solar_fetch_plants, name='api_fusion_solar_fetch_plants'),
    path('api/site-onboarding/fusion-solar-fetch-devices/', views.api_fusion_solar_fetch_devices, name='api_fusion_solar_fetch_devices'),
    path('api/site-onboarding/laplaceid-test-connection/', views.api_laplaceid_test_connection, name='api_laplaceid_test_connection'),
    path('api/site-onboarding/laplaceid-fetch-nodes/', views.api_laplaceid_fetch_nodes, name='api_laplaceid_fetch_nodes'),
    path('api/site-onboarding/laplaceid-discover-devices/', views.api_laplaceid_discover_devices_from_csv, name='api_laplaceid_discover_devices_from_csv'),
    path('api/site-onboarding/laplaceid-fetch-devices/', views.api_laplaceid_fetch_devices_for_assets, name='api_laplaceid_fetch_devices_for_assets'),
    path('api/site-onboarding/fusion-solar-asset-csv/', views.api_fusion_solar_asset_csv, name='api_fusion_solar_asset_csv'),
    path('api/site-onboarding/fusion-solar-device-csv/', views.api_fusion_solar_device_csv, name='api_fusion_solar_device_csv'),
    path('api/site-onboarding/adapter-fetch-raw-samples/', views.api_adapter_fetch_raw_samples, name='api_adapter_fetch_raw_samples'),
    path('api/site-onboarding/adapter-accounts/', views.api_adapter_account_list, name='api_adapter_account_list'),
    path('api/site-onboarding/adapter-accounts/create/', views.api_create_adapter_account, name='api_create_adapter_account'),
    path('api/site-onboarding/adapter-accounts/update/', views.api_update_adapter_account, name='api_update_adapter_account'),
    path('api/site-onboarding/adapter-accounts/delete/<int:account_id>/', views.api_delete_adapter_account, name='api_delete_adapter_account'),
    path('api/site-onboarding/asset-adapter-config/', views.api_asset_adapter_config_data, name='api_asset_adapter_config_data'),
    path('api/site-onboarding/asset-adapter-config/create/', views.api_create_asset_adapter_config, name='api_create_asset_adapter_config'),
    path('api/site-onboarding/asset-adapter-config/update/', views.api_update_asset_adapter_config, name='api_update_asset_adapter_config'),
    path('api/site-onboarding/asset-adapter-config/delete/<int:config_id>/', views.api_delete_asset_adapter_config, name='api_delete_asset_adapter_config'),
    
    # Spare Management API endpoints
    # Spare Master
    path('api/site-onboarding/spares/', views.api_spare_master_list, name='api_spare_master_list'),
    path('api/site-onboarding/spares/create/', views.api_create_spare_master, name='api_create_spare_master'),
    path('api/site-onboarding/spares/update/<int:spare_id>/', views.api_update_spare_master, name='api_update_spare_master'),
    path('api/site-onboarding/spares/delete/<int:spare_id>/', views.api_delete_spare_master, name='api_delete_spare_master'),
    # Location Master
    path('api/site-onboarding/locations/', views.api_location_master_list, name='api_location_master_list'),
    path('api/site-onboarding/locations/create/', views.api_create_location_master, name='api_create_location_master'),
    path('api/site-onboarding/locations/update/<int:location_id>/', views.api_update_location_master, name='api_update_location_master'),
    path('api/site-onboarding/locations/delete/<int:location_id>/', views.api_delete_location_master, name='api_delete_location_master'),
    # Spare-Site-Location Map
    path('api/site-onboarding/spare-site-map/', views.api_spare_site_map_list, name='api_spare_site_map_list'),
    path('api/site-onboarding/spare-site-map/create/', views.api_create_spare_site_map, name='api_create_spare_site_map'),
    path('api/site-onboarding/spare-site-map/update/<int:map_id>/', views.api_update_spare_site_map, name='api_update_spare_site_map'),
    path('api/site-onboarding/spare-site-map/delete/<int:map_id>/', views.api_delete_spare_site_map, name='api_delete_spare_site_map'),
    # Stock Balance (read-only)
    path('api/site-onboarding/stock-balance/', views.api_stock_balance_list, name='api_stock_balance_list'),
    # Stock Entry (IN transactions)
    path('api/site-onboarding/stock-entry/', views.api_stock_entry_list, name='api_stock_entry_list'),
    path('api/site-onboarding/stock-entry/create/', views.api_create_stock_entry, name='api_create_stock_entry'),
    # Stock Issue (OUT transactions)
    path('api/site-onboarding/stock-issue/', views.api_stock_issue_list, name='api_stock_issue_list'),
    path('api/site-onboarding/stock-issue/create/', views.api_create_stock_issue, name='api_create_stock_issue'),
    
    # Data management API endpoints
    path('api/data-counts/', views.api_data_counts, name='api_data_counts'),
    path('api/recent-uploads/', views.api_recent_uploads, name='api_recent_uploads'),
    path('api/upload-history/', views.api_upload_history, name='api_upload_history'),
    path('api/data-preview/<str:data_type>/', views.api_data_preview, name='api_data_preview'),
    path('api/delete-data/', views.api_delete_data, name='api_delete_data'),
    path('api/download-data/', views.api_download_data, name='api_download_data'),
    path('api/loss-calculation-data/', views.api_loss_calculation_data, name='api_loss_calculation_data'),
    path('api/analyze-file-encoding/', views.api_analyze_file_encoding, name='api_analyze_file_encoding'),
    
    # Feedback URLs
    path('feedback/', views.feedback_submit_view, name='feedback_submit'),
    path('feedback/list/', views.feedback_list_view, name='feedback_list'),
    path('api/feedback/list/', views.api_feedback_list, name='api_feedback_list'),
    path('api/feedback/submit/', views.feedback_submit_view, name='api_feedback_submit'),
    path('api/feedback/<int:feedback_id>/mark-attended/', views.mark_feedback_attended, name='api_mark_feedback_attended'),
    path('api/feedback/<int:feedback_id>/delete/', views.delete_feedback, name='api_delete_feedback'),
    path('api/feedback/<int:feedback_id>/images/', views.feedback_images_ajax, name='api_feedback_images'),
    path('feedback/mark-attended/<int:feedback_id>/', views.mark_feedback_attended, name='mark_feedback_attended'),
    path('feedback/delete/<int:feedback_id>/', views.delete_feedback, name='delete_feedback'),
    path('feedback/download-image/<int:feedback_id>/', views.feedback_image_download, name='feedback_image_download'),
    path('feedback/direct-image/<int:feedback_id>/', views.feedback_image_direct, name='feedback_image_direct'),
    path('feedback/images/<int:feedback_id>/', views.feedback_images_ajax, name='feedback_images_ajax'),
    
    # Download URLs
    path('download/<str:data_type>/', views.download_data_view, name='download_data'),
    
    # External Service Proxy URLs for Iframe Integration (Temporarily disabled)
    # path('proxy/external/<path:service_path>', views.proxy_external_service, name='proxy_external_service'),
    # path('proxy/iframe/', views.iframe_proxy_view, name='iframe_proxy'),
    # path('proxy/example/', views.iframe_proxy_example_view, name='iframe_proxy_example'), 
   
    # Enhanced Blocking Management API Endpoints
    path('api/blocking/stats/', views.blocking_stats_api, name='api_blocking_stats'),
    path('api/blocking/ips/', views.blocked_ips_api, name='api_blocked_ips'),
    path('api/blocking/users/', views.blocked_users_api, name='api_blocked_users'),
    path('api/blocking/block-ip/', views.block_ip_api, name='api_block_ip'),
    path('api/blocking/unblock-ip/', views.unblock_ip_api, name='api_unblock_ip'),
    path('api/blocking/block-user/', views.block_user_api, name='api_block_user'),
    path('api/blocking/unblock-user/', views.unblock_user_api, name='api_unblock_user'),
    path('api/blocking/check-ip/<str:ip_address>/', views.check_ip_status_api, name='api_check_ip_status'),
    path('api/csrf-token/', views.get_csrf_token_api, name='api_csrf_token'),
    path('api/csrf/', views.get_csrf_token_api, name='api_csrf'),  # Alternative shorter path
]


