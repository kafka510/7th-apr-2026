
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.db import transaction

from accounts.decorators import role_required


from ..models import (
    DataImportLog, AssetList, device_list, device_mapping, budget_values, ic_budget, assets_contracts
)
import pandas as pd

from .shared.utilities import (
	ensure_unicode_string, detect_file_encoding
)
from .shared.validators import (
    validate_csv_structure, parse_date_safely, validate_ic_budget_dates_batch,
    validate_csv_requirements, validate_budget_values_data, create_data_backup
)
from .shared import validate_csv_upload



#@csrf_exempt
@login_required
@role_required(allowed_roles=['admin'])
def upload_site_onboarding_data(request):
    """Upload CSV data for asset_list, device_list, or device_mapping"""
    if request.method != 'POST':
        return JsonResponse({'error': 'Only POST method allowed'}, status=405)
    
    try:
        table_name = request.POST.get('table_name')
        csv_file = request.FILES.get('csv_file')
        
        if not csv_file:
            return JsonResponse({'error': 'No file uploaded'}, status=400)
        
        # SECURITY: Validate file upload (type, size, etc.)
        try:
            validate_csv_upload(csv_file)
        except Exception as e:
            return JsonResponse({
                'error': f'File validation failed: {str(e)}'
            }, status=400)
        
        if not table_name or table_name not in ['asset_list', 'device_list', 'device_mapping', 'budget_values', 'ic_budget',
                                                 'asset_adapter_config', 'device_operating_state',
                                                 'spare_master', 'location_master', 'spare_site_map', 'stock_entry', 'stock_issue',
                                                 'assets_contracts']:
            return JsonResponse({'error': 'Invalid table name'}, status=400)
        
        # Read and parse CSV with enhanced encoding support
        try:
            # Detect encoding
            detected_encoding = detect_file_encoding(csv_file)
            csv_file.seek(0)
            
            # List of encodings to try, prioritizing detected encoding and Japanese encodings
            encodings_to_try = [
                detected_encoding,
                'utf-8',
                'utf-8-sig',  # UTF-8 with BOM
                'shift_jis',  # Japanese Shift JIS
                'cp932',      # Windows Japanese
                'euc-jp',     # Japanese EUC
                'iso-2022-jp', # Japanese JIS
                'latin1',
                'cp1252',
                'iso-8859-1'
            ]
            
            # Remove duplicates while preserving order
            encodings_to_try = list(dict.fromkeys(encodings_to_try))
            
            df = None
            last_error = None
            
            for encoding in encodings_to_try:
                try:
                    csv_file.seek(0)
                 
                    df = pd.read_csv(csv_file, encoding=encoding)
                 
                    
                   
                    break
                except (UnicodeDecodeError, UnicodeError) as e:
                    last_error = e
               
                    continue
                except Exception as e:
                    last_error = e
             
                    continue
            
            if df is None:
                raise Exception(f"Could not read CSV file with any encoding. Last error: {str(last_error)}")
            
            # CRITICAL: Enhanced validation for site onboarding data
            # First, validate CSV structure
            is_valid, validation_error, missing_fields, extra_fields = validate_csv_structure(df, table_name)
            
            if not is_valid:
                structure_error_response = {
                    'error': f'CSV validation failed: {validation_error}',
                    'details': {
                        'missing_required_fields': missing_fields,
                        'unexpected_fields': extra_fields,
                        'table_expected': table_name,
                        'csv_columns': list(df.columns),
                        'suggestion': f'Please ensure you are uploading the correct CSV file for {table_name.replace("_", " ").title()}'
                    }
                }
                
                # Ensure all values are JSON serializable
                def make_json_serializable(obj):
                    """Recursively convert numpy/pandas types to native Python types"""
                    if isinstance(obj, dict):
                        return {key: make_json_serializable(value) for key, value in obj.items()}
                    elif isinstance(obj, list):
                        return [make_json_serializable(item) for item in obj]
                    elif hasattr(obj, 'item'):  # numpy scalar
                        return obj.item()
                    elif hasattr(obj, 'tolist'):  # numpy array
                        return obj.tolist()
                    else:
                        return obj
                
                structure_error_response = make_json_serializable(structure_error_response)
                return JsonResponse(structure_error_response, status=400)
            
            # Apply enhanced validation for site onboarding data
            requirements_result = validate_csv_requirements(df, table_name, csv_file.name)
            
            # Build comprehensive validation response
            validation_warnings = []
            validation_errors = []
            
            if not requirements_result.get('valid', True):
                validation_errors.extend(requirements_result.get('requirements_failed', []))
            
            validation_warnings.extend(requirements_result.get('requirements_met', []))
            validation_warnings.extend(requirements_result.get('suggestions', []))
            
            # Special validation for budget_values
            if table_name == 'budget_values':
                budget_validation = validate_budget_values_data(df)
                if budget_validation.get('errors'):
                    validation_errors.extend(budget_validation['errors'])
                if budget_validation.get('warnings'):
                    validation_warnings.extend(budget_validation['warnings'])
            
            # Special validation for IC budget: validate dates before processing
            if table_name == 'ic_budget':
                date_validation_errors, date_validation_warnings, converted_df = validate_ic_budget_dates_batch(df, auto_convert=True)
                
                # If dates were auto-converted, use the converted DataFrame
                if converted_df is not None:
                    print(f"✅ Auto-converted dates from MM-DD-YYYY to DD-MM-YYYY format")
                    df = converted_df
                    # Add warnings to validation_warnings
                    for w in date_validation_warnings:
                        if w.get('type') == 'auto_converted':
                            validation_warnings.append(w.get('message', 'Auto-converted dates'))
                
                if date_validation_errors:
                    # Format errors for user-friendly display
                    error_messages = []
                    error_summary = {
                        'format_errors': 0,
                        'day_errors': 0,
                        'month_mismatch_errors': 0,
                        'missing_months_errors': 0,
                        'other_errors': 0
                    }
                    
                    for error in date_validation_errors:
                        error_type = error.get('type', 'unknown')
                        if error_type == 'format_detected_mm_dd_yyyy':
                            error_summary['format_errors'] += 1
                            error_messages.append({
                                'type': 'format_error',
                                'message': error.get('message', ''),
                                'asset_code': error.get('asset_code', ''),
                                'year': error.get('year', ''),
                                'rows': error.get('rows', []),
                                'total_rows': error.get('total_rows', 0)
                            })
                        elif error_type == 'day_not_01':
                            error_summary['day_errors'] += 1
                            error_messages.append({
                                'type': 'day_error',
                                'row': error.get('row', 0),
                                'message': error.get('message', ''),
                                'asset_code': error.get('asset_code', ''),
                                'date': error.get('date', '')
                            })
                        elif error_type == 'month_mismatch':
                            error_summary['month_mismatch_errors'] += 1
                            error_messages.append({
                                'type': 'month_mismatch',
                                'row': error.get('row', 0),
                                'message': error.get('message', ''),
                                'asset_code': error.get('asset_code', ''),
                                'month_str': error.get('month_str', ''),
                                'expected_month': error.get('expected_month', ''),
                                'actual_month': error.get('actual_month', ''),
                                'date': error.get('date', '')
                            })
                        elif error_type in ['missing_months', 'duplicate_months']:
                            error_summary['missing_months_errors'] += 1
                            error_messages.append({
                                'type': error_type,
                                'message': error.get('message', ''),
                                'asset_code': error.get('asset_code', ''),
                                'year': error.get('year', ''),
                                'expected': error.get('expected', 12),
                                'found': error.get('found', 0)
                            })
                        else:
                            error_summary['other_errors'] += 1
                            error_messages.append({
                                'type': error_type,
                                'row': error.get('row', 0),
                                'message': error.get('message', ''),
                                'asset_code': error.get('asset_code', '')
                            })
                    
                    # Build comprehensive error response
                    total_errors = len(date_validation_errors)
                    error_summary_text = []
                    if error_summary['format_errors'] > 0:
                        error_summary_text.append(f"{error_summary['format_errors']} format error(s)")
                    if error_summary['day_errors'] > 0:
                        error_summary_text.append(f"{error_summary['day_errors']} day validation error(s)")
                    if error_summary['month_mismatch_errors'] > 0:
                        error_summary_text.append(f"{error_summary['month_mismatch_errors']} month mismatch error(s)")
                    if error_summary['missing_months_errors'] > 0:
                        error_summary_text.append(f"{error_summary['missing_months_errors']} missing/duplicate month error(s)")
                    if error_summary['other_errors'] > 0:
                        error_summary_text.append(f"{error_summary['other_errors']} other error(s)")
                    
                    # Build detailed error message
                    detailed_message_parts = []
                    if error_summary['format_errors'] > 0:
                        detailed_message_parts.append(f"{error_summary['format_errors']} format error(s) - dates appear to be in MM-DD-YYYY format, expected DD-MM-YYYY")
                    if error_summary['day_errors'] > 0:
                        detailed_message_parts.append(f"{error_summary['day_errors']} day error(s) - day must be 01 for monthly values")
                    if error_summary['month_mismatch_errors'] > 0:
                        detailed_message_parts.append(f"{error_summary['month_mismatch_errors']} month mismatch error(s) - month_date doesn't match month_str")
                    if error_summary['missing_months_errors'] > 0:
                        detailed_message_parts.append(f"{error_summary['missing_months_errors']} missing/duplicate month error(s) - need exactly 12 months per asset/year")
                    if error_summary['other_errors'] > 0:
                        detailed_message_parts.append(f"{error_summary['other_errors']} other error(s)")
                    
                    detailed_error_message = f'Date validation failed: {total_errors} error(s) found. ' + ' | '.join(detailed_message_parts)
                    
                    # Build first few error examples for quick reference
                    error_examples = []
                    for err in error_messages[:5]:
                        if err.get('message'):
                            error_examples.append(err['message'])
                    
                    error_response = {
                        'success': False,
                        'error': detailed_error_message,
                        'message': f'❌ Validation Failed: {", ".join(error_summary_text)}',
                        'validation_errors': error_messages[:50],  # Limit to first 50 errors
                        'error_examples': error_examples[:5],  # First 5 examples for quick view
                        'total_errors': total_errors,
                        'error_summary': error_summary,
                        'help_text': 'Please fix the date format issues and ensure:\n' +
                                   '1. Dates are in DD-MM-YYYY format (e.g., 01-12-2026)\n' +
                                   '2. Day is always 01 for monthly values\n' +
                                   '3. Month numbers (1-12) match the month_str column (JAN=1, FEB=2, etc.)\n' +
                                   '4. All 12 months are present for each asset/year'
                    }
                    
                    # Ensure all values are JSON serializable
                    def make_json_serializable(obj):
                        """Recursively convert numpy/pandas types to native Python types"""
                        if isinstance(obj, dict):
                            return {key: make_json_serializable(value) for key, value in obj.items()}
                        elif isinstance(obj, list):
                            return [make_json_serializable(item) for item in obj]
                        elif hasattr(obj, 'item'):  # numpy scalar
                            return obj.item()
                        elif hasattr(obj, 'tolist'):  # numpy array
                            return obj.tolist()
                        else:
                            return obj
                    
                    error_response = make_json_serializable(error_response)
                    return JsonResponse(error_response, status=400)
                
                # Add warnings if any
                if date_validation_warnings:
                    validation_warnings.extend(date_validation_warnings)
            
            # If there are critical validation failures, return error
            if validation_errors:
                error_response = {
                    'error': f'Site onboarding validation failed: {len(validation_errors)} requirement(s) not met',
                    'validation_errors': validation_errors,
                    'validation_warnings': validation_warnings,
                    'requirements_failed': requirements_result.get('requirements_failed', []),
                    'suggestions': requirements_result.get('suggestions', []),
                    'file_statistics': {
                        'total_rows': len(df),
                        'total_columns': len(df.columns),
                        'empty_rows': int(df.isnull().all(axis=1).sum()),
                        'missing_data_count': int(df.isnull().sum().sum())
                    }
                }
                
                # Ensure all values are JSON serializable
                def make_json_serializable(obj):
                    """Recursively convert numpy/pandas types to native Python types"""
                    if isinstance(obj, dict):
                        return {key: make_json_serializable(value) for key, value in obj.items()}
                    elif isinstance(obj, list):
                        return [make_json_serializable(item) for item in obj]
                    elif hasattr(obj, 'item'):  # numpy scalar
                        return obj.item()
                    elif hasattr(obj, 'tolist'):  # numpy array
                        return obj.tolist()
                    else:
                        return obj
                
                error_response = make_json_serializable(error_response)
                return JsonResponse(error_response, status=400)
            
            print(f"CSV validation passed for {table_name}")
            
            # Create backup before making any changes
            backup_file = create_data_backup(table_name, request.user.id)
            if backup_file:
                print(f"Data backup created: {backup_file}")
            else:
                print("Warning: Could not create backup")
            
            success_count = 0
            error_count = 0
            errors = []
            
            # Ensure database connection uses proper charset
            from django.db import connection
            if connection.vendor == 'postgresql':
                with connection.cursor() as cursor:
                    cursor.execute("SET client_encoding TO 'UTF8'")
            elif connection.vendor == 'mysql':
                with connection.cursor() as cursor:
                    cursor.execute("SET NAMES utf8mb4 COLLATE utf8mb4_unicode_ci")
            
            # Process each row individually to avoid full rollback on single row errors
            print(f"Processing {len(df)} rows for {table_name}")
            for index, row in df.iterrows():
                try:
                    # Skip empty rows
                    if row.isnull().all():
                        print(f"Skipping empty row {index + 2}")
                        continue
                    
                    print(f"Processing row {index + 2}: {row.get('asset_code', 'N/A')} - {row.get('device_type', 'N/A')} - {row.get('metric', 'N/A')}")
                        
                    with transaction.atomic():
                        if table_name == 'asset_list':
                            # Use raw SQL to insert asset data with proper Unicode handling
                            from django.db import connection
                            import json as json_module
                            tilt_configs_raw = row.get('tilt_configs_json') or row.get('tilt_configs')
                            tilt_configs_val = None
                            if pd.notna(tilt_configs_raw) and str(tilt_configs_raw).strip():
                                try:
                                    raw = str(tilt_configs_raw).strip()
                                    tilt_configs_val = json_module.dumps(json_module.loads(raw)) if raw else None
                                except (ValueError, TypeError):
                                    tilt_configs_val = None
                            altitude_m_val = float(row.get('altitude_m')) if pd.notna(row.get('altitude_m')) and str(row.get('altitude_m')).strip() else None
                            albedo_val = float(row.get('albedo')) if pd.notna(row.get('albedo')) and str(row.get('albedo')).strip() else None
                            pv_syst_pr_val = float(row.get('pv_syst_pr')) if pd.notna(row.get('pv_syst_pr')) and str(row.get('pv_syst_pr')).strip() else None
                            with connection.cursor() as cursor:
                                timezone_value = ensure_unicode_string(row.get('timezone', ''))
                                if not timezone_value:
                                    raise ValueError("timezone is required for asset_list")
                                cols = [
                                    'asset_code', 'asset_name', 'provider_asset_id', 'capacity', 'address', 'country',
                                    'latitude', 'longitude', 'contact_person', 'contact_method',
                                    'grid_connection_date', 'asset_number', 'timezone', 'asset_name_oem',
                                    'customer_name',
                                    'cod', 'operational_cod', 'portfolio', 'y1_degradation', 'anual_degradation',
                                    'api_name', 'api_key', 'tilt_configs', 'altitude_m', 'albedo', 'pv_syst_pr',
                                    'satellite_irradiance_source_asset_code',
                                ]
                                placeholders = [
                                    '%s::jsonb' if c == 'tilt_configs' else '%s'
                                    for c in cols
                                ]
                                sql = """
                                    INSERT INTO asset_list ({cols})
                                    VALUES ({ph})
                                    ON CONFLICT (asset_code) DO UPDATE SET
                                        asset_name = EXCLUDED.asset_name,
                                        provider_asset_id = EXCLUDED.provider_asset_id,
                                        capacity = EXCLUDED.capacity,
                                        address = EXCLUDED.address,
                                        country = EXCLUDED.country,
                                        latitude = EXCLUDED.latitude,
                                        longitude = EXCLUDED.longitude,
                                        contact_person = EXCLUDED.contact_person,
                                        contact_method = EXCLUDED.contact_method,
                                        grid_connection_date = EXCLUDED.grid_connection_date,
                                        asset_number = EXCLUDED.asset_number,
                                        timezone = EXCLUDED.timezone,
                                        asset_name_oem = EXCLUDED.asset_name_oem,
                                        customer_name = EXCLUDED.customer_name,
                                        cod = EXCLUDED.cod,
                                        operational_cod = EXCLUDED.operational_cod,
                                        portfolio = EXCLUDED.portfolio,
                                        y1_degradation = EXCLUDED.y1_degradation,
                                        anual_degradation = EXCLUDED.anual_degradation,
                                        api_name = EXCLUDED.api_name,
                                        api_key = EXCLUDED.api_key,
                                        tilt_configs = EXCLUDED.tilt_configs,
                                        altitude_m = EXCLUDED.altitude_m,
                                        albedo = EXCLUDED.albedo,
                                        pv_syst_pr = EXCLUDED.pv_syst_pr,
                                        satellite_irradiance_source_asset_code = EXCLUDED.satellite_irradiance_source_asset_code
                                """.format(
                                    cols=", ".join(cols),
                                    ph=", ".join(placeholders),
                                )
                                cursor.execute(
                                    sql,
                                    [
                                        ensure_unicode_string(row.get('asset_code', '')),
                                        ensure_unicode_string(row.get('asset_name', '')),
                                        ensure_unicode_string(row.get('provider_asset_id', '')) or None,
                                        float(row.get('capacity', 0)) if pd.notna(row.get('capacity')) else None,
                                        ensure_unicode_string(row.get('address', '')),
                                        ensure_unicode_string(row.get('country', '')),
                                        float(row.get('latitude', 0)) if pd.notna(row.get('latitude')) else None,
                                        float(row.get('longitude', 0)) if pd.notna(row.get('longitude')) else None,
                                        ensure_unicode_string(row.get('contact_person', '')),
                                        ensure_unicode_string(row.get('contact_method', '')),
                                        pd.to_datetime(row.get('grid_connection_date')) if pd.notna(row.get('grid_connection_date')) else None,
                                        ensure_unicode_string(row.get('asset_number', '')),
                                        timezone_value,
                                        ensure_unicode_string(row.get('asset_name_oem', '')),
                                        ensure_unicode_string(row.get('customer_name', '')),
                                        pd.to_datetime(row.get('cod')) if pd.notna(row.get('cod')) else None,
                                        pd.to_datetime(row.get('operational_cod')) if pd.notna(row.get('operational_cod')) else None,
                                        ensure_unicode_string(row.get('portfolio', '')),
                                        float(row.get('y1_degradation')) if pd.notna(row.get('y1_degradation')) else None,
                                        float(row.get('anual_degradation')) if pd.notna(row.get('anual_degradation')) else None,
                                        ensure_unicode_string(row.get('api_name', '')),
                                        ensure_unicode_string(row.get('api_key', '')),
                                        tilt_configs_val,
                                        altitude_m_val,
                                        albedo_val,
                                        pv_syst_pr_val,
                                        (ensure_unicode_string(str(row.get('satellite_irradiance_source_asset_code', '') or '').strip()) or None)
                                        if pd.notna(row.get('satellite_irradiance_source_asset_code'))
                                        and str(row.get('satellite_irradiance_source_asset_code', '')).strip()
                                        else None,
                                    ],
                                )
                            success_count += 1
                        elif table_name == 'device_list':
                            # Use raw SQL to insert device data
                            from django.db import connection
                            from decimal import Decimal, InvalidOperation
                            with connection.cursor() as cursor:
                                def _normalize_excel_id(s: str) -> str:
                                    """
                                    Normalize IDs coming from Excel/CSV:
                                    - Strip leading apostrophe (Excel text marker)
                                    - Convert scientific notation (e.g. 1.00E+15) to plain integer string when integral
                                    """
                                    raw = ensure_unicode_string(s or '').strip()
                                    if raw.startswith("'"):
                                        raw = raw[1:].strip()
                                    if not raw:
                                        return ''
                                    if raw.isdigit():
                                        return raw
                                    try:
                                        d = Decimal(raw)
                                        if d == d.to_integral_value():
                                            return format(d.to_integral_value(), 'f')
                                    except (InvalidOperation, ValueError):
                                        pass
                                    return raw

                                raw_device_id = ensure_unicode_string(row.get('device_id', ''))
                                raw_device_id = _normalize_excel_id(raw_device_id)
                                raw_device_code = _normalize_excel_id(row.get('device_code', ''))
                                cursor.execute("""
                                    INSERT INTO device_list (
                                        device_id, device_name, device_code, device_type_id,
                                        device_serial, device_model, device_make, latitude,
                                        longitude, optimizer_no, parent_code, device_type,
                                        software_version, country, string_no, connected_strings,
                                        device_sub_group, dc_cap, device_source, ac_capacity,
                                        equipment_warranty_start_date, equipment_warranty_expire_date,
                                        epc_warranty_start_date, epc_warranty_expire_date,
                                        calibration_frequency, pm_frequency, visual_inspection_frequency,
                                        bess_capacity, yom, nomenclature, location
                                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                                ON CONFLICT (device_id) DO UPDATE SET
                                    device_name = EXCLUDED.device_name,
                                    device_code = EXCLUDED.device_code,
                                    device_type_id = EXCLUDED.device_type_id,
                                    device_serial = EXCLUDED.device_serial,
                                    device_model = EXCLUDED.device_model,
                                    device_make = EXCLUDED.device_make,
                                    latitude = EXCLUDED.latitude,
                                    longitude = EXCLUDED.longitude,
                                    optimizer_no = EXCLUDED.optimizer_no,
                                    parent_code = EXCLUDED.parent_code,
                                    device_type = EXCLUDED.device_type,
                                    software_version = EXCLUDED.software_version,
                                    country = EXCLUDED.country,
                                    string_no = EXCLUDED.string_no,
                                    connected_strings = EXCLUDED.connected_strings,
                                    device_sub_group = EXCLUDED.device_sub_group,
                                    dc_cap = EXCLUDED.dc_cap,
                                    device_source = EXCLUDED.device_source,
                                    ac_capacity = EXCLUDED.ac_capacity,
                                    equipment_warranty_start_date = EXCLUDED.equipment_warranty_start_date,
                                    equipment_warranty_expire_date = EXCLUDED.equipment_warranty_expire_date,
                                    epc_warranty_start_date = EXCLUDED.epc_warranty_start_date,
                                    epc_warranty_expire_date = EXCLUDED.epc_warranty_expire_date,
                                    calibration_frequency = EXCLUDED.calibration_frequency,
                                    pm_frequency = EXCLUDED.pm_frequency,
                                    visual_inspection_frequency = EXCLUDED.visual_inspection_frequency,
                                    bess_capacity = EXCLUDED.bess_capacity,
                                    yom = EXCLUDED.yom,
                                    nomenclature = EXCLUDED.nomenclature,
                                    location = EXCLUDED.location
                                """, [
                                    raw_device_id,
                                ensure_unicode_string(row.get('device_name', '')),
                                raw_device_code,
                                ensure_unicode_string(row.get('device_type_id', '')),
                                ensure_unicode_string(row.get('device_serial', '')),
                                ensure_unicode_string(row.get('device_model', '')),
                                ensure_unicode_string(row.get('device_make', '')),
                                float(row.get('latitude', 0)) if pd.notna(row.get('latitude')) else 0,
                                float(row.get('longitude', 0)) if pd.notna(row.get('longitude')) else 0,
                                int(row.get('optimizer_no', 0)) if pd.notna(row.get('optimizer_no')) else 0,
                                ensure_unicode_string(row.get('parent_code', '')),
                                ensure_unicode_string(row.get('device_type', '')),
                                ensure_unicode_string(row.get('software_version', '')),
                                ensure_unicode_string(row.get('country', '')),
                                ensure_unicode_string(row.get('string_no', '')),
                                ensure_unicode_string(row.get('connected_strings', '')),
                                ensure_unicode_string(row.get('device_sub_group', '')),
                                float(row.get('dc_cap', 0)) if pd.notna(row.get('dc_cap')) else None,
                                ensure_unicode_string(row.get('device_source', '')),
                                float(row.get('ac_capacity', 0)) if pd.notna(row.get('ac_capacity')) else None,
                                pd.to_datetime(row.get('equipment_warranty_start_date')) if pd.notna(row.get('equipment_warranty_start_date')) else None,
                                pd.to_datetime(row.get('equipment_warranty_expire_date')) if pd.notna(row.get('equipment_warranty_expire_date')) else None,
                                pd.to_datetime(row.get('epc_warranty_start_date')) if pd.notna(row.get('epc_warranty_start_date')) else None,
                                pd.to_datetime(row.get('epc_warranty_expire_date')) if pd.notna(row.get('epc_warranty_expire_date')) else None,
                                ensure_unicode_string(row.get('calibration_frequency', row.get('calibration_frequnecy', ''))),  # Handle typo in CSV
                                ensure_unicode_string(row.get('pm_frequency', '')),
                                ensure_unicode_string(row.get('visual_inspection_frequency', '')),
                                float(row.get('bess_capacity', 0)) if pd.notna(row.get('bess_capacity')) else None,
                                ensure_unicode_string(row.get('yom', '')),
                                ensure_unicode_string(row.get('nomenclature', '')),
                                ensure_unicode_string(row.get('location', ''))
                            ])
                            success_count += 1
                        elif table_name == 'device_mapping':
                            # Use raw SQL to insert device mapping data with proper unique constraint
                            from django.db import connection
                            with connection.cursor() as cursor:
                                # First check if record exists based on unique constraint (asset_code, oem_tag, metric, device_type)
                                # This allows multiple sensors to have the same metric but different oem_tags
                                asset_code = ensure_unicode_string(row.get('asset_code', ''))
                                metric = ensure_unicode_string(row.get('metric', ''))
                                device_type = ensure_unicode_string(row.get('device_type', ''))
                                oem_tag = ensure_unicode_string(row.get('oem_tag', ''))
                                
                                print(f"  Device mapping: {asset_code} - {device_type} - {metric} - {oem_tag}")
                                
                                cursor.execute("""
                                    SELECT id FROM device_mapping 
                                    WHERE asset_code = %s AND oem_tag = %s AND metric = %s AND device_type = %s
                                """, [asset_code, oem_tag, metric, device_type])
                                
                                existing_record = cursor.fetchone()
                                
                                if existing_record:
                                    # Update existing record
                                    mapping_id = existing_record[0]
                                    print(f"    Updating existing record ID: {mapping_id}")
                                    # Only update fields that have values, skip empty optional fields
                                    update_fields = []
                                    update_values = []
                                    
                                    # Always update oem_tag (required field)
                                    update_fields.append("oem_tag = %s")
                                    update_values.append(ensure_unicode_string(row.get('oem_tag', '')))
                                    
                                    # Handle optional fields - only update if they have values
                                    # SECURITY: Whitelist of allowed field names to prevent SQL injection
                                    ALLOWED_DEVICE_MAPPING_UPDATE_FIELDS = {
                                        'discription', 'data_type', 'units', 'fault_code', 
                                        'module_no', 'default_value', 'oem_tag'
                                    }
                                    
                                    optional_fields = {
                                        'discription': row.get('discription', row.get('description', '')),
                                        'data_type': row.get('data_type', ''),
                                        'units': row.get('units', ''),
                                        'fault_code': row.get('fault_code', ''),
                                        'module_no': row.get('module_no', ''),
                                        'default_value': row.get('default_value', '')
                                    }
                                    
                                    for field_name, field_value in optional_fields.items():
                                        # SECURITY: Only process fields that are in the whitelist
                                        if field_name in ALLOWED_DEVICE_MAPPING_UPDATE_FIELDS:
                                            if field_value and str(field_value).strip():  # Only update if not empty
                                                update_fields.append(f"{field_name} = %s")
                                                update_values.append(ensure_unicode_string(field_value))
                                    
                                    # Add the ID for WHERE clause
                                    update_values.append(mapping_id)
                                    
                                    cursor.execute(f"""
                                        UPDATE device_mapping SET
                                            {', '.join(update_fields)}
                                        WHERE id = %s
                                    """, update_values)
                                else:
                                    # Insert new record with auto-generated ID
                                    cursor.execute("SELECT COALESCE(MAX(id), 0) + 1 FROM device_mapping")
                                    mapping_id = cursor.fetchone()[0]
                                    print(f"    Inserting new record with ID: {mapping_id}")
                                    
                                    # Build dynamic INSERT for only non-empty fields
                                    insert_fields = ['id', 'asset_code', 'device_type', 'oem_tag', 'metric']
                                    insert_values = [
                                        int(mapping_id),
                                        asset_code,
                                        device_type,
                                        ensure_unicode_string(row.get('oem_tag', '')),
                                        metric
                                    ]
                                    
                                    # Add optional fields only if they have values
                                    # SECURITY: Whitelist of allowed field names to prevent SQL injection
                                    ALLOWED_DEVICE_MAPPING_INSERT_FIELDS = {
                                        'id', 'asset_code', 'device_type', 'oem_tag', 'metric',
                                        'discription', 'data_type', 'units', 'fault_code', 
                                        'module_no', 'default_value'
                                    }
                                    
                                    optional_fields = {
                                        'discription': row.get('discription', row.get('description', '')),
                                        'data_type': row.get('data_type', ''),
                                        'units': row.get('units', ''),
                                        'fault_code': row.get('fault_code', ''),
                                        'module_no': row.get('module_no', ''),
                                        'default_value': row.get('default_value', '')
                                    }
                                    
                                    for field_name, field_value in optional_fields.items():
                                        # SECURITY: Only process fields that are in the whitelist
                                        if field_name in ALLOWED_DEVICE_MAPPING_INSERT_FIELDS:
                                            if field_value and str(field_value).strip():  # Only insert if not empty
                                                insert_fields.append(field_name)
                                                insert_values.append(ensure_unicode_string(field_value))
                                    
                                    placeholders = ', '.join(['%s'] * len(insert_values))
                                    
                                    cursor.execute(f"""
                                        INSERT INTO device_mapping ({', '.join(insert_fields)})
                                        VALUES ({placeholders})
                                    """, insert_values)
                                success_count += 1
                                print(f"    Successfully processed device mapping record")
                        elif table_name == 'budget_values':
                            # Enhanced budget values processing with better error handling
                            try:
                                from django.db import connection
                                
                                # Validate required fields
                                asset_code = ensure_unicode_string(row.get('asset_code', ''))
                                month_str = ensure_unicode_string(row.get('month_str', ''))
                                
                                if not asset_code or not month_str:
                                    error_msg = f"Row {index + 2}: Missing required fields - asset_code: '{asset_code}', month_str: '{month_str}'"
                                    errors.append(error_msg)
                                    print(f"    ERROR: {error_msg}")
                                    error_count += 1
                                    continue
                                
                                # Validate numeric fields
                                try:
                                    bd_production = float(row.get('bd_production', 0)) if pd.notna(row.get('bd_production')) else 0
                                    bd_ghi = float(row.get('bd_ghi', 0)) if pd.notna(row.get('bd_ghi')) else 0
                                    bd_gti = float(row.get('bd_gti', 0)) if pd.notna(row.get('bd_gti')) else 0
                                except (ValueError, TypeError) as ve:
                                    error_msg = f"Row {index + 2}: Invalid numeric values - {str(ve)}"
                                    errors.append(error_msg)
                                    print(f"    ERROR: {error_msg}")
                                    error_count += 1
                                    continue
                                
                                print(f"    Processing budget: {asset_code} - {month_str} - Production: {bd_production}")
                                
                                with connection.cursor() as cursor:
                                    # Check if record exists based on unique constraint (asset_code, month_str)
                                    cursor.execute("""
                                        SELECT id FROM budget_values 
                                        WHERE asset_code = %s AND month_str = %s
                                    """, [asset_code, month_str])
                                    
                                    existing_record = cursor.fetchone()
                                    
                                    if existing_record:
                                        # Update existing record
                                        budget_id = existing_record[0]
                                        print(f"      Updating existing budget record ID: {budget_id}")
                                        cursor.execute("""
                                            UPDATE budget_values SET
                                                asset_number = %s,
                                                month_date = %s,
                                                bd_production = %s,
                                                bd_ghi = %s,
                                                bd_gti = %s
                                            WHERE id = %s
                                        """, [
                                            ensure_unicode_string(row.get('asset_number', '')),
                                            parse_date_safely(row.get('month_date')),
                                            bd_production,
                                            bd_ghi,
                                            bd_gti,
                                            budget_id
                                        ])
                                    else:
                                        # Insert new record (let database auto-generate ID)
                                        print(f"      Inserting new budget record")
                                        cursor.execute("""
                                            INSERT INTO budget_values (
                                                asset_number, asset_code, month_str, month_date,
                                                bd_production, bd_ghi, bd_gti
                                            ) VALUES (%s, %s, %s, %s, %s, %s, %s)
                                        """, [
                                            ensure_unicode_string(row.get('asset_number', '')),
                                            asset_code,
                                            month_str,
                                            parse_date_safely(row.get('month_date')),
                                            bd_production,
                                            bd_ghi,
                                            bd_gti
                                        ])
                                
                                print(f"    ✅ Successfully processed budget record")
                                success_count += 1
                                
                            except Exception as budget_error:
                                error_msg = f"Row {index + 2}: Budget processing error - {str(budget_error)}"
                                errors.append(error_msg)
                                print(f"    ❌ {error_msg}")
                                import traceback
                                print(f"    Traceback: {traceback.format_exc()}")
                                error_count += 1
                        elif table_name == 'ic_budget':
                            # Use raw SQL to insert IC budget data with proper unique constraint
                            from django.db import connection
                            with connection.cursor() as cursor:
                                # Check if record exists based on unique constraint (asset_code, month_str)
                                asset_code = ensure_unicode_string(row.get('asset_code', ''))
                                month_str = ensure_unicode_string(row.get('month_str', ''))
                                asset_number = ensure_unicode_string(row.get('asset_number', ''))
                                
                                # Parse and validate ic_bd_production
                                ic_bd_production_raw = row.get('ic_bd_production', 0)
                                ic_bd_production = float(ic_bd_production_raw) if pd.notna(ic_bd_production_raw) else 0
                                
                                # Parse month_date with proper format handling
                                month_date_raw = row.get('month_date')
                                month_date = parse_date_safely(month_date_raw)
                                print(f"    Parsed date: {month_date_raw} -> {month_date}")
                                
                                print(f"    IC Budget processing: {asset_code} - {month_str} - {month_date} - Production: {ic_bd_production}")
                                print(f"    Raw data: asset_number='{asset_number}', month_date='{month_date}', ic_bd_production_raw='{ic_bd_production_raw}'")
                                
                                # Check for existing record using asset_code + month_date (the new unique constraint)
                                if month_date:
                                    cursor.execute("""
                                        SELECT id FROM ic_budget 
                                        WHERE asset_code = %s AND month_date = %s
                                    """, [asset_code, month_date])
                                else:
                                    # Fallback to month_str if month_date is not available (shouldn't happen with proper data)
                                    print(f"    WARNING: month_date is None, falling back to month_str check")
                                    cursor.execute("""
                                        SELECT id FROM ic_budget 
                                        WHERE asset_code = %s AND month_str = %s
                                    """, [asset_code, month_str])
                                
                                existing_record = cursor.fetchone()
                                
                                if existing_record:
                                    # Update existing record
                                    ic_budget_id = existing_record[0]
                                    print(f"    Updating existing IC budget record ID: {ic_budget_id} for {asset_code} - {month_date}")
                                    cursor.execute("""
                                        UPDATE ic_budget SET
                                            asset_number = %s,
                                            month_str = %s,
                                            month_date = %s,
                                            ic_bd_production = %s
                                        WHERE id = %s
                                    """, [
                                        asset_number,
                                        month_str,
                                        month_date,
                                        ic_bd_production,
                                        ic_budget_id
                                    ])
                                    print(f"    Updated IC budget record with production: {ic_bd_production}")
                                else:
                                    # Insert new record
                                    print(f"    Inserting new IC budget record for {asset_code} - {month_date}")
                                    cursor.execute("""
                                        INSERT INTO ic_budget (
                                            asset_code, asset_number, month_str, month_date, ic_bd_production
                                        ) VALUES (%s, %s, %s, %s, %s)
                                    """, [
                                        asset_code,
                                        asset_number,
                                        month_str,
                                        month_date,
                                        ic_bd_production
                                    ])
                                    print(f"    Inserted new IC budget record with production: {ic_bd_production}")
                                
                                # Verify the data was saved correctly using month_date
                                if month_date:
                                    cursor.execute("""
                                        SELECT ic_bd_production FROM ic_budget 
                                        WHERE asset_code = %s AND month_date = %s
                                    """, [asset_code, month_date])
                                else:
                                    cursor.execute("""
                                        SELECT ic_bd_production FROM ic_budget 
                                        WHERE asset_code = %s AND month_str = %s
                                    """, [asset_code, month_str])
                                saved_record = cursor.fetchone()
                                if saved_record:
                                    print(f"    ✅ Verified: IC budget production saved as: {saved_record[0]}")
                                else:
                                    print(f"    ❌ ERROR: Could not verify IC budget record was saved!")
                                
                            success_count += 1
                        elif table_name == 'assets_contracts':
                            asset_number = ensure_unicode_string(row.get('asset_number', '')).strip()
                            asset_code = ensure_unicode_string(row.get('asset_code', '')).strip()
                            if not asset_number or not asset_code:
                                raise ValueError('asset_number and asset_code are required')

                            # Dynamic mapping: if the column name matches a model field, persist it.
                            model_fields = {
                                f.name: f for f in assets_contracts._meta.fields
                                if f.name not in ('id', 'created_at', 'updated_at')
                            }

                            def _coerce(field, raw):
                                if raw is None or (isinstance(raw, float) and pd.isna(raw)) or (hasattr(pd, 'isna') and pd.isna(raw)):
                                    return None
                                s = str(raw).strip()
                                if s == '':
                                    return None
                                internal = field.get_internal_type()
                                try:
                                    if internal == 'DateField':
                                        return parse_date_safely(raw)
                                    if internal in ('IntegerField', 'BigIntegerField', 'SmallIntegerField', 'PositiveIntegerField'):
                                        return int(float(s))
                                    if internal in ('DecimalField', 'FloatField'):
                                        return float(s)
                                    if internal == 'JSONField':
                                        import json as json_module
                                        try:
                                            return json_module.loads(s)
                                        except Exception:
                                            return {}
                                    return ensure_unicode_string(s)
                                except Exception:
                                    return ensure_unicode_string(s)

                            defaults = {'asset_code': asset_code}
                            for col in row.index:
                                key = str(col).strip().lower()
                                if key in model_fields and key not in ('asset_number',):
                                    defaults[key] = _coerce(model_fields[key], row.get(col))

                            assets_contracts.objects.update_or_create(
                                asset_number=asset_number,
                                defaults=defaults,
                            )
                            success_count += 1
                        elif table_name == 'asset_adapter_config':
                            from data_collection.models import AssetAdapterConfig
                            from ..models import AssetList
                            import json as json_module
                            asset_code = ensure_unicode_string(str(row.get('asset_code', '')).strip())
                            adapter_id = ensure_unicode_string(str(row.get('adapter_id', 'solargis')).strip()) or 'solargis'
                            if not asset_code:
                                raise ValueError('asset_code is required')
                            # Allow import even if asset is not yet in asset_list (config can be created first)
                            if not AssetList.objects.filter(asset_code=asset_code).exists():
                                pass  # proceed with adapter config import; add asset to asset_list separately if needed
                            enabled = str(row.get('enabled', 'Yes')).strip().lower() in ['yes', 'true', '1']
                            interval = int(row.get('acquisition_interval_minutes', 5)) if pd.notna(row.get('acquisition_interval_minutes')) else 5
                            interval = interval if interval in (5, 30, 1440) else min(max(interval, 5), 1440)
                            linked_raw = row.get('linked_asset_codes', '[]')
                            try:
                                linked = json_module.loads(linked_raw) if pd.notna(linked_raw) and str(linked_raw).strip() else []
                            except (ValueError, TypeError):
                                linked = []
                            config = {
                                'api_url': str(row.get('api_url', '')).strip() or 'https://solargis.info/ws/rest/datadelivery/request',
                                'api_key': str(row.get('api_key', '')).strip() if pd.notna(row.get('api_key')) else '',
                                'summarization': str(row.get('summarization', 'MIN_5')).strip() or 'MIN_5',
                                'processing_keys': str(row.get('processing_keys', '')).strip() or 'GHI DNI DIF GTI PVOUT TMOD TEMP WS WD RH CI_FLAG',
                                'terrain_shading': str(row.get('terrain_shading', 'No')).strip().lower() in ['yes', 'true', '1'],
                                'time_stamp_type': str(row.get('time_stamp_type', 'CENTER')).strip() or 'CENTER',
                                'tilt': float(row.get('tilt', 0)) if pd.notna(row.get('tilt')) and str(row.get('tilt')).strip() else 0,
                                'azimuth': float(row.get('azimuth', 180)) if pd.notna(row.get('azimuth')) and str(row.get('azimuth')).strip() else 180,
                                'linked_asset_codes': linked if isinstance(linked, list) else [],
                            }
                            if pd.notna(row.get('solargis_region')) and str(row.get('solargis_region')).strip():
                                config['solargis_region'] = str(row.get('solargis_region')).strip()
                            if pd.notna(row.get('daily_run_local_time')) and str(row.get('daily_run_local_time')).strip():
                                config['daily_run_local_time'] = str(row.get('daily_run_local_time')).strip()
                            if pd.notna(row.get('daily_run_timezone')) and str(row.get('daily_run_timezone')).strip():
                                config['daily_run_timezone'] = str(row.get('daily_run_timezone')).strip()
                            if pd.notna(row.get('asset_id')) and str(row.get('asset_id')).strip():
                                config['asset_id'] = str(row.get('asset_id')).strip()
                            # Optional adapter_account_id column: link config to an AdapterAccount when provided.
                            # IMPORTANT: do NOT overwrite existing adapter_account_id when CSV cell is blank.
                            adapter_account_raw = row.get('adapter_account_id', '')
                            defaults = {
                                'adapter_id': adapter_id,
                                'config': config,
                                'enabled': enabled,
                                'acquisition_interval_minutes': interval,
                            }
                            if pd.notna(adapter_account_raw) and str(adapter_account_raw).strip():
                                try:
                                    defaults['adapter_account_id'] = int(str(adapter_account_raw).strip())
                                except (TypeError, ValueError):
                                    # Ignore invalid values; keep existing adapter_account_id
                                    pass

                            obj, created = AssetAdapterConfig.objects.update_or_create(
                                asset_code=asset_code,
                                defaults=defaults,
                            )
                            success_count += 1
                        elif table_name == 'device_operating_state':
                            from data_collection.models import DeviceOperatingState
                            adapter_id = ensure_unicode_string(row.get('adapter_id', ''))
                            device_type = ensure_unicode_string(row.get('device_type', ''))
                            state_value = ensure_unicode_string(row.get('state_value', ''))
                            oem_state_label = ensure_unicode_string(row.get('oem_state_label', ''))
                            internal_state = ensure_unicode_string(row.get('internal_state', ''))
                            if not adapter_id or not device_type or not state_value:
                                raise ValueError('adapter_id, device_type and state_value are required')
                            is_normal_raw = row.get('is_normal', '')
                            is_normal = str(is_normal_raw).strip().lower() in ['1', 'true', 'yes', 'y']
                            fault_code = ensure_unicode_string(row.get('fault_code', ''))
                            DeviceOperatingState.objects.update_or_create(
                                adapter_id=adapter_id,
                                device_type=device_type,
                                state_value=state_value,
                                defaults={
                                    'oem_state_label': oem_state_label,
                                    'internal_state': internal_state,
                                    'is_normal': is_normal,
                                    'fault_code': fault_code or None,
                                },
                            )
                            success_count += 1
                        elif table_name == 'spare_master':
                            from ..models import SpareMaster
                            from django.db import connection
                            with connection.cursor() as cursor:
                                spare_code = ensure_unicode_string(row.get('spare_code', ''))
                                spare_name = ensure_unicode_string(row.get('spare_name', ''))
                                description = ensure_unicode_string(row.get('description', ''))
                                category = ensure_unicode_string(row.get('category', ''))
                                unit = ensure_unicode_string(row.get('unit', ''))
                                min_stock = int(row.get('min_stock', 0)) if pd.notna(row.get('min_stock')) else None
                                max_stock = int(row.get('max_stock', 0)) if pd.notna(row.get('max_stock')) else None
                                is_critical = str(row.get('is_critical', 'No')).strip().lower() in ['yes', 'true', '1']
                                
                                cursor.execute("""
                                    INSERT INTO Spare_Master (
                                        Spare_Code, Spare_Name, Description, Category,
                                        Unit, Min_Stock, Max_Stock, Is_Critical
                                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                                    ON CONFLICT (Spare_Code) DO UPDATE SET
                                        Spare_Name = EXCLUDED.Spare_Name,
                                        Description = EXCLUDED.Description,
                                        Category = EXCLUDED.Category,
                                        Unit = EXCLUDED.Unit,
                                        Min_Stock = EXCLUDED.Min_Stock,
                                        Max_Stock = EXCLUDED.Max_Stock,
                                        Is_Critical = EXCLUDED.Is_Critical
                                """, [spare_code, spare_name, description, category, unit, min_stock, max_stock, is_critical])
                            success_count += 1
                        elif table_name == 'location_master':
                            from ..models import LocationMaster
                            from django.db import connection
                            with connection.cursor() as cursor:
                                location_code = ensure_unicode_string(row.get('location_code', ''))
                                location_name = ensure_unicode_string(row.get('location_name', ''))
                                location_type = ensure_unicode_string(row.get('location_type', ''))
                                
                                cursor.execute("""
                                    INSERT INTO Location_Master (
                                        Location_Code, Location_Name, Location_Type
                                    ) VALUES (%s, %s, %s)
                                    ON CONFLICT (Location_Code) DO UPDATE SET
                                        Location_Name = EXCLUDED.Location_Name,
                                        Location_Type = EXCLUDED.Location_Type
                                """, [location_code, location_name, location_type])
                            success_count += 1
                        elif table_name == 'spare_site_map':
                            from ..models import SpareSiteMap, SpareMaster, AssetList, LocationMaster
                            from django.db import connection
                            with connection.cursor() as cursor:
                                spare_id = int(row.get('spare_id', 0)) if pd.notna(row.get('spare_id')) else None
                                asset_code = ensure_unicode_string(row.get('asset_code', ''))
                                location_id = int(row.get('location_id', 0)) if pd.notna(row.get('location_id')) else None
                                is_active = str(row.get('is_active', 'Yes')).strip().lower() in ['yes', 'true', '1']
                                
                                if not spare_id or not asset_code or not location_id:
                                    raise ValueError("Missing required fields: spare_id, asset_code, location_id")
                                
                                # Verify foreign keys exist
                                if not SpareMaster.objects.filter(spare_id=spare_id).exists():
                                    raise ValueError(f"Spare ID {spare_id} does not exist")
                                if not AssetList.objects.filter(asset_code=asset_code).exists():
                                    raise ValueError(f"Asset code {asset_code} does not exist")
                                if not LocationMaster.objects.filter(location_id=location_id).exists():
                                    raise ValueError(f"Location ID {location_id} does not exist")
                                
                                cursor.execute("""
                                    INSERT INTO Spare_Site_Map (
                                        Spare_ID_id, Asset_Code_id, Location_ID_id, Is_Active
                                    ) VALUES (%s, %s, %s, %s)
                                    ON CONFLICT (Spare_ID_id, Asset_Code_id, Location_ID_id) DO UPDATE SET
                                        Is_Active = EXCLUDED.Is_Active
                                """, [spare_id, asset_code, location_id, is_active])
                            success_count += 1
                        elif table_name == 'stock_entry':
                            from ..models import StockEntry, SpareMaster, LocationMaster
                            from django.utils import timezone
                            from django.db import connection
                            with connection.cursor() as cursor:
                                spare_id = int(row.get('spare_id', 0)) if pd.notna(row.get('spare_id')) else None
                                location_id = int(row.get('location_id', 0)) if pd.notna(row.get('location_id')) else None
                                quantity = float(row.get('quantity', 0)) if pd.notna(row.get('quantity')) else 0
                                entry_type = ensure_unicode_string(row.get('entry_type', ''))
                                reference_number = ensure_unicode_string(row.get('reference_number', ''))
                                remarks = ensure_unicode_string(row.get('remarks', ''))
                                
                                if not spare_id or not location_id or not quantity or not entry_type:
                                    raise ValueError("Missing required fields: spare_id, location_id, quantity, entry_type")
                                
                                # Get spare and location for denormalized fields
                                spare = SpareMaster.objects.get(spare_id=spare_id)
                                location = LocationMaster.objects.get(location_id=location_id)
                                
                                # Create entry using Django ORM to trigger balance update
                                entry = StockEntry.objects.create(
                                    spare=spare,
                                    spare_code=spare.spare_code,
                                    location=location,
                                    location_code=location.location_code,
                                    quantity=quantity,
                                    entry_type=entry_type,
                                    reference_number=reference_number,
                                    remarks=remarks,
                                    entry_date=timezone.now(),
                                    performed_by=request.user,
                                )
                                
                                # Update stock balance
                                from ..models import StockBalance
                                balance, created = StockBalance.objects.get_or_create(
                                    spare=spare,
                                    location=location,
                                    defaults={
                                        'spare_code': spare.spare_code,
                                        'location_code': location.location_code,
                                        'quantity': quantity,
                                        'unit': spare.unit,
                                    }
                                )
                                if not created:
                                    balance.quantity += quantity
                                    balance.save()
                                
                                # Create ledger entry
                                from ..models import StockLedger
                                StockLedger.objects.create(
                                    spare=spare,
                                    spare_code=spare.spare_code,
                                    location_code=location.location_code,
                                    transaction_type='IN',
                                    quantity=quantity,
                                    balance_after=balance.quantity,
                                    reference=reference_number,
                                    remarks=remarks,
                                    performed_by=request.user,
                                )
                            success_count += 1
                        elif table_name == 'stock_issue':
                            from ..models import StockIssue, StockBalance, StockLedger, SpareMaster, LocationMaster
                            from django.utils import timezone
                            from django.db import connection
                            with connection.cursor() as cursor:
                                spare_id = int(row.get('spare_id', 0)) if pd.notna(row.get('spare_id')) else None
                                location_id = int(row.get('location_id', 0)) if pd.notna(row.get('location_id')) else None
                                quantity = float(row.get('quantity', 0)) if pd.notna(row.get('quantity')) else 0
                                issue_type = ensure_unicode_string(row.get('issue_type', ''))
                                ticket_id = str(row.get('ticket_id', '')).strip() if pd.notna(row.get('ticket_id')) else None
                                issued_to = ensure_unicode_string(row.get('issued_to', ''))
                                remarks = ensure_unicode_string(row.get('remarks', ''))
                                
                                if not spare_id or not location_id or not quantity or not issue_type:
                                    raise ValueError("Missing required fields: spare_id, location_id, quantity, issue_type")
                                
                                # Get spare and location
                                spare = SpareMaster.objects.get(spare_id=spare_id)
                                location = LocationMaster.objects.get(location_id=location_id)
                                
                                # Check available stock
                                try:
                                    balance = StockBalance.objects.get(spare=spare, location=location)
                                    if balance.quantity < quantity:
                                        raise ValueError(f"Insufficient stock. Available: {balance.quantity}, Requested: {quantity}")
                                except StockBalance.DoesNotExist:
                                    raise ValueError(f"No stock available for {spare.spare_code} at {location.location_code}")
                                
                                # Get ticket if provided
                                ticket = None
                                if ticket_id:
                                    try:
                                        from ticketing.models import Ticket
                                        ticket = Ticket.objects.get(id=ticket_id)
                                    except Exception:
                                        pass  # Ticket not found, continue without it
                                
                                # Create issue
                                issue = StockIssue.objects.create(
                                    spare=spare,
                                    spare_code=spare.spare_code,
                                    location=location,
                                    location_code=location.location_code,
                                    quantity=quantity,
                                    issue_type=issue_type,
                                    ticket=ticket,
                                    issued_to=issued_to,
                                    remarks=remarks,
                                    issue_date=timezone.now(),
                                    performed_by=request.user,
                                )
                                
                                # Update stock balance
                                balance.quantity -= quantity
                                balance.save()
                                
                                # Create ledger entry
                                StockLedger.objects.create(
                                    spare=spare,
                                    spare_code=spare.spare_code,
                                    location_code=location.location_code,
                                    transaction_type='OUT',
                                    quantity=quantity,
                                    balance_after=balance.quantity,
                                    reference=str(issue.issue_id),
                                    remarks=remarks,
                                    performed_by=request.user,
                                )
                            success_count += 1
                except Exception as row_error:
                    error_count += 1
                    errors.append(f"Row {index + 2}: {str(row_error)}")
                    print(f"Error processing row {index + 2}: {str(row_error)}")
                    # Continue processing other rows instead of stopping
            
            # Log the upload
            print(f"Upload completed - Success: {success_count}, Errors: {error_count}")
            print(f"Errors list: {errors}")
            
            try:
                DataImportLog.objects.create(
                    file_name=csv_file.name,
                    data_type=f'site_onboarding_{table_name}',
                    records_imported=success_count,
                    records_skipped=error_count,
                    status='success' if error_count == 0 else 'partial',
                    imported_by=request.user,
                    file_size=csv_file.size,
                    error_message='; '.join(errors[:10]) if errors else None
                )
                print("DataImportLog created successfully")
            except Exception as log_error:
                print(f"Error creating DataImportLog: {str(log_error)}")
                # Don't fail the entire upload for logging errors
            
            # Determine response status and message based on results
            if success_count > 0:
                # At least some data was processed successfully
                response_status = 200
                if error_count == 0:
                    response_data = {
                        'success': True,
                        'message': f'✅ Successfully uploaded {success_count} {table_name.replace("_", " ").title()} records',
                        'statistics': {
                            'records_imported': int(success_count),
                            'records_skipped': int(error_count),
                            'total_rows_processed': int(len(df)),
                            'empty_rows_skipped': int(len(df) - success_count - error_count)
                        },
                        'validation_feedback': {
                            'warnings': validation_warnings[:5],  # Show first 5 warnings
                            'file_statistics': {
                                'total_rows': int(len(df)),
                                'total_columns': int(len(df.columns)),
                                'empty_rows': int(df.isnull().all(axis=1).sum()),
                                'missing_data_count': int(df.isnull().sum().sum())
                            }
                        }
                    }
                else:
                    # Some errors occurred but some data was still processed
                    response_data = {
                        'success': True,
                        'message': f'⚠️ Partially successful: {success_count} records imported, {error_count} failed',
                        'statistics': {
                            'records_imported': int(success_count),
                            'records_skipped': int(error_count),
                            'total_rows_processed': int(len(df)),
                            'empty_rows_skipped': int(len(df) - success_count - error_count)
                        },
                        'errors': errors[:10],  # Return first 10 errors
                        'validation_feedback': {
                            'warnings': validation_warnings[:5],
                            'file_statistics': {
                                'total_rows': int(len(df)),
                                'total_columns': int(len(df.columns)),
                                'empty_rows': int(df.isnull().all(axis=1).sum()),
                                'missing_data_count': int(df.isnull().sum().sum())
                            }
                        }
                    }
            else:
                # No data was processed successfully
                response_status = 400
                response_data = {
                    'success': False,
                    'error': f'❌ Failed to upload {table_name.replace("_", " ").title()} data',
                    'message': f'No records could be imported. {len(errors)} errors occurred.',
                    'statistics': {
                        'records_imported': int(success_count),
                        'records_skipped': int(error_count),
                        'total_rows_processed': int(len(df)),
                        'empty_rows_skipped': int(len(df) - success_count - error_count)
                    },
                    'errors': errors[:10],  # Return first 10 errors
                    'validation_feedback': {
                        'warnings': validation_warnings[:5],
                        'file_statistics': {
                            'total_rows': int(len(df)),
                            'total_columns': int(len(df.columns)),
                            'empty_rows': int(df.isnull().all(axis=1).sum()),
                            'missing_data_count': int(df.isnull().sum().sum())
                        }
                    }
                }
            
            # Add validation warnings if any
            if validation_warnings:
                if 'message' in response_data:
                    response_data['message'] += f' • {len(validation_warnings)} validation notes'
            
            # Ensure all values are JSON serializable
            def make_json_serializable(obj):
                """Recursively convert numpy/pandas types to native Python types"""
                if isinstance(obj, dict):
                    return {key: make_json_serializable(value) for key, value in obj.items()}
                elif isinstance(obj, list):
                    return [make_json_serializable(item) for item in obj]
                elif hasattr(obj, 'item'):  # numpy scalar
                    return obj.item()
                elif hasattr(obj, 'tolist'):  # numpy array
                    return obj.tolist()
                else:
                    return obj
            
            response_data = make_json_serializable(response_data)
            
            print(f"Returning response with status {response_status}: {response_data.get('message', 'No message')}")
            return JsonResponse(response_data, status=response_status)
            
        except Exception as parse_error:
            print(f"Exception in upload_site_onboarding_data: {str(parse_error)}")
            print(f"Exception type: {type(parse_error).__name__}")
            import traceback
            print(f"Traceback: {traceback.format_exc()}")
            return JsonResponse({
                'error': f'Error parsing CSV file: {str(parse_error)}'
            }, status=400)
            
    except Exception as e:
        print(f"Outer exception in upload_site_onboarding_data: {str(e)}")
        import traceback
        print(f"Outer traceback: {traceback.format_exc()}")
        return JsonResponse({'error': str(e)}, status=500)
    
    
