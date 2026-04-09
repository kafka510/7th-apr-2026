"""
Download and file management views
"""
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse

from accounts.decorators import role_required, feature_required
from main.permissions import user_has_capability
import logging
from functools import wraps

from ..models import (
    YieldData, BESSData, BESSV1Data, AOCData, ICEData, ICVSEXVSCURData, MapData,
    MinamataStringLossData, DataImportLog, AssetList, device_list, device_mapping, budget_values, UserProfile,
    ActualGenerationDailyData, ExpectedBudgetDailyData, BudgetGIIDailyData, ActualGIIDailyData,
    ICApprovedBudgetDailyData, LossCalculationData, RealTimeKPI, Feedback, ic_budget, assets_contracts
)


import csv, json, math
from datetime import datetime
from django.http import HttpResponse
from django.utils import timezone



@feature_required('user_management')
@login_required
def download_page(request):
    """Simple download page that opens in new window to bypass iframe restrictions"""
    return render(request, 'main/download_page.html')



@feature_required('data_upload')
@login_required
def download_data_view(request, data_type):
    """Generic download view for all data types - Admin only"""
    try:
        if not user_has_capability(request.user, 'data_upload.manage'):
            html_content = '''
            <!DOCTYPE html>
            <html>
            <head>
                <title>Access Denied</title>
                <style>
                    body { font-family: Arial, sans-serif; text-align: center; padding: 50px; }
                    h3 { color: #d32f2f; }
                </style>
            </head>
            <body>
                <h3>Access Denied</h3>
                <p>Administrator privileges required to download data.</p>
                <script>setTimeout(() => window.close(), 3000);</script>
            </body>
            </html>
            '''
            return HttpResponse(html_content, content_type='text/html', status=403)
        
        # Define the model mapping for download
        model_mapping = {
            'yield': YieldData,
            'bess': BESSData,
            'bess_v1': BESSV1Data,
            'aoc': AOCData,
            'ice': ICEData,
            'icvsexvscur': ICVSEXVSCURData,
            'map': MapData,
            'minamata': MinamataStringLossData,
            'loss_calculation': LossCalculationData,
            'actual_generation_daily': ActualGenerationDailyData,
            'expected_budget_daily': ExpectedBudgetDailyData,
            'budget_gii_daily': BudgetGIIDailyData,
            'actual_gii_daily': ActualGIIDailyData,
            'ic_approved_budget_daily': ICApprovedBudgetDailyData,
            'data_import_log': DataImportLog,
            'realtime_kpi': RealTimeKPI,
            'feedback': Feedback,
        }

        # Define friendly names for download files
        friendly_names = {
            'yield': 'Yield_Data',
            'bess': 'BESS_Performance_Data',
            'bess_v1': 'BESS_V1_Performance_Data',
            'aoc': 'Areas_of_Concern_Data',
            'ice': 'ICE_Data',
            'icvsexvscur': 'IC_Budget_vs_Expected_Data',
            'map': 'Map_Data',
            'minamata': 'Minamata_String_Loss_Data',
            'loss_calculation': 'Loss_Calculation_Data',
            'actual_generation_daily': 'Actual_Generation_Daily_Data',
            'expected_budget_daily': 'Expected_Budget_Daily_Data',
            'budget_gii_daily': 'Budget_GII_Daily_Data',
            'actual_gii_daily': 'Actual_GII_Daily_Data',
            'ic_approved_budget_daily': 'IC_Approved_Budget_Daily_Data',
            'data_import_log': 'Data_Import_Log',
            'realtime_kpi': 'Real_Time_KPI_Data',
            'feedback': 'Feedback_Data',
        }

        if data_type not in model_mapping:
            html_content = f'''
            <!DOCTYPE html>
            <html>
            <head>
                <title>Invalid Data Type</title>
                <style>
                    body {{ font-family: Arial, sans-serif; text-align: center; padding: 50px; }}
                    h3 {{ color: #d32f2f; }}
                </style>
            </head>
            <body>
                <h3>Invalid Data Type</h3>
                <p>Data type "{data_type}" is not valid.</p>
                <script>setTimeout(() => window.close(), 3000);</script>
            </body>
            </html>
            '''
            return HttpResponse(html_content, content_type='text/html', status=400)

        model = model_mapping[data_type]
        friendly_name = friendly_names.get(data_type, data_type)

        # Admin users get access to all data (no filtering needed)
        # Since we already verified user is admin above, just return all data
        queryset = model.objects.all()

        # Get format parameter
        format_type = request.GET.get('format', 'csv').lower()

        if format_type == 'excel':
            return export_to_excel(queryset, friendly_name, data_type)
        else:
            return export_to_csv(queryset, friendly_name, data_type)

    except Exception as e:
        logger = logging.getLogger(__name__)
        logger.error(f"Error downloading data ({data_type}): {str(e)}", exc_info=True)
        html_content = f'''
        <!DOCTYPE html>
        <html>
        <head>
            <title>Download Error</title>
            <style>
                body {{ font-family: Arial, sans-serif; text-align: center; padding: 50px; }}
                h3 {{ color: #d32f2f; }}
                .error-details {{ background: #f5f5f5; padding: 20px; margin: 20px auto; max-width: 600px; border-radius: 5px; }}
            </style>
        </head>
        <body>
            <h3>Download Error</h3>
            <div class="error-details">
                <p><strong>Error:</strong> {str(e)}</p>
                <p>Please try again or contact support if the problem persists.</p>
            </div>
            <script>setTimeout(() => window.close(), 5000);</script>
        </body>
        </html>
        '''
        return HttpResponse(html_content, content_type='text/html', status=500)

def export_to_csv(queryset, friendly_name, data_type):
    """Export queryset to CSV format"""
    import csv
    from datetime import datetime

    try:
        # Create the HTTP response with CSV content type
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"{friendly_name}_{timestamp}.csv"
        
        response = HttpResponse(content_type='text/csv; charset=utf-8')
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        # Add UTF-8 BOM for better Excel compatibility
        response.write('\ufeff')

        writer = csv.writer(response)

        if queryset.exists():
            # Get all field names from the model
            field_names = []
            model_fields = queryset.model._meta.get_fields()
            
            for field in model_fields:
                if hasattr(field, 'column'):  # Skip reverse foreign keys and many-to-many
                    field_names.append(field.name)

            # Write header
            writer.writerow(field_names)

            # Write data rows
            for obj in queryset:
                row = []
                for field_name in field_names:
                    value = getattr(obj, field_name, '')
                    if value is None:
                        value = ''
                    elif hasattr(value, 'strftime'):  # Handle datetime fields
                        value = value.strftime('%Y-%m-%d %H:%M:%S')
                    row.append(str(value))
                writer.writerow(row)
        else:
            # Write header even if no data
            writer.writerow(['No data available'])

        return response
    except Exception as e:
        logger = logging.getLogger(__name__)
        logger.error(f"Error exporting CSV ({data_type}): {str(e)}", exc_info=True)
        html_content = f'''
        <!DOCTYPE html>
        <html>
        <head>
            <title>CSV Export Error</title>
            <style>
                body {{ font-family: Arial, sans-serif; text-align: center; padding: 50px; }}
                h3 {{ color: #d32f2f; }}
            </style>
        </head>
        <body>
            <h3>CSV Export Error</h3>
            <p>Error: {str(e)}</p>
            <script>setTimeout(() => window.close(), 3000);</script>
        </body>
        </html>
        '''
        return HttpResponse(html_content, content_type='text/html', status=500)

def export_to_excel(queryset, friendly_name, data_type):
    """Export queryset to Excel format"""
    try:
        import pandas as pd
        from io import BytesIO
        from datetime import datetime

        # Create timestamp for filename
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"{friendly_name}_{timestamp}.xlsx"

        if queryset.exists():
            # Convert queryset to DataFrame
            data = []
            field_names = []
            model_fields = queryset.model._meta.get_fields()
            
            for field in model_fields:
                if hasattr(field, 'column'):  # Skip reverse foreign keys and many-to-many
                    field_names.append(field.name)

            for obj in queryset:
                row = {}
                for field_name in field_names:
                    value = getattr(obj, field_name, None)
                    if value is None:
                        value = ''
                    row[field_name] = value
                data.append(row)

            df = pd.DataFrame(data)
        else:
            # Create empty DataFrame with message
            df = pd.DataFrame({'Message': ['No data available']})

        # Create Excel file in memory
        output = BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, sheet_name=friendly_name[:30], index=False)  # Sheet name max 31 chars
        
        output.seek(0)

        # Create response
        response = HttpResponse(
            output.getvalue(),
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        
        return response

    except ImportError:
        # Fallback to CSV if pandas/openpyxl not available
        logger = logging.getLogger(__name__)
        logger.warning(f"Pandas/OpenPyXL not available, falling back to CSV for {data_type}")
        return export_to_csv(queryset, friendly_name, data_type)
    except Exception as e:
        logger = logging.getLogger(__name__)
        logger.error(f"Error exporting Excel ({data_type}): {str(e)}", exc_info=True)
        html_content = f'''
        <!DOCTYPE html>
        <html>
        <head>
            <title>Excel Export Error</title>
            <style>
                body {{ font-family: Arial, sans-serif; text-align: center; padding: 50px; }}
                h3 {{ color: #d32f2f; }}
            </style>
        </head>
        <body>
            <h3>Excel Export Error</h3>
            <p>Error: {str(e)}</p>
            <p>Falling back to CSV format...</p>
            <script>
                setTimeout(() => {{
                    // Redirect to CSV format
                    const url = new URL(window.location.href);
                    url.searchParams.set('format', 'csv');
                    window.location.href = url.toString();
                }}, 2000);
            </script>
        </body>
        </html>
        '''
        return HttpResponse(html_content, content_type='text/html', status=500)


@login_required
def download_site_onboarding_data(request, table_name):
    """Download CSV data for asset_list, device_list, or device_mapping with optional filters"""
    try:
        from decimal import Decimal, InvalidOperation

        def _excel_text_id(val):
            """
            Force Excel to keep IDs as text.
            - If val is an integer string -> prefix apostrophe.
            - If val is scientific notation (e.g. 1.00E+15) -> normalize to integer and prefix apostrophe.
            """
            s = "" if val is None else str(val).strip()
            if not s:
                return ""
            if s.startswith("'"):
                return s
            if s.isdigit():
                return "'" + s
            try:
                d = Decimal(s)
                if d == d.to_integral_value():
                    return "'" + format(d.to_integral_value(), "f")
            except (InvalidOperation, ValueError):
                pass
            return s

        if table_name == 'asset_list':
            queryset = AssetList.objects.all()
            filename = 'asset_list_export.csv'
            headers = [
                'asset_code', 'asset_name', 'provider_asset_id', 'capacity', 'address', 'country',
                'latitude', 'longitude', 'contact_person', 'contact_method',
                'grid_connection_date', 'asset_number', 'customer_name', 'timezone', 'asset_name_oem',
                'cod', 'operational_cod', 'portfolio', 'y1_degradation', 'anual_degradation',
                'api_name', 'api_key',
                'tilt_configs_json', 'altitude_m', 'albedo', 'pv_syst_pr',
                'satellite_irradiance_source_asset_code'
            ]
        elif table_name == 'device_list':
            # Get filter parameters
            parent_code_filter = request.GET.get('parent_code', '').strip()
            parent_code_filters = [pc.strip() for pc in parent_code_filter.split(',') if pc.strip()]
            asset_code_filter = request.GET.get('asset_code', '').strip()
            search_filter = request.GET.get('search', '').strip()
            
            # Require either parent_code or asset_code filter for device_list download
            if not parent_code_filters and not asset_code_filter:
                return JsonResponse({
                    'error': 'Site filter is required. Please select a parent code or asset code filter before downloading.'
                }, status=400)
            
            queryset = device_list.objects.all()
            
            # Apply filters - prioritize asset_code if both are provided
            if asset_code_filter:
                # Filter by asset_code (assuming parent_code matches asset_code)
                queryset = queryset.filter(parent_code=asset_code_filter)
            elif parent_code_filters:
                queryset = queryset.filter(parent_code__in=parent_code_filters)
            
            if search_filter:
                from django.db.models import Q
                queryset = queryset.filter(
                    Q(device_id__icontains=search_filter) |
                    Q(device_name__icontains=search_filter) |
                    Q(device_code__icontains=search_filter) |
                    Q(parent_code__icontains=search_filter) |
                    Q(device_type__icontains=search_filter)
                )
            
            # Generate filename with filter info
            filter_suffix = ''
            if asset_code_filter:
                filter_suffix = f'_{asset_code_filter}'
            elif parent_code_filters:
                filter_suffix = f'_{len(parent_code_filters)}_sites'
            filename = f'device_list_export{filter_suffix}.csv'
            
            headers = [
                'device_id', 'device_name', 'device_code', 'device_type_id',
                'device_serial', 'device_model', 'device_make', 'latitude',
                'longitude', 'optimizer_no', 'parent_code', 'device_type',
                'software_version', 'country', 'string_no', 'connected_strings',
                'device_sub_group', 'dc_cap', 'device_source', 'ac_capacity',
                'equipment_warranty_start_date', 'equipment_warranty_expire_date',
                'epc_warranty_start_date', 'epc_warranty_expire_date',
                'calibration_frequency', 'pm_frequency', 'visual_inspection_frequency',
                'bess_capacity', 'yom', 'nomenclature', 'location',
                # PV Module Configuration Fields
                'module_datasheet_id', 'modules_in_series', 'installation_date',
                'tilt_angle', 'azimuth_angle', 'mounting_type',
                'expected_soiling_loss', 'shading_factor', 'measured_degradation_rate',
                'last_performance_test_date', 'operational_notes', 'power_model_id',
                'power_model_config', 'model_fallback_enabled',
                'weather_device_config', 'tilt_configs_json'
            ]
        elif table_name == 'device_mapping':
            # Get filter parameters
            asset_code_filter = request.GET.get('asset_code', '').strip()
            search_filter = request.GET.get('search', '').strip()
            
            queryset = device_mapping.objects.all()
            
            # Apply filters
            if asset_code_filter:
                queryset = queryset.filter(asset_code=asset_code_filter)
            
            if search_filter:
                from django.db.models import Q
                queryset = queryset.filter(
                    Q(asset_code__icontains=search_filter) |
                    Q(device_type__icontains=search_filter) |
                    Q(oem_tag__icontains=search_filter) |
                    Q(discription__icontains=search_filter) |
                    Q(metric__icontains=search_filter)
                )
            
            # Generate filename with filter info
            filter_suffix = ''
            if asset_code_filter:
                filter_suffix = f'_{asset_code_filter}'
            filename = f'device_mapping_export{filter_suffix}.csv'
            
            headers = [
                'id', 'asset_code', 'device_type', 'oem_tag', 'discription',
                'data_type', 'units', 'metric', 'fault_code', 'module_no',
                'default_value'
            ]
        elif table_name == 'budget_values':
            # Get filter parameters
            asset_code_filter = request.GET.get('asset_code', '').strip()
            search_filter = request.GET.get('search', '').strip()
            
            queryset = budget_values.objects.all().order_by('asset_code', 'month_str')
            
            # Apply filters
            if asset_code_filter:
                queryset = queryset.filter(asset_code=asset_code_filter)
            
            if search_filter:
                from django.db.models import Q
                queryset = queryset.filter(
                    Q(asset_code__icontains=search_filter) |
                    Q(asset_number__icontains=search_filter) |
                    Q(month_str__icontains=search_filter)
                )
            
            # Generate filename with filter info
            filter_suffix = ''
            if asset_code_filter:
                filter_suffix = f'_{asset_code_filter}'
            filename = f'budget_values_export{filter_suffix}.csv'
            
            headers = [
                'id', 'asset_number', 'asset_code', 'month_str', 'month_date',
                'bd_production', 'bd_ghi', 'bd_gti'
            ]
        elif table_name == 'ic_budget':
            # Get filter parameters
            asset_code_filter = request.GET.get('asset_code', '').strip()
            search_filter = request.GET.get('search', '').strip()
            
            queryset = ic_budget.objects.all().order_by('asset_code', 'month_str')
            
            # Apply filters
            if asset_code_filter:
                queryset = queryset.filter(asset_code=asset_code_filter)
            
            if search_filter:
                from django.db.models import Q
                queryset = queryset.filter(
                    Q(asset_code__icontains=search_filter) |
                    Q(asset_number__icontains=search_filter) |
                    Q(month_str__icontains=search_filter)
                )
            
            # Generate filename with filter info
            filter_suffix = ''
            if asset_code_filter:
                filter_suffix = f'_{asset_code_filter}'
            filename = f'ic_budget_export{filter_suffix}.csv'
            
            headers = [
                'id', 'asset_code', 'asset_number', 'month_str', 'month_date', 'ic_bd_production'
            ]
        elif table_name == 'assets_contracts':
            search_filter = request.GET.get('search', '').strip()
            queryset = assets_contracts.objects.all().order_by('asset_number')
            if search_filter:
                from django.db.models import Q
                queryset = queryset.filter(
                    Q(asset_number__icontains=search_filter)
                    | Q(asset_code__icontains=search_filter)
                    | Q(customer_asset_name__icontains=search_filter)
                )
            filename = 'assets_contracts_export.csv'
            headers = [f.name for f in assets_contracts._meta.fields]
        elif table_name == 'asset_adapter_config':
            from data_collection.models import AssetAdapterConfig
            search_filter = request.GET.get('search', '').strip()
            adapter_id_filter = request.GET.get('adapter_id', '').strip()
            asset_code_filter = request.GET.get('asset_code', '').strip()

            queryset = AssetAdapterConfig.objects.all().order_by('asset_code')
            if adapter_id_filter:
                queryset = queryset.filter(adapter_id=adapter_id_filter)
            if asset_code_filter:
                queryset = queryset.filter(asset_code__icontains=asset_code_filter)
            if search_filter:
                from django.db.models import Q
                queryset = queryset.filter(
                    Q(asset_code__icontains=search_filter) |
                    Q(adapter_id__icontains=search_filter)
                )

            filename = 'asset_adapter_config_export.csv'
            headers = [
                'id', 'asset_code', 'adapter_id', 'adapter_account_id', 'enabled', 'acquisition_interval_minutes',
                'asset_name', 'latitude', 'longitude', 'capacity', 'timezone', 'altitude_m',
                'satellite_irradiance_source_asset_code',
                'api_url', 'api_key', 'summarization', 'processing_keys', 'terrain_shading',
                'time_stamp_type', 'tilt', 'azimuth', 'linked_asset_codes',
                'solargis_region', 'daily_run_local_time', 'daily_run_timezone',
                'asset_id',
            ]
        elif table_name == 'device_operating_state':
            from data_collection.models import DeviceOperatingState
            adapter_id_filter = request.GET.get('adapter_id', '').strip()
            device_type_filter = request.GET.get('device_type', '').strip()
            search_filter = request.GET.get('search', '').strip()

            queryset = DeviceOperatingState.objects.all().order_by('adapter_id', 'device_type', 'state_value')
            if adapter_id_filter:
                queryset = queryset.filter(adapter_id=adapter_id_filter)
            if device_type_filter:
                queryset = queryset.filter(device_type=device_type_filter)
            if search_filter:
                from django.db.models import Q
                queryset = queryset.filter(
                    Q(adapter_id__icontains=search_filter)
                    | Q(device_type__icontains=search_filter)
                    | Q(state_value__icontains=search_filter)
                    | Q(oem_state_label__icontains=search_filter)
                    | Q(internal_state__icontains=search_filter)
                )

            filename = 'device_operating_state_export.csv'
            headers = [
                'id',
                'adapter_id',
                'device_type',
                'state_value',
                'oem_state_label',
                'internal_state',
                'is_normal',
                'fault_code',
                'created_at',
                'updated_at',
            ]
        elif table_name == 'spare_master':
            # Get filter parameters
            search_filter = request.GET.get('search', '').strip()
            
            from ..models import SpareMaster
            queryset = SpareMaster.objects.all()
            
            if search_filter:
                from django.db.models import Q
                queryset = queryset.filter(
                    Q(spare_code__icontains=search_filter) |
                    Q(spare_name__icontains=search_filter) |
                    Q(category__icontains=search_filter)
                )
            
            filename = 'spare_master_export.csv'
            headers = [
                'spare_id', 'spare_code', 'spare_name', 'description', 'category',
                'unit', 'min_stock', 'max_stock', 'is_critical'
            ]
        elif table_name == 'location_master':
            # Get filter parameters
            search_filter = request.GET.get('search', '').strip()
            
            from ..models import LocationMaster
            queryset = LocationMaster.objects.all()
            
            if search_filter:
                from django.db.models import Q
                queryset = queryset.filter(
                    Q(location_code__icontains=search_filter) |
                    Q(location_name__icontains=search_filter) |
                    Q(location_type__icontains=search_filter)
                )
            
            filename = 'location_master_export.csv'
            headers = [
                'location_id', 'location_code', 'location_name', 'location_type'
            ]
        elif table_name == 'spare_site_map':
            # Get filter parameters
            asset_code_filter = request.GET.get('asset_code', '').strip()
            spare_code_filter = request.GET.get('spare_code', '').strip()
            location_code_filter = request.GET.get('location_code', '').strip()
            search_filter = request.GET.get('search', '').strip()
            
            from ..models import SpareSiteMap
            queryset = SpareSiteMap.objects.select_related('spare', 'asset', 'location').all()
            
            # Apply filters
            if asset_code_filter:
                queryset = queryset.filter(asset__asset_code=asset_code_filter)
            if spare_code_filter:
                queryset = queryset.filter(spare__spare_code=spare_code_filter)
            if location_code_filter:
                queryset = queryset.filter(location__location_code=location_code_filter)
            
            if search_filter:
                from django.db.models import Q
                queryset = queryset.filter(
                    Q(asset__asset_code__icontains=search_filter) |
                    Q(spare__spare_code__icontains=search_filter) |
                    Q(location__location_code__icontains=search_filter)
                )
            
            # Generate filename with filter info
            filter_suffix = ''
            if asset_code_filter:
                filter_suffix = f'_{asset_code_filter}'
            filename = f'spare_site_map_export{filter_suffix}.csv'
            
            headers = [
                'map_id', 'spare_id', 'spare_code', 'asset_code', 'location_id', 'location_code', 'is_active', 'created_at'
            ]
        elif table_name == 'stock_balance':
            # Get filter parameters
            asset_code_filter = request.GET.get('asset_code', '').strip()
            spare_code_filter = request.GET.get('spare_code', '').strip()
            location_code_filter = request.GET.get('location_code', '').strip()
            search_filter = request.GET.get('search', '').strip()
            
            from ..models import StockBalance
            queryset = StockBalance.objects.select_related('spare', 'location').all()
            
            # Apply filters
            if asset_code_filter:
                queryset = queryset.filter(
                    spare__site_mappings__asset__asset_code=asset_code_filter,
                    spare__site_mappings__is_active=True
                ).distinct()
            if spare_code_filter:
                queryset = queryset.filter(spare__spare_code=spare_code_filter)
            if location_code_filter:
                queryset = queryset.filter(location__location_code=location_code_filter)
            
            if search_filter:
                from django.db.models import Q
                queryset = queryset.filter(
                    Q(spare__spare_code__icontains=search_filter) |
                    Q(location__location_code__icontains=search_filter)
                )
            
            # Generate filename with filter info
            filter_suffix = ''
            if asset_code_filter:
                filter_suffix = f'_{asset_code_filter}'
            filename = f'stock_balance_export{filter_suffix}.csv'
            
            headers = [
                'stock_balance_id', 'spare_id', 'spare_code', 'location_id', 'location_code',
                'quantity', 'unit', 'last_updated'
            ]
        elif table_name == 'stock_entry':
            # Get filter parameters
            asset_code_filter = request.GET.get('asset_code', '').strip()
            spare_code_filter = request.GET.get('spare_code', '').strip()
            location_code_filter = request.GET.get('location_code', '').strip()
            search_filter = request.GET.get('search', '').strip()
            
            from ..models import StockEntry
            queryset = StockEntry.objects.select_related('spare', 'location').all()
            
            # Apply filters
            if asset_code_filter:
                queryset = queryset.filter(
                    spare__site_mappings__asset__asset_code=asset_code_filter,
                    spare__site_mappings__is_active=True
                ).distinct()
            if spare_code_filter:
                queryset = queryset.filter(spare__spare_code=spare_code_filter)
            if location_code_filter:
                queryset = queryset.filter(location__location_code=location_code_filter)
            
            if search_filter:
                from django.db.models import Q
                queryset = queryset.filter(
                    Q(spare__spare_code__icontains=search_filter) |
                    Q(reference_number__icontains=search_filter)
                )
            
            # Generate filename with filter info
            filter_suffix = ''
            if asset_code_filter:
                filter_suffix = f'_{asset_code_filter}'
            filename = f'stock_entry_export{filter_suffix}.csv'
            
            headers = [
                'entry_id', 'spare_id', 'spare_code', 'location_id', 'location_code',
                'quantity', 'entry_type', 'reference_number', 'remarks', 'entry_date'
            ]
        elif table_name == 'stock_issue':
            # Get filter parameters
            asset_code_filter = request.GET.get('asset_code', '').strip()
            spare_code_filter = request.GET.get('spare_code', '').strip()
            location_code_filter = request.GET.get('location_code', '').strip()
            ticket_id_filter = request.GET.get('ticket_id', '').strip()
            search_filter = request.GET.get('search', '').strip()
            
            from ..models import StockIssue
            queryset = StockIssue.objects.select_related('spare', 'location', 'ticket').all()
            
            # Apply filters
            if asset_code_filter:
                queryset = queryset.filter(
                    spare__site_mappings__asset__asset_code=asset_code_filter,
                    spare__site_mappings__is_active=True
                ).distinct()
            if spare_code_filter:
                queryset = queryset.filter(spare__spare_code=spare_code_filter)
            if location_code_filter:
                queryset = queryset.filter(location__location_code=location_code_filter)
            if ticket_id_filter:
                queryset = queryset.filter(ticket_id=ticket_id_filter)
            
            if search_filter:
                from django.db.models import Q
                queryset = queryset.filter(
                    Q(spare__spare_code__icontains=search_filter) |
                    Q(issued_to__icontains=search_filter)
                )
            
            # Generate filename with filter info
            filter_suffix = ''
            if asset_code_filter:
                filter_suffix = f'_{asset_code_filter}'
            filename = f'stock_issue_export{filter_suffix}.csv'
            
            headers = [
                'issue_id', 'spare_id', 'spare_code', 'location_id', 'location_code',
                'quantity', 'issue_type', 'ticket_id', 'issued_to', 'remarks', 'issue_date'
            ]
        else:
            return JsonResponse({'error': 'Invalid table name'}, status=400)
        
        response = HttpResponse(content_type='text/csv; charset=utf-8')
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        
        # Add UTF-8 BOM for better Excel compatibility
        response.write('\ufeff')
        
        writer = csv.writer(response)
        writer.writerow(headers)
        
        if table_name == 'asset_adapter_config':
            import json as json_module
            asset_codes = list(queryset.values_list('asset_code', flat=True).distinct())
            assets = {a.asset_code: a for a in AssetList.objects.filter(asset_code__in=asset_codes)}
            for obj in queryset:
                asset = assets.get(obj.asset_code)
                cfg = obj.config or {}
                linked = cfg.get('linked_asset_codes')
                linked_str = json_module.dumps(linked) if isinstance(linked, (list, dict)) else (str(linked) if linked else '')
                row_dict = {
                    'id': obj.id,
                    'asset_code': obj.asset_code,
                    'adapter_id': obj.adapter_id,
                    'adapter_account_id': obj.adapter_account_id or '',
                    'enabled': obj.enabled,
                    'acquisition_interval_minutes': obj.acquisition_interval_minutes,
                    'asset_name': asset.asset_name if asset else '',
                    'latitude': asset.latitude if asset and asset.latitude is not None else '',
                    'longitude': asset.longitude if asset and asset.longitude is not None else '',
                    'capacity': asset.capacity if asset and asset.capacity is not None else '',
                    'timezone': asset.timezone if asset else '',
                    'altitude_m': getattr(asset, 'altitude_m', None) if asset else '',
                    'satellite_irradiance_source_asset_code': getattr(asset, 'satellite_irradiance_source_asset_code', '') or '' if asset else '',
                    'api_url': cfg.get('api_url', ''),
                    'api_key': '****' if cfg.get('api_key') else '',
                    'summarization': cfg.get('summarization', ''),
                    'processing_keys': cfg.get('processing_keys', ''),
                    'terrain_shading': cfg.get('terrain_shading', False),
                    'time_stamp_type': cfg.get('time_stamp_type', ''),
                    'tilt': cfg.get('tilt', ''),
                    'azimuth': cfg.get('azimuth', ''),
                    'linked_asset_codes': linked_str,
                    'solargis_region': cfg.get('solargis_region', ''),
                    'daily_run_local_time': cfg.get('daily_run_local_time', ''),
                    'daily_run_timezone': cfg.get('daily_run_timezone', ''),
                }
                row = []
                for header in headers:
                    value = row_dict.get(header, '')
                    if isinstance(value, bool):
                        value = 'Yes' if value else 'No'
                    elif value is None:
                        value = ''
                    row.append(str(value))
                writer.writerow(row)
        else:
            for obj in queryset:
                row = []
                for header in headers:
                    # Handle special cases for related fields
                    if header in ['spare_code', 'spare_name'] and hasattr(obj, 'spare'):
                        if header == 'spare_code':
                            value = obj.spare.spare_code
                        elif header == 'spare_name':
                            value = obj.spare.spare_name
                    elif header in ['location_code', 'location_name'] and hasattr(obj, 'location'):
                        if header == 'location_code':
                            value = obj.location.location_code
                        elif header == 'location_name':
                            value = obj.location.location_name
                    elif header == 'asset_code' and hasattr(obj, 'asset'):
                        value = obj.asset.asset_code
                    elif header == 'ticket_id' and hasattr(obj, 'ticket'):
                        value = str(obj.ticket.id) if obj.ticket else ''
                    elif header == 'ticket_number' and hasattr(obj, 'ticket'):
                        value = obj.ticket.ticket_number if obj.ticket else ''
                    elif header == 'performed_by' and hasattr(obj, 'performed_by'):
                        value = obj.performed_by.username
                    elif header == 'tilt_configs_json' and hasattr(obj, 'tilt_configs'):
                        value = getattr(obj, 'tilt_configs', None)
                        if value is not None and isinstance(value, (list, dict)):
                            import json as json_module
                            value = json_module.dumps(value)
                    elif header in ['power_model_config', 'weather_device_config'] and hasattr(obj, header):
                        value = getattr(obj, header, None)
                        if value is not None and isinstance(value, (list, dict, dict)):
                            import json as json_module
                            value = json_module.dumps(value)
                    elif hasattr(obj, header):
                        value = getattr(obj, header, '')
                    else:
                        value = ''

                    # Prevent Excel scientific notation for large numeric IDs in device_list exports
                    if table_name == 'device_list' and header in ('device_id', 'device_code'):
                        value = _excel_text_id(value)
                    
                    # Format datetime fields (datetime is the class from: from datetime import datetime)
                    if isinstance(value, datetime):
                        value = value.isoformat()
                    elif isinstance(value, bool):
                        value = 'Yes' if value else 'No'
                    elif value is None:
                        value = ''
                    
                    row.append(str(value))
                writer.writerow(row)
        
        return response
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@role_required(allowed_roles=['admin'])
@login_required
def download_site_onboarding_template(request, table_name):
    """Download CSV template for asset_list, device_list, or device_mapping"""
    import logging
    logger = logging.getLogger(__name__)
    try:
        if table_name == 'asset_list':
            filename = 'asset_list_template.csv'
            headers = [
                'asset_code', 'asset_name', 'capacity', 'address', 'country',
                'latitude', 'longitude', 'contact_person', 'contact_method',
                'grid_connection_date', 'asset_number', 'customer_name', 'timezone', 'asset_name_oem',
                'cod', 'operational_cod', 'portfolio', 'y1_degradation', 'anual_degradation',
                'api_name', 'api_key',
                'tilt_configs_json', 'altitude_m', 'albedo', 'pv_syst_pr',
                'satellite_irradiance_source_asset_code'
            ]
            # Sample data to help users understand the format (includes Unicode example)
            sample_data = [{
                'asset_code': 'SAMPLE_001',
                'asset_name': 'サンプルソーラーファーム',  # Sample Solar Farm in Japanese
                'capacity': '1000.50',
                'address': '東京都港区芝公園1丁目2-3',  # Tokyo address in Japanese
                'country': '日本',  # Japan in Japanese
                'latitude': '35.6762',
                'longitude': '139.6503',
                'contact_person': '山田太郎',  # Yamada Taro in Japanese
                'contact_method': 'yamada.taro@example.com',
                'grid_connection_date': '2023-01-15 10:30:00',
                'asset_number': 'AST001',
                'customer_name': 'Sample Customer',
                'timezone': '+09:00',
                'asset_name_oem': 'OEM Solar Farm 001',
                'cod': '2023-01-15 10:30:00',
                'operational_cod': '2023-02-01 00:00:00',
                'portfolio': 'ポートフォリオA',  # Portfolio A in Japanese
                'y1_degradation': '2.5',
                'anual_degradation': '0.5',
                'api_name': 'sample_api',
                'api_key': 'sample_api_key_123',
                'tilt_configs_json': '[{"tilt_deg":25,"azimuth_deg":0,"panel_count":100}]',
                'altitude_m': '100',
                'albedo': '0.2',
                'pv_syst_pr': '0.82',
                'satellite_irradiance_source_asset_code': ''
            }]
        elif table_name == 'device_list':
            filename = 'device_list_template.csv'
            headers = [
                'device_id', 'device_name', 'device_code', 'device_type_id',
                'device_serial', 'device_model', 'device_make', 'latitude',
                'longitude', 'optimizer_no', 'parent_code', 'device_type',
                'software_version', 'country', 'string_no', 'connected_strings',
                'device_sub_group', 'dc_cap', 'device_source', 'ac_capacity',
                'equipment_warranty_start_date', 'equipment_warranty_expire_date',
                'epc_warranty_start_date', 'epc_warranty_expire_date',
                'calibration_frequency', 'pm_frequency', 'visual_inspection_frequency',
                'bess_capacity', 'yom', 'nomenclature', 'location',
                # PV Module Configuration Fields
                'module_datasheet_id', 'modules_in_series', 'installation_date',
                'tilt_angle', 'azimuth_angle', 'mounting_type',
                'expected_soiling_loss', 'shading_factor', 'measured_degradation_rate',
                'last_performance_test_date', 'operational_notes', 'power_model_id',
                'model_fallback_enabled'
            ]
            sample_data = [{
                'device_id': 'DEV_001',
                'device_name': 'サンプルインバーター',  # Sample Inverter in Japanese
                'device_code': 'INV001',
                'device_type_id': 'TYPE_001',
                'device_serial': 'SN123456789',
                'device_model': 'モデルX100',  # Model X100 in Japanese
                'device_make': 'ソーラーテック',  # SolarTech in Japanese
                'latitude': '35.6762',
                'longitude': '139.6503',
                'optimizer_no': '1',
                'parent_code': 'PARENT_001',
                'device_type': 'インバーター',  # Inverter in Japanese
                'software_version': 'v2.1.5',
                'country': '日本',  # Japan in Japanese
                'string_no': 'STRING_01',
                'connected_strings': 'STRING_01,STRING_02',
                'device_sub_group': 'グループA',  # Group A in Japanese
                'dc_cap': '100.50',
                'device_source': '手動',  # Manual in Japanese
                'ac_capacity': '95.50',
                'equipment_warranty_start_date': '2023-01-15 00:00:00',
                'equipment_warranty_expire_date': '2028-01-15 00:00:00',
                'epc_warranty_start_date': '2023-01-15 00:00:00',
                'epc_warranty_expire_date': '2026-01-15 00:00:00',
                'calibration_frequency': 'Monthly',
                'pm_frequency': 'Quarterly',
                'visual_inspection_frequency': 'Monthly',
                'bess_capacity': '50.00',
                'yom': '2023',
                'nomenclature': 'INV-001-SOLAR-TECH',
                'location': 'Tokyo Office',
                # PV Module Configuration Fields (Optional)
                'module_datasheet_id': '',  # Leave blank or use ID from PV Module Library
                'modules_in_series': '24',  # Number of modules per string
                'installation_date': '2023-01-15',
                'tilt_angle': '30.0',  # Degrees
                'azimuth_angle': '180.0',  # Degrees (180 = South)
                'mounting_type': 'Fixed',  # Fixed, Single-Axis Tracker, Dual-Axis Tracker, etc.
                'expected_soiling_loss': '2.0',  # Percentage
                'shading_factor': '0.5',  # Percentage
                'measured_degradation_rate': '0.5',  # Percentage per year
                'last_performance_test_date': '2023-06-15',
                'operational_notes': 'Sample notes about PV configuration',
                'power_model_id': '',  # Leave blank or use ID from Power Model Registry
                'model_fallback_enabled': 'TRUE'  # TRUE or FALSE
            }]
        elif table_name == 'device_mapping':
            filename = 'device_mapping_template.csv'
            headers = [
                'id', 'asset_code', 'device_type', 'oem_tag', 'discription',
                'data_type', 'units', 'metric', 'fault_code', 'module_no',
                'default_value'
            ]
            sample_data = [{
                'id': '1',
                'asset_code': 'SAMPLE_001',
                'device_type': 'インバーター',  # Inverter in Japanese
                'oem_tag': 'AC_POWER',
                'discription': 'AC電力出力',  # AC Power Output in Japanese
                'data_type': 'FLOAT',
                'units': 'kW',
                'metric': '電力',  # power in Japanese
                'fault_code': 'F001',
                'module_no': 'MOD_01',
                'default_value': '0.0'
            }]
        elif table_name == 'budget_values':
            filename = 'budget_values_template.csv'
            headers = [
                'asset_number', 'asset_code', 'month_str', 'month_date', 
                'bd_production', 'bd_ghi', 'bd_gti'
            ]
            # Generate sample data for all 12 months
            months_data = [
                ('JAN', '2024-01-01'), ('FEB', '2024-02-01'), ('MAR', '2024-03-01'),
                ('APR', '2024-04-01'), ('MAY', '2024-05-01'), ('JUN', '2024-06-01'),
                ('JUL', '2024-07-01'), ('AUG', '2024-08-01'), ('SEP', '2024-09-01'),
                ('OCT', '2024-10-01'), ('NOV', '2024-11-01'), ('DEC', '2024-12-01')
            ]
            sample_data = []
            for month_str, month_date in months_data:
                sample_data.append({
                    'asset_number': 'ENTER_ASSET_NUMBER',
                    'asset_code': 'ENTER_ASSET_CODE',
                    'month_str': month_str,
                    'month_date': month_date,
                    'bd_production': '100.0',
                    'bd_ghi': '150.0',
                    'bd_gti': '150.0'
                })
        elif table_name == 'ic_budget':
            filename = 'ic_budget_template.csv'
            headers = [
                'asset_code', 'asset_number', 'month_str', 'month_date', 'ic_bd_production'
            ]
            # Generate sample data for all 12 months with current year
            from datetime import datetime
            current_year = datetime.now().year
            months_data = [
                ('JAN', f'{current_year}-01-01'), ('FEB', f'{current_year}-02-01'), ('MAR', f'{current_year}-03-01'),
                ('APR', f'{current_year}-04-01'), ('MAY', f'{current_year}-05-01'), ('JUN', f'{current_year}-06-01'),
                ('JUL', f'{current_year}-07-01'), ('AUG', f'{current_year}-08-01'), ('SEP', f'{current_year}-09-01'),
                ('OCT', f'{current_year}-10-01'), ('NOV', f'{current_year}-11-01'), ('DEC', f'{current_year}-12-01')
            ]
            sample_data = []
            for month_str, month_date in months_data:
                sample_data.append({
                    'asset_code': 'ENTER_ASSET_CODE',
                    'asset_number': 'ENTER_ASSET_NUMBER',
                    'month_str': month_str,
                    'month_date': month_date,
                    'ic_bd_production': '100.0'
                })
        elif table_name == 'asset_adapter_config':
            filename = 'asset_adapter_config_template.csv'
            headers = [
                'asset_code', 'adapter_id', 'adapter_account_id', 'enabled', 'acquisition_interval_minutes',
                'api_url', 'api_key', 'summarization', 'processing_keys', 'terrain_shading',
                'time_stamp_type', 'tilt', 'azimuth', 'linked_asset_codes',
                'solargis_region', 'daily_run_local_time', 'daily_run_timezone'
            ]
            sample_data = [{
                'asset_code': 'ENTER_ASSET_CODE',
                'adapter_id': 'solargis',
                # adapter_account_id: leave blank when using inline credentials;
                # set to an existing AdapterAccount.id when using shared account config.
                'adapter_account_id': '',
                'enabled': 'Yes',
                'acquisition_interval_minutes': '5',
                'api_url': 'https://solargis.info/ws/rest/datadelivery/request',
                'api_key': 'YOUR_API_KEY',
                'summarization': 'MIN_5',
                'processing_keys': 'GHI DNI DIF GTI PVOUT TMOD TEMP WS WD RH CI_FLAG',
                'terrain_shading': 'No',
                'time_stamp_type': 'CENTER',
                'tilt': '0',
                'azimuth': '180',
                'linked_asset_codes': '[]',
                'solargis_region': '',
                'daily_run_local_time': '',
                'daily_run_timezone': ''
            }]
        elif table_name == 'assets_contracts':
            filename = 'assets_contracts_template.csv'
            headers = [f.name for f in assets_contracts._meta.fields if f.name not in ('created_at', 'updated_at')]
            sample_data = [{
                'asset_number': 'ENTER_ASSET_NUMBER',
                'asset_code': 'ENTER_ASSET_CODE',
                'customer_asset_name': 'Sample Customer Asset',
                'contractor_name': 'Sample Contractor',
                'spv_name': 'Sample SPV',
                'contract_start_date': '2026-01-01',
                'contract_end_date': '2036-12-31',
                'contract_billing_cycle': 'monthly',
                'contract_billing_cycle_start_day': '1',
                'contract_billing_cycle_end_day': '31',
                'currency_code': 'SGD',
                'sp_account_no': 'SP-123456',
                'rooftop_self_consumption_rate': '0.125',
                'rooftop_self_consumption_tax': '0.09',
            }]
        elif table_name == 'device_operating_state':
            filename = 'device_operating_state_template.csv'
            headers = [
                'adapter_id',
                'device_type',
                'state_value',
                'oem_state_label',
                'internal_state',
                'is_normal',
                'fault_code',
            ]
            sample_data = [{
                'adapter_id': 'fusion_solar',
                'device_type': 'inverter',
                'state_value': '512',
                'oem_state_label': 'Grid-connected',
                'internal_state': 'NORMAL',
                'is_normal': 'Yes',
                'fault_code': '',
            }]
        elif table_name == 'spare_master':
            filename = 'spare_master_template.csv'
            headers = [
                'spare_code', 'spare_name', 'description', 'category',
                'unit', 'min_stock', 'max_stock', 'is_critical'
            ]
            sample_data = [{
                'spare_code': 'SPARE-001',
                'spare_name': 'Sample Spare Part',
                'description': 'Description of the spare part',
                'category': 'Electrical',
                'unit': 'Pcs',
                'min_stock': '10',
                'max_stock': '100',
                'is_critical': 'Yes'
            }]
        elif table_name == 'location_master':
            filename = 'location_master_template.csv'
            headers = [
                'location_code', 'location_name', 'location_type'
            ]
            sample_data = [{
                'location_code': 'WH-001',
                'location_name': 'Main Warehouse',
                'location_type': 'Warehouse'
            }]
        elif table_name == 'spare_site_map':
            filename = 'spare_site_map_template.csv'
            headers = [
                'spare_id', 'asset_code', 'location_id', 'is_active'
            ]
            sample_data = [{
                'spare_id': '1',
                'asset_code': 'ENTER_ASSET_CODE',
                'location_id': '1',
                'is_active': 'Yes'
            }]
        elif table_name == 'stock_entry':
            filename = 'stock_entry_template.csv'
            headers = [
                'spare_id', 'location_id', 'quantity', 'entry_type',
                'reference_number', 'remarks'
            ]
            sample_data = [{
                'spare_id': '1',
                'location_id': '1',
                'quantity': '10.00',
                'entry_type': 'Purchase',
                'reference_number': 'PO-001',
                'remarks': 'Initial stock entry'
            }]
        elif table_name == 'stock_issue':
            filename = 'stock_issue_template.csv'
            headers = [
                'spare_id', 'location_id', 'quantity', 'issue_type',
                'ticket_id', 'issued_to', 'remarks'
            ]
            sample_data = [{
                'spare_id': '1',
                'location_id': '1',
                'quantity': '5.00',
                'issue_type': 'Breakdown',
                'ticket_id': '',  # Optional - leave blank if not linked to ticket
                'issued_to': 'Site A Pump',
                'remarks': 'Issued for maintenance'
            }]
        else:
            return JsonResponse({'error': 'Invalid table name'}, status=400)

        # Create CSV response with UTF-8 encoding
        response = HttpResponse(content_type='text/csv; charset=utf-8')
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        
        # Add UTF-8 BOM for better Excel compatibility
        response.write('\ufeff')
        
        writer = csv.writer(response)
        
        # Write headers
        writer.writerow(headers)
        
        # Write sample data
        for row_data in sample_data:
            row = [row_data.get(header, '') for header in headers]
            writer.writerow(row)
        
        return response
        
    except Exception as e:
        logger.error(f"Error downloading template for {table_name}: {str(e)}")
        return JsonResponse({'error': str(e)}, status=500)