"""
Shared validation functions for CSV and data processing
"""

from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt
from accounts.decorators import role_required
from ...models import (
    DataImportLog, AssetList, device_list, device_mapping, budget_values, ic_budget, assets_contracts
)
import pandas as pd
import chardet
from .utilities import (
	ensure_unicode_string, detect_file_encoding
)

def validate_csv_structure(df, table_name):
    """
    Validate that CSV structure matches the expected table schema
    Returns (is_valid, error_message, missing_required_fields, extra_fields)
    """
    expected_schemas = {
        'asset_list': {
            'required_fields': ['asset_code', 'asset_name', 'country', 'portfolio', 'timezone'],
            'optional_fields': ['capacity', 'address', 'latitude', 'longitude', 
                              'contact_person', 'contact_method', 'grid_connection_date', 
                              'asset_number', 'customer_name', 'timezone', 'asset_name_oem', 'cod', 'operational_cod', 
                              'portfolio', 'y1_degradation', 'anual_degradation', 'api_name', 'api_key',
                              'tilt_configs', 'tilt_configs_json', 'altitude_m', 'albedo', 'pv_syst_pr',
                              'satellite_irradiance_source_asset_code'],
            'unique_identifier': 'asset_code'
        },
        'device_list': {
            'required_fields': ['device_id', 'device_name', 'device_type', 'country'],
            'optional_fields': ['device_code', 'device_type_id', 'device_serial', 
                              'device_model', 'device_make', 'latitude', 'longitude',
                              'optimizer_no', 'parent_code', 'software_version',
                              'string_no', 'connected_strings', 'device_sub_group', 
                              'dc_cap', 'device_source', 'ac_capacity',
                              'equipment_warranty_start_date', 'equipment_warranty_expire_date',
                              'epc_warranty_start_date', 'epc_warranty_expire_date',
                              'calibration_frequency', 'calibration_frequnecy',  # Handle typo in CSV
                              'pm_frequency', 'visual_inspection_frequency',
                              'bess_capacity', 'yom', 'nomenclature', 'location'],
            'unique_identifier': 'device_id'
        },
        'device_mapping': {
            'required_fields': ['asset_code', 'device_type', 'oem_tag'],
            'optional_fields': ['id', 'metric', 'discription', 'description', 
                              'data_type', 'units', 'fault_code', 'module_no', 
                              'default_value'],
            'unique_identifier': ['asset_code', 'oem_tag', 'metric', 'device_type']  # Composite key
        },
        'budget_values': {
            'required_fields': ['asset_code', 'month_str', 'bd_production', 'bd_ghi', 'bd_gti'],
            'optional_fields': ['id', 'asset_number', 'month_date'],
            'unique_identifier': ['asset_code', 'month_str']  # Composite key
        },
        'ic_budget': {
            'required_fields': ['asset_code', 'asset_number', 'month_str', 'month_date', 'ic_bd_production'],
            'optional_fields': ['id'],
            'unique_identifier': ['asset_code', 'month_str']  # Composite key
        },
        'asset_adapter_config': {
            'required_fields': ['asset_code', 'adapter_id'],
            'optional_fields': ['id', 'adapter_account_id', 'enabled', 'acquisition_interval_minutes',
                               'api_url', 'api_key', 'summarization', 'processing_keys',
                               'terrain_shading', 'time_stamp_type', 'tilt', 'azimuth', 'linked_asset_codes',
                               'solargis_region', 'daily_run_local_time', 'daily_run_timezone', 'asset_id'],
            'unique_identifier': 'asset_code'
        },
        'assets_contracts': {
            'required_fields': ['asset_number', 'asset_code'],
            # Keep this dynamic to avoid schema drift; allow any model field as optional.
            'optional_fields': [f.name for f in assets_contracts._meta.fields],
            'unique_identifier': 'asset_number'
        },
        'spare_master': {
            'required_fields': ['spare_code', 'spare_name', 'unit'],
            'optional_fields': ['spare_id', 'description', 'category', 'min_stock', 'max_stock', 'is_critical'],
            'unique_identifier': 'spare_code'
        },
        'location_master': {
            'required_fields': ['location_code', 'location_name'],
            'optional_fields': ['location_id', 'location_type'],
            'unique_identifier': 'location_code'
        },
        'spare_site_map': {
            'required_fields': ['spare_id', 'asset_code', 'location_id'],
            'optional_fields': ['map_id', 'is_active'],
            'unique_identifier': ['spare_id', 'asset_code', 'location_id']  # Composite key
        },
        'stock_entry': {
            'required_fields': ['spare_id', 'location_id', 'quantity', 'entry_type'],
            'optional_fields': ['entry_id', 'reference_number', 'remarks'],
            'unique_identifier': None  # No unique constraint, multiple entries allowed
        },
        'stock_issue': {
            'required_fields': ['spare_id', 'location_id', 'quantity', 'issue_type'],
            'optional_fields': ['issue_id', 'ticket_id', 'issued_to', 'remarks'],
            'unique_identifier': None  # No unique constraint, multiple issues allowed
        },
        'device_operating_state': {
            'required_fields': ['adapter_id', 'device_type', 'state_value', 'oem_state_label', 'internal_state'],
            'optional_fields': ['id', 'is_normal', 'fault_code', 'created_at', 'updated_at'],
            'unique_identifier': ['adapter_id', 'device_type', 'state_value']
        },
    }
    
    if table_name not in expected_schemas:
        return False, f"Unknown table: {table_name}", [], []
    
    schema = expected_schemas[table_name]
    csv_columns = set(df.columns.str.lower().str.strip())
    
    # Expected fields (case-insensitive)
    required_fields = set(field.lower() for field in schema['required_fields'])
    optional_fields = set(field.lower() for field in schema['optional_fields'])
    all_expected_fields = required_fields | optional_fields
    
    # Check for missing required fields
    missing_required = required_fields - csv_columns
    
    # Check for unexpected fields (not in schema)
    extra_fields = csv_columns - all_expected_fields
    
    # Validation results
    is_valid = True
    error_messages = []
    
    if missing_required:
        is_valid = False
        error_messages.append(f"Missing required fields: {', '.join(sorted(missing_required))}")
    
    # Allow some extra fields but warn about significant mismatches
    critical_mismatches = []
    for field in extra_fields:
        # Check if this looks like a field from a different table
        if table_name == 'asset_list':
            if any(device_field in field for device_field in ['device_', 'oem_', 'metric', 'fault_']):
                critical_mismatches.append(field)
        elif table_name == 'device_list':
            if any(asset_field in field for asset_field in ['portfolio', 'grid_connection']) or \
               any(mapping_field in field for mapping_field in ['oem_', 'metric', 'fault_']):
                critical_mismatches.append(field)
        elif table_name == 'device_mapping':
            if any(asset_field in field for asset_field in ['portfolio', 'grid_connection', 'address']) or \
               any(device_field in field for device_field in ['device_serial', 'device_model', 'optimizer_']) or \
               any(budget_field in field for budget_field in ['bd_', 'month_']):
                critical_mismatches.append(field)
        elif table_name == 'budget_values':
            if any(asset_field in field for asset_field in ['portfolio', 'grid_connection', 'address']) or \
               any(device_field in field for device_field in ['device_serial', 'device_model', 'optimizer_', 'oem_', 'metric']) or \
               not any(budget_field in field for budget_field in ['asset_code', 'month_str', 'bd_']):
                critical_mismatches.append(field)
        elif table_name == 'ic_budget':
            if any(asset_field in field for asset_field in ['portfolio', 'grid_connection', 'address']) or \
               any(device_field in field for device_field in ['device_serial', 'device_model', 'optimizer_', 'oem_', 'metric']) or \
               any(budget_field in field for budget_field in ['bd_ghi', 'bd_gti']) or \
               not any(ic_field in field for ic_field in ['asset_code', 'month_str', 'ic_bd_']):
                critical_mismatches.append(field)
        elif table_name in ['spare_master', 'location_master', 'spare_site_map', 'stock_entry', 'stock_issue']:
            # Spare management tables - check for fields from other modules
            if any(asset_field in field for asset_field in ['portfolio', 'grid_connection', 'address']) or \
               any(device_field in field for device_field in ['device_serial', 'device_model', 'optimizer_', 'oem_', 'metric']) or \
               any(budget_field in field for budget_field in ['bd_', 'month_', 'ic_bd_']):
                critical_mismatches.append(field)
    
    if critical_mismatches:
        is_valid = False
        error_messages.append(f"CSV appears to be for a different table. Suspicious fields: {', '.join(sorted(critical_mismatches))}")
    
    # Check data consistency for unique identifiers
    # Note: We're now more lenient - empty values in identifiers will generate warnings, not errors
    # Rows with empty identifiers will be skipped during import
    if not df.empty:
        if isinstance(schema['unique_identifier'], list):
            # Composite key - check for empty values but don't fail validation
            for key_field in schema['unique_identifier']:
                if key_field.lower() in csv_columns:
                    empty_count = df[key_field].isna().sum()
                    if empty_count > 0:
                        # Just log a warning, don't fail validation
                        print(f"Warning: Field '{key_field}' has {empty_count} empty values. These rows will be skipped during import.")
        else:
            # Single key
            key_field = schema['unique_identifier']
            if key_field.lower() in csv_columns:
                empty_count = df[key_field].isna().sum()
                if empty_count > 0:
                    # Just log a warning, don't fail validation
                    print(f"Warning: Field '{key_field}' has {empty_count} empty values. These rows will be skipped during import.")
                
                # Check for duplicates (still important)
                duplicates = df[df[key_field].duplicated()][key_field].tolist()
                if duplicates:
                    error_messages.append(f"Duplicate values in '{key_field}': {', '.join(map(str, duplicates[:5]))}")
                    is_valid = False
    
    error_message = '; '.join(error_messages) if error_messages else ''
    
    return is_valid, error_message, list(missing_required), list(extra_fields)

def validate_csv_requirements(df, data_type, file_name=''):
    """
    Validate basic CSV requirements and standards
    """
    requirements_result = {
        'valid': True,
        'error': None,
        'requirements_met': [],
        'requirements_failed': [],
        'suggestions': []
    }
    
    # Basic file requirements
    if df.empty:
        requirements_result.update({
            'valid': False,
            'error': 'CSV file is empty',
            'requirements_failed': ['File must contain data rows']
        })
        return requirements_result
    
    # Check file name conventions
    if file_name:
        expected_patterns = {
            'yield': ['yield', 'yield_data'],
            'bess': ['bess', 'battery'],
            'bess_v1': ['bessv1', 'bess_v1', 'bess-v1'],
            'aoc': ['aoc', 'areas_of_concern'],
            'ice': ['ice'],
            'map': ['map', 'mapping'],
            'minamata': ['minamata'],
            'icvsexvscur': ['icvsexvscur', 'ic_budget'],
            'loss_calculation': ['loss', 'loss_calculation']
        }
        
        if data_type in expected_patterns:
            file_lower = file_name.lower()
            if not any(pattern in file_lower for pattern in expected_patterns[data_type]):
                requirements_result['suggestions'].append(f'File name should contain one of: {", ".join(expected_patterns[data_type])}')
    
    # Check column count requirements
    min_columns = {
        'yield': 4,  # At least month, country, portfolio, assetno
        'bess': 5,   # At least date, month, country, portfolio, asset_no
        'bess_v1': 4,  # At least month, country, portfolio, asset_no
        'aoc': 5,    # At least s_no, month, asset_no, country, portfolio
        'ice': 2,    # At least month, portfolio
        'map': 4,    # At least asset_no, country, site_name, portfolio
        'minamata': 1,  # At least month
        'icvsexvscur': 3,  # At least country, portfolio, month
        'loss_calculation': 2  # At least month, asset_no
    }
    
    if data_type in min_columns:
        if len(df.columns) < min_columns[data_type]:
            requirements_result['requirements_failed'].append(f'Minimum {min_columns[data_type]} columns required for {data_type} data, found {len(df.columns)}')
        else:
            requirements_result['requirements_met'].append(f'Column count requirement met ({len(df.columns)} >= {min_columns[data_type]})')
    
    # Check for empty columns - only fail for required columns, warn for optional ones
    empty_columns = []
    empty_required_columns = []
    empty_optional_columns = []
    
    # Get required columns for this data type
    required_columns_for_type = {
        'asset_list': ['asset_code', 'asset_name', 'country', 'portfolio', 'timezone'],
        'device_list': ['device_id', 'device_name', 'device_type', 'country'],
        'device_mapping': ['asset_code', 'device_type', 'oem_tag'],  # metric is now optional
        'budget_values': ['asset_code', 'month_str', 'bd_production', 'bd_ghi', 'bd_gti'],
        'ic_budget': ['asset_code', 'asset_number', 'month_str', 'month_date', 'ic_bd_production'],
        'assets_contracts': ['asset_number', 'asset_code'],
        'bess_v1': ['month', 'country', 'portfolio', 'asset_no']
    }
    
    required_cols = set(required_columns_for_type.get(data_type, []))
    
    for col in df.columns:
        if df[col].isna().all():
            empty_columns.append(col)
            if col.lower() in [req.lower() for req in required_cols]:
                empty_required_columns.append(col)
            else:
                empty_optional_columns.append(col)
    
    # Only fail validation for empty required columns
    if empty_required_columns:
        requirements_result['requirements_failed'].append(f'Empty required columns found: {", ".join(empty_required_columns)}')
        requirements_result['suggestions'].append('Required columns must contain data')
    
    # Just warn about empty optional columns
    if empty_optional_columns:
        requirements_result['suggestions'].append(f'Empty optional columns will be ignored: {", ".join(empty_optional_columns[:5])}{"..." if len(empty_optional_columns) > 5 else ""}')
    
    if not empty_columns:
        requirements_result['requirements_met'].append('No completely empty columns found')
    elif not empty_required_columns:
        requirements_result['requirements_met'].append('All required columns contain data')
    
    # Check for duplicate column names
    duplicate_columns = []
    seen_columns = set()
    for col in df.columns:
        col_lower = col.lower().strip()
        if col_lower in seen_columns:
            duplicate_columns.append(col)
        seen_columns.add(col_lower)
    
    if duplicate_columns:
        requirements_result['requirements_failed'].append(f'Duplicate column names found: {", ".join(duplicate_columns)}')
        requirements_result['suggestions'].append('Ensure all column names are unique')
    else:
        requirements_result['requirements_met'].append('All column names are unique')
    
    # Check data quality
    # For daily data types (wide format), be more lenient with missing data checks
    # as many cells will naturally be empty (not all assets have data for all dates)
    daily_data_types = ['actual_generation_daily', 'expected_budget_daily', 'budget_gii_daily', 'actual_gii_daily', 'ic_approved_budget_daily']
    
    if data_type in daily_data_types:
        # For daily data, only check that:
        # 1. Date column (first column) has data
        # 2. At least some asset columns have data
        # 3. We don't count completely empty columns in the missing percentage
        
        # Remove completely empty columns from calculation
        non_empty_cols = [col for col in df.columns if not df[col].isna().all()]
        
        if len(non_empty_cols) < 2:  # Need at least date column + one asset column
            requirements_result['requirements_failed'].append('Daily CSV must have at least one date column and one asset column with data')
        else:
            # Calculate missing percentage only for non-empty columns
            if len(non_empty_cols) > 0:
                total_cells = len(df) * len(non_empty_cols)
                missing_cells = df[non_empty_cols].isna().sum().sum()
                missing_percentage = (missing_cells / total_cells) * 100 if total_cells > 0 else 0
                
                # For daily data, allow up to 80% missing (since many assets won't have data for all dates)
                if missing_percentage > 80:
                    requirements_result['requirements_failed'].append(f'Too much missing data: {missing_percentage:.1f}% of cells are empty in non-empty columns')
                    requirements_result['suggestions'].append('Ensure data completeness before uploading')
                elif missing_percentage > 60:
                    requirements_result['suggestions'].append(f'High amount of missing data: {missing_percentage:.1f}% of cells are empty')
                else:
                    requirements_result['requirements_met'].append(f'Acceptable data completeness: {100-missing_percentage:.1f}% of cells have data')
            
            # Warn about completely empty columns
            empty_cols = [col for col in df.columns if df[col].isna().all()]
            if empty_cols:
                requirements_result['suggestions'].append(f'Empty optional columns will be ignored: {", ".join(empty_cols[:5])}{"..." if len(empty_cols) > 5 else ""}')
    else:
        # For other data types, use the original strict validation
        total_cells = len(df) * len(df.columns)
        missing_cells = df.isna().sum().sum()
        missing_percentage = (missing_cells / total_cells) * 100 if total_cells > 0 else 0
        
        if missing_percentage > 50:
            requirements_result['requirements_failed'].append(f'Too much missing data: {missing_percentage:.1f}% of cells are empty')
            requirements_result['suggestions'].append('Ensure data completeness before uploading')
        elif missing_percentage > 20:
            requirements_result['suggestions'].append(f'High amount of missing data: {missing_percentage:.1f}% of cells are empty')
        else:
            requirements_result['requirements_met'].append(f'Acceptable data completeness: {100-missing_percentage:.1f}% of cells have data')
    
    # Data type specific requirements
    if data_type == 'yield':
        # Check for essential yield columns
        essential_yield_columns = ['month', 'country', 'portfolio', 'assetno']
        missing_essential = [col for col in essential_yield_columns if col not in [c.lower() for c in df.columns]]
        
        if missing_essential:
            requirements_result['requirements_failed'].append(f'Essential yield columns missing: {", ".join(missing_essential)}')
        else:
            requirements_result['requirements_met'].append('All essential yield columns present')
        
        # Check for common yield column naming issues
        problematic_names = []
        for col in df.columns:
            if ' ' in col and col.lower() not in ['string failure', 'inverter failure']:
                problematic_names.append(col)
            elif '$' in col and not col.endswith('_dollar'):
                problematic_names.append(col)
        
        if problematic_names:
            requirements_result['suggestions'].extend([
                f'Column "{name}" should use underscores instead of spaces' if ' ' in name else f'Column "{name}" should end with "_dollar" instead of "$"'
                for name in problematic_names[:3]
            ])
    
    # Final validation
    if requirements_result['requirements_failed']:
        requirements_result['valid'] = False
        requirements_result['error'] = f'{len(requirements_result["requirements_failed"])} requirement(s) failed'
    
    return requirements_result

def validate_budget_values_data(df):
    """
    Validate budget_values specific data requirements
    """
    errors = []
    warnings = []
    
    # Check required columns
    required_columns = ['asset_code', 'month_str']
    missing_columns = []
    for col in required_columns:
        if col not in df.columns:
            missing_columns.append(col)
    
    if missing_columns:
        errors.append(f"Missing required columns: {', '.join(missing_columns)}")
    
    # Check for valid month_str values
    if 'month_str' in df.columns:
        valid_months = ['JAN', 'FEB', 'MAR', 'APR', 'MAY', 'JUN', 
                       'JUL', 'AUG', 'SEP', 'OCT', 'NOV', 'DEC']
        invalid_months = df[~df['month_str'].isin(valid_months)]['month_str'].unique()
        if len(invalid_months) > 0:
            errors.append(f"Invalid month values found: {', '.join(map(str, invalid_months[:5]))}")
    
    # Check for duplicate asset_code + month_str combinations
    if 'asset_code' in df.columns and 'month_str' in df.columns:
        duplicates = df[df.duplicated(subset=['asset_code', 'month_str'], keep=False)]
        if len(duplicates) > 0:
            duplicate_count = len(duplicates)
            errors.append(f"Found {duplicate_count} duplicate asset_code + month_str combinations")
    
    # Check numeric columns
    numeric_columns = ['bd_production', 'bd_ghi', 'bd_gti']
    for col in numeric_columns:
        if col in df.columns:
            # Check for non-numeric values
            non_numeric = df[pd.to_numeric(df[col], errors='coerce').isna() & df[col].notna()]
            if len(non_numeric) > 0:
                warnings.append(f"Column '{col}' contains {len(non_numeric)} non-numeric values")
    
    # Check for empty asset_codes
    if 'asset_code' in df.columns:
        empty_assets = df[df['asset_code'].isna() | (df['asset_code'] == '')]
        if len(empty_assets) > 0:
            errors.append(f"Found {len(empty_assets)} rows with empty asset_code")
    
    return {
        'errors': errors,
        'warnings': warnings,
        'valid': len(errors) == 0
    }
    
def create_data_backup(table_name, user_id):
    """
    Create a backup of current data before upload operations
    """
    try:
        from datetime import datetime
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        if table_name == 'asset_list':
            assets = list(AssetList.objects.all().values())
            backup_data = {
                'table': 'asset_list',
                'timestamp': timestamp,
                'user_id': user_id,
                'record_count': len(assets),
                'data': assets
            }
        elif table_name == 'device_list':
            devices = list(device_list.objects.all().values())
            backup_data = {
                'table': 'device_list',
                'timestamp': timestamp,
                'user_id': user_id,
                'record_count': len(devices),
                'data': devices
            }
        elif table_name == 'device_mapping':
            mappings = list(device_mapping.objects.all().values())
            backup_data = {
                'table': 'device_mapping',
                'timestamp': timestamp,
                'user_id': user_id,
                'record_count': len(mappings),
                'data': mappings
            }
        elif table_name == 'budget_values':
            budgets = list(budget_values.objects.all().values())
            backup_data = {
                'table': 'budget_values',
                'timestamp': timestamp,
                'user_id': user_id,
                'record_count': len(budgets),
                'data': budgets
            }
        elif table_name == 'ic_budget':
            ic_budgets = list(ic_budget.objects.all().values())
            backup_data = {
                'table': 'ic_budget',
                'timestamp': timestamp,
                'user_id': user_id,
                'record_count': len(ic_budgets),
                'data': ic_budgets
            }
        elif table_name == 'assets_contracts':
            contracts = list(assets_contracts.objects.all().values())
            backup_data = {
                'table': 'assets_contracts',
                'timestamp': timestamp,
                'user_id': user_id,
                'record_count': len(contracts),
                'data': contracts
            }
        else:
            return None
        
        # Store backup as JSON file
        import json
        import os
        backup_dir = 'backups'
        if not os.path.exists(backup_dir):
            os.makedirs(backup_dir)
        
        backup_filename = f"{backup_dir}/backup_{table_name}_{timestamp}_user{user_id}.json"
        with open(backup_filename, 'w', encoding='utf-8') as f:
            json.dump(backup_data, f, indent=2, default=str, ensure_ascii=False)
        
        print(f"Backup created: {backup_filename}")
        return backup_filename
        
    except Exception as e:
        print(f"Failed to create backup: {str(e)}")
        return None
    
def parse_date_safely(date_value):
    """
    Parse date with multiple format attempts, prioritizing DD-MM-YYYY format
    """
    if pd.isna(date_value) or not date_value:
        return None
    
    date_str = str(date_value).strip()
    if not date_str:
        return None
    
    # Try different date formats in order of preference
    formats_to_try = [
        '%d-%m-%Y',    # DD-MM-YYYY (European format) - try first
        '%d/%m/%Y',    # DD/MM/YYYY 
        '%Y-%m-%d',    # YYYY-MM-DD (ISO format)
        '%m-%d-%Y',    # MM-DD-YYYY (US format)
        '%m/%d/%Y',    # MM/DD/YYYY (US format)
    ]
    
    for fmt in formats_to_try:
        try:
            return pd.to_datetime(date_str, format=fmt).date()
        except ValueError:
            continue
    
    # Last resort: try automatic parsing
    try:
        return pd.to_datetime(date_str).date()
    except ValueError:
        print(f"❌ Could not parse date: {date_str}")
        return None


# Month string to number mapping (case-insensitive)
MONTH_MAPPING = {
    'jan': 1, 'january': 1,
    'feb': 2, 'february': 2,
    'mar': 3, 'march': 3,
    'apr': 4, 'april': 4,
    'may': 5,
    'jun': 6, 'june': 6,
    'jul': 7, 'july': 7,
    'aug': 8, 'august': 8,
    'sep': 9, 'september': 9, 'sept': 9,
    'oct': 10, 'october': 10,
    'nov': 11, 'november': 11,
    'dec': 12, 'december': 12
}


def validate_ic_budget_dates_batch(df, auto_convert=False):
    """
    Comprehensive validation for IC budget dates by analyzing all 12 months for each asset/year.
    
    Groups rows by asset_code and year, then validates:
    1. Exactly 12 rows (one per month) for each asset/year
    2. Day is always 01 in DD-MM-YYYY format
    3. Months are 1-12 and match month_str column
    4. Detects if format is MM-DD-YYYY vs DD-MM-YYYY
    5. Cross-validates month_date with month_str
    
    If auto_convert=True and MM-DD-YYYY format is detected with high confidence,
    automatically converts dates to DD-MM-YYYY format.
    
    Returns:
        tuple: (errors: list, warnings: list, converted_df: DataFrame or None)
        If auto_convert=True and conversion successful, returns converted DataFrame
    """
    import re
    from collections import defaultdict
    
    errors = []
    warnings = []
    conversion_map = {}  # Map of (row_index, original_date) -> converted_date
    needs_conversion = False
    
    if df.empty:
        return errors, warnings, None
    
    # Step 1: Group rows by asset_code and year
    grouped_rows = defaultdict(list)
    
    for idx, row in df.iterrows():
        asset_code = str(row.get('asset_code', '')).strip()
        month_date_raw = row.get('month_date')
        month_str_raw = str(row.get('month_str', '')).strip()
        
        if pd.isna(month_date_raw) or not month_date_raw:
            errors.append({
                'type': 'missing_date',
                'row': idx + 2,  # +2 for header and 0-index
                'asset_code': asset_code,
                'message': f'Row {idx + 2}: month_date is missing or empty'
            })
            continue
        
        # Extract year from date (try both formats)
        year = None
        date_str = str(month_date_raw).strip()
        date_parts = re.split(r'[^\d]+', date_str)
        
        if len(date_parts) == 3:
            try:
                # Year is typically the last part (or first if YYYY-MM-DD)
                # Try last first (DD-MM-YYYY or MM-DD-YYYY)
                year = int(date_parts[2])
                # Validate year is reasonable (1900-2100)
                if year < 1900 or year > 2100:
                    errors.append({
                        'type': 'invalid_year',
                        'row': idx + 2,
                        'asset_code': asset_code,
                        'year': year,
                        'message': f'Row {idx + 2}: Invalid year {year}. Year must be between 1900 and 2100'
                    })
                    continue
            except (ValueError, IndexError):
                errors.append({
                    'type': 'invalid_date_format',
                    'row': idx + 2,
                    'asset_code': asset_code,
                    'date': month_date_raw,
                    'message': f'Row {idx + 2}: Date must have 3 numeric parts (day, month, year). Found: {date_str}'
                })
                continue
        else:
            errors.append({
                'type': 'invalid_date_format',
                'row': idx + 2,
                'asset_code': asset_code,
                'date': month_date_raw,
                'message': f'Row {idx + 2}: Date must have 3 parts. Found: {date_str}'
            })
            continue
        
        if asset_code and year:
            key = (asset_code, year)
            grouped_rows[key].append({
                'row_index': idx + 2,  # +2 for header and 0-index
                'asset_code': asset_code,
                'month_date_raw': month_date_raw,
                'month_str': month_str_raw,
                'date_parts': date_parts,
                'year': year
            })
    
    # Step 2: Validate each group
    for (asset_code, year), rows in grouped_rows.items():
        if len(rows) < 12:
            errors.append({
                'type': 'missing_months',
                'asset_code': asset_code,
                'year': year,
                'expected': 12,
                'found': len(rows),
                'message': f'Asset {asset_code} year {year}: Expected 12 months, found {len(rows)}'
            })
            # Continue validation even if not all months present
        elif len(rows) > 12:
            errors.append({
                'type': 'duplicate_months',
                'asset_code': asset_code,
                'year': year,
                'expected': 12,
                'found': len(rows),
                'message': f'Asset {asset_code} year {year}: Expected 12 months, found {len(rows)} (duplicate months detected)'
            })
        
        # Step 3: Extract and analyze dates
        month_positions = {'first': set(), 'second': set()}
        day_positions = {'first': set(), 'second': set()}
        month_str_to_number = {}
        
        # Map month strings to numbers (case-insensitive)
        for row in rows:
            month_str = row['month_str'].upper().strip()
            month_num = MONTH_MAPPING.get(month_str.lower())
            if month_num:
                month_str_to_number[month_str] = month_num
            elif month_str:
                errors.append({
                    'type': 'invalid_month_str',
                    'row': row['row_index'],
                    'asset_code': asset_code,
                    'month_str': month_str,
                    'message': f'Row {row["row_index"]}: Invalid month string "{month_str}". Expected: JAN, FEB, MAR, APR, MAY, JUN, JUL, AUG, SEP, OCT, NOV, DEC (case-insensitive)'
                })
        
        # Step 4: Analyze date format for each row
        for row in rows:
            date_parts = row['date_parts']
            if len(date_parts) != 3:
                continue
            
            try:
                first = int(date_parts[0])
                second = int(date_parts[1])
                year_val = int(date_parts[2])
                
                # Check which position has day=01
                if first == 1:
                    day_positions['first'].add(row['month_str'])
                if second == 1:
                    day_positions['second'].add(row['month_str'])
                
                # Check which position has months 1-12
                if 1 <= first <= 12:
                    month_positions['first'].add(first)
                if 1 <= second <= 12:
                    month_positions['second'].add(second)
                    
            except (ValueError, IndexError):
                continue
        
        # Step 5: Detect format
        # If months 1-12 appear in first position → MM-DD-YYYY (WRONG)
        # If months 1-12 appear in second position → DD-MM-YYYY (CORRECT)
        
        first_has_all_months = len(month_positions['first']) >= 11  # Allow for 1 missing
        second_has_all_months = len(month_positions['second']) >= 11
        
        detected_format = None
        
        if first_has_all_months and not second_has_all_months:
            # Months 1-12 in first position → MM-DD-YYYY format (WRONG)
            detected_format = 'mm-dd-yyyy'
            
            # Check if we can confidently convert (all day=01 in second position, months match month_str)
            can_convert = True
            conversion_errors = []
            
            for row in rows:
                date_parts = row['date_parts']
                if len(date_parts) != 3:
                    can_convert = False
                    break
                
                try:
                    first = int(date_parts[0])  # Month in MM-DD-YYYY
                    second = int(date_parts[1])  # Day in MM-DD-YYYY
                    month_str = row['month_str'].upper().strip()
                    expected_month_num = MONTH_MAPPING.get(month_str.lower())
                    
                    # Check day=01
                    if second != 1:
                        can_convert = False
                        conversion_errors.append(f'Row {row["row_index"]}: Day is {second}, not 01')
                        break
                    
                    # Check month matches month_str
                    if expected_month_num and first != expected_month_num:
                        can_convert = False
                        conversion_errors.append(f'Row {row["row_index"]}: Month {first} doesn\'t match month_str {month_str} (expected {expected_month_num})')
                        break
                        
                except (ValueError, IndexError):
                    can_convert = False
                    break
            
            if auto_convert and can_convert and len(rows) == 12:
                # Confident conversion - convert all dates for this asset/year
                needs_conversion = True
                for row in rows:
                    date_parts = row['date_parts']
                    if len(date_parts) == 3:
                        try:
                            month = int(date_parts[0])  # Month in MM-DD-YYYY
                            day = int(date_parts[1])     # Day (should be 01)
                            year_val = int(date_parts[2])
                            
                            # Convert MM-DD-YYYY to DD-MM-YYYY
                            # Extract separator from original date
                            original_date = str(row['month_date_raw']).strip()
                            separator = '-'
                            if '/' in original_date:
                                separator = '/'
                            elif '.' in original_date:
                                separator = '.'
                            
                            # Create converted date: DD-MM-YYYY
                            converted_date = f'01{separator}{month:02d}{separator}{year_val}'
                            conversion_map[(row['row_index'], original_date)] = converted_date
                            
                        except (ValueError, IndexError):
                            pass
                
                warnings.append({
                    'type': 'auto_converted',
                    'asset_code': asset_code,
                    'year': year,
                    'message': f'Asset {asset_code} year {year}: Automatically converted {len(rows)} dates from MM-DD-YYYY to DD-MM-YYYY format'
                })
            else:
                # Cannot auto-convert - report error
                error_rows = [r['row_index'] for r in rows]
                error_msg = f'Asset {asset_code} year {year}: Dates appear to be in MM-DD-YYYY format. Expected DD-MM-YYYY format with day=01 (e.g., 01-01-{year}, 01-02-{year}, ..., 01-12-{year})'
                if conversion_errors:
                    error_msg += f'. Conversion issues: {"; ".join(conversion_errors[:3])}'
                errors.append({
                    'type': 'format_detected_mm_dd_yyyy',
                    'asset_code': asset_code,
                    'year': year,
                    'message': error_msg,
                    'rows': error_rows[:5],  # Show first 5 rows
                    'total_rows': len(error_rows)
                })
        elif second_has_all_months and not first_has_all_months:
            # Months 1-12 in second position → DD-MM-YYYY format (CORRECT)
            detected_format = 'dd-mm-yyyy'
        elif first_has_all_months and second_has_all_months:
            # Ambiguous - both positions have months 1-12
            detected_format = 'ambiguous'
            error_rows = [r['row_index'] for r in rows]
            errors.append({
                'type': 'ambiguous_format',
                'asset_code': asset_code,
                'year': year,
                'message': f'Asset {asset_code} year {year}: Date format is ambiguous. Both positions contain months 1-12. Expected DD-MM-YYYY format with day=01.',
                'rows': error_rows[:5],
                'total_rows': len(error_rows)
            })
        else:
            detected_format = 'unknown'
        
        # Step 6: Validate day=01 for all rows
        for row in rows:
            date_parts = row['date_parts']
            if len(date_parts) != 3:
                continue
            
            try:
                first = int(date_parts[0])
                second = int(date_parts[1])
                
                if detected_format == 'dd-mm-yyyy':
                    # First position should be day=01
                    if first != 1:
                        errors.append({
                            'type': 'day_not_01',
                            'row': row['row_index'],
                            'asset_code': asset_code,
                            'day': first,
                            'date': row['month_date_raw'],
                            'message': f'Row {row["row_index"]}: Day must be 01 for monthly values. Found day={first} in date "{row["month_date_raw"]}". Expected: 01-{second:02d}-{year}'
                        })
                elif detected_format == 'mm-dd-yyyy':
                    # Second position should be day=01
                    if second != 1:
                        errors.append({
                            'type': 'day_not_01',
                            'row': row['row_index'],
                            'asset_code': asset_code,
                            'day': second,
                            'date': row['month_date_raw'],
                            'message': f'Row {row["row_index"]}: Day must be 01 for monthly values. Found day={second} in date "{row["month_date_raw"]}". Expected format: DD-MM-YYYY with day=01'
                        })
                elif detected_format == 'ambiguous':
                    # Check both positions
                    if first != 1 and second != 1:
                        errors.append({
                            'type': 'day_not_01',
                            'row': row['row_index'],
                            'asset_code': asset_code,
                            'date': row['month_date_raw'],
                            'message': f'Row {row["row_index"]}: Day must be 01 for monthly values. Found day={first} or {second} in date "{row["month_date_raw"]}". Expected: 01-MM-YYYY format'
                        })
                    
            except (ValueError, IndexError):
                continue
        
        # Step 7: Cross-validate month_date with month_str
        for row in rows:
            date_parts = row['date_parts']
            if len(date_parts) != 3:
                continue
            
            try:
                first = int(date_parts[0])
                second = int(date_parts[1])
                month_str = row['month_str'].upper().strip()
                expected_month_num = MONTH_MAPPING.get(month_str.lower())
                
                if expected_month_num is None:
                    # Already reported in step 3
                    continue
                
                # Determine actual month based on detected format
                actual_month = None
                if detected_format == 'dd-mm-yyyy':
                    # Second position is month
                    actual_month = second
                elif detected_format == 'mm-dd-yyyy':
                    # First position is month
                    actual_month = first
                elif detected_format == 'ambiguous':
                    # Try to match with month_str
                    if first == expected_month_num:
                        actual_month = first
                    elif second == expected_month_num:
                        actual_month = second
                    else:
                        # Neither matches, report error
                        errors.append({
                            'type': 'month_mismatch',
                            'row': row['row_index'],
                            'asset_code': asset_code,
                            'month_str': month_str,
                            'expected_month': expected_month_num,
                            'date': row['month_date_raw'],
                            'message': f'Row {row["row_index"]}: Month mismatch. month_str="{month_str}" (month {expected_month_num}) but date "{row["month_date_raw"]}" does not contain month {expected_month_num}'
                        })
                        continue
                else:
                    # Unknown format, try both
                    if first == expected_month_num:
                        actual_month = first
                    elif second == expected_month_num:
                        actual_month = second
                
                if actual_month is not None and actual_month != expected_month_num:
                    errors.append({
                        'type': 'month_mismatch',
                        'row': row['row_index'],
                        'asset_code': asset_code,
                        'month_str': month_str,
                        'expected_month': expected_month_num,
                        'actual_month': actual_month,
                        'date': row['month_date_raw'],
                        'message': f'Row {row["row_index"]}: Month mismatch. month_str="{month_str}" (month {expected_month_num}) but date "{row["month_date_raw"]}" shows month {actual_month}'
                    })
                    
            except (ValueError, IndexError):
                continue
    
    # If conversion was performed, create converted DataFrame
    converted_df = None
    if needs_conversion and conversion_map:
        converted_df = df.copy()
        for idx, row in converted_df.iterrows():
            original_date = str(row.get('month_date', '')).strip()
            row_idx = idx + 2  # +2 for header and 0-index
            key = (row_idx, original_date)
            if key in conversion_map:
                converted_df.at[idx, 'month_date'] = conversion_map[key]
                print(f"Converted row {row_idx}: {original_date} -> {conversion_map[key]}")
    
    return errors, warnings, converted_df

def try_read_csv_with_encoding(file_obj, encoding, delimiter=','):
    """
    Try to read CSV with specific encoding and delimiter
    """
    try:
        file_obj.seek(0)  # Reset file pointer
        df = pd.read_csv(file_obj, encoding=encoding, sep=delimiter)
        return {'success': True, 'df': df, 'encoding': encoding, 'delimiter': delimiter}
    except UnicodeDecodeError as e:
        return {'success': False, 'error': f'UnicodeDecodeError with {encoding}: {str(e)}', 'encoding': encoding}
    except Exception as e:
        return {'success': False, 'error': f'Error with {encoding}: {str(e)}', 'encoding': encoding}
    
def clean_file_content(file_obj):
    """
    Clean problematic characters from file content
    """
    try:
        file_obj.seek(0)
        content = file_obj.read()
        
        # Replace problematic characters
        replacements = {
            b'\x92': b"'",  # Smart single quote
            b'\x93': b'"',  # Smart double quote (left)
            b'\x94': b'"',  # Smart double quote (right)
            b'\x96': b'-',  # En dash
            b'\x97': b'--', # Em dash
            b'\x85': b'...', # Horizontal ellipsis
            b'\x91': b"'",  # Left single quotation mark
            b'\x99': b'(TM)', # Trade mark sign
            b'\x80': b'EUR', # Euro sign
            b'\x82': b',',   # Low-9 quotation mark
            b'\x84': b'"',   # Low double prime quotation mark
            b'\x86': b'+',   # Single low-9 quotation mark
            b'\x87': b'<<',  # Double low-9 quotation mark
            b'\x88': b'^',   # Caron
            b'\x89': b'0/00', # Per mille sign
            b'\x8A': b'S',   # Latin capital letter S with caron
            b'\x8B': b'<',   # Single left-pointing angle quotation mark
            b'\x8C': b'OE',  # Latin capital ligature OE
            b'\x8D': b'',    # Latin small letter z with caron
            b'\x8E': b'Z',   # Latin capital letter Z with caron
            b'\x8F': b'',    # Latin small letter z with caron
        }
        
        for old_char, new_char in replacements.items():
            content = content.replace(old_char, new_char)
        
        # Create a new file-like object with cleaned content
        from io import BytesIO
        cleaned_file = BytesIO(content)
        cleaned_file.name = getattr(file_obj, 'name', 'cleaned_file.csv')
        
        return cleaned_file
        
    except Exception as e:
        print(f"Error cleaning file content: {e}")
        return file_obj
    
def try_decode_with_errors(file_obj, encoding):
    """
    Try to decode file content with error handling
    """
    try:
        file_obj.seek(0)
        content = file_obj.read()
        
        # Try to decode with error handling
        decoded_content = content.decode(encoding, errors='replace')
        
        # Create a new file-like object with decoded content
        from io import StringIO
        decoded_file = StringIO(decoded_content)
        decoded_file.name = getattr(file_obj, 'name', 'decoded_file.csv')
        
        return decoded_file
        
    except Exception as e:
        print(f"Error decoding with {encoding}: {e}")
        return None

def analyze_file_encoding(file_obj):
    """
    Analyze file encoding and provide specific guidance
    """
    try:
        # Read first few bytes to analyze
        sample = file_obj.read(1000)
        file_obj.seek(0)
        
        # Check for BOM (Byte Order Mark)
        if sample.startswith(b'\xef\xbb\xbf'):
            return "File has UTF-8 BOM. This should work with UTF-8 encoding."
        elif sample.startswith(b'\xff\xfe'):
            return "File has UTF-16 LE BOM. Try saving as UTF-8."
        elif sample.startswith(b'\xfe\xff'):
            return "File has UTF-16 BE BOM. Try saving as UTF-8."
        
        # Check for common problematic characters
        problematic_chars = [b'\x92', b'\x93', b'\x94', b'\x96', b'\x97']  # Smart quotes, em-dash, etc.
        found_chars = []
        for char in problematic_chars:
            if char in sample:
                found_chars.append(char.hex())
        
        if found_chars:
            return f"File contains problematic characters: {found_chars}. These are likely smart quotes or special characters from Word/Excel. Please save the file as UTF-8."
        
        # Try to detect encoding
        result = chardet.detect(sample)
        if result['encoding'] and result['confidence'] > 0.5:
            return f"Detected encoding: {result['encoding']} (confidence: {result['confidence']:.2f})"
        else:
            return "Could not reliably detect encoding. Try opening in a text editor and saving as UTF-8."
            
    except Exception as e:
        return f"Error analyzing file: {str(e)}"
    
    
def validate_csv_data(df, data_type):
    """
    Validate CSV data based on data type with comprehensive error reporting
    """
    try:
        validation_result = {
            'valid': True,
            'error': None,
            'warnings': [],
            'column_issues': [],
            'data_issues': [],
            'statistics': {
                'total_rows': len(df),
                'total_columns': len(df.columns),
                'empty_rows': 0,
                'missing_data_count': 0
            }
        }
        
        # Check for empty data
        if df.empty:
            validation_result.update({
                'valid': False,
                'error': 'CSV file is empty or contains no data rows'
            })
            return validation_result
        
        # Count empty rows and missing data
        empty_rows = df.isnull().all(axis=1).sum()
        missing_data_count = df.isnull().sum().sum()
        validation_result['statistics']['empty_rows'] = int(empty_rows)
        validation_result['statistics']['missing_data_count'] = int(missing_data_count)
        
        # For daily CSV files, skip generic column validation as they have special wide format
        if data_type not in ['actual_generation_daily', 'expected_budget_daily', 'budget_gii_daily', 'actual_gii_daily', 'ic_approved_budget_daily']:
            required_columns = get_required_columns(data_type)
            missing_columns = [col for col in required_columns if col not in df.columns]
            
            if missing_columns:
                validation_result.update({
                    'valid': False,
                    'error': f'Missing required columns: {", ".join(missing_columns)}',
                    'column_issues': [f'Required column "{col}" not found in CSV' for col in missing_columns]
                })
                return validation_result
            
            # Check for column mapping issues for all data types
            column_validation = validate_data_type_columns(df, data_type)
            validation_result['column_issues'].extend(column_validation['issues'])
            validation_result['warnings'].extend(column_validation['warnings'])
            
            # If there are critical column mapping issues, fail validation
            if column_validation['issues']:
                critical_issues = [issue for issue in column_validation['issues'] if 'Important column' in issue or 'does not match' in issue]
                if critical_issues:
                    validation_result.update({
                        'valid': False,
                        'error': f'Column mapping issues found: {len(critical_issues)} critical issues'
                    })
                    return validation_result
        
        # Content validation for all data types
        content_validation = validate_data_content(df, data_type)
        validation_result['warnings'].extend(content_validation['warnings'])
        validation_result['data_issues'].extend(content_validation['issues'])
        
        if content_validation['critical_issues']:
            validation_result.update({
                'valid': False,
                'error': 'Critical data validation issues found',
                'data_issues': content_validation['critical_issues']
            })
            return validation_result
        
        elif data_type in ['actual_generation_daily', 'expected_budget_daily', 'budget_gii_daily', 'actual_gii_daily', 'ic_approved_budget_daily']:
            # Validate daily data (wide format: first column should be date, others should be asset codes)
            if len(df.columns) < 2:
                return {'valid': False, 'error': 'Daily CSV files must have at least 2 columns: Date and asset columns'}
            
            # Check if first column contains dates
            date_col = df.columns[0]
            try:
                # Try to parse a few sample dates
                sample_dates = df[date_col].dropna().head(3)
                for date_val in sample_dates:
                    date_str = str(date_val)
                    if ' ' in date_str:
                        date_str = date_str.split(' ')[0]
                    
                    # Try common date formats
                    parsed = False
                    for fmt in ['%m/%d/%Y', '%Y-%m-%d', '%d/%m/%Y']:
                        try:
                            pd.to_datetime(date_str, format=fmt)
                            parsed = True
                            break
                        except:
                            continue
                    
                    if not parsed:
                        try:
                            pd.to_datetime(date_str)
                            parsed = True
                        except:
                            pass
                    
                    if not parsed:
                        return {'valid': False, 'error': f'Invalid date format in first column: "{date_val}". Expected formats: MM/DD/YYYY, YYYY-MM-DD, or DD/MM/YYYY'}
            except Exception as e:
                return {'valid': False, 'error': f'Error validating date column: {str(e)}'}
        
        elif data_type == 'icvsexvscur':
            # Validate ICVSEXVSCUR data - check that month values are parsable dates
            # We now accept:
            # - Historic formats like "25-Apr" or "Jan-25"
            # - Standard date formats like "1/1/2026", "2026-01-01", etc.
            if 'month' in df.columns:
                sample_months = df['month'].dropna().head(5)
                for month_val in sample_months:
                    try:
                        # First try flexible pandas parsing (handles strings, timestamps, datetimes)
                        pd.to_datetime(month_val)
                    except Exception:
                        # As a fallback, allow the historic "25-Apr" / "Jan-25" style
                        month_str = str(month_val)
                        if '-' in month_str:
                            parts = month_str.split('-')
                            if len(parts) == 2:
                                part1, part2 = parts[0].strip(), parts[1].strip()
                                valid_months = ['jan', 'feb', 'mar', 'apr', 'may', 'jun',
                                                'jul', 'aug', 'sep', 'oct', 'nov', 'dec']
                                
                                if (part1.isdigit() and len(part1) == 2 and part2.lower() in valid_months) or \
                                   (part1.lower() in valid_months and part2.isdigit() and len(part2) == 2):
                                    # Accept classic formats as well
                                    continue
                        # If neither generic parsing nor classic formats work, fail validation
                        return {
                            'valid': False,
                            'error': (
                                f'Invalid month value "{month_val}". Expected something like '
                                '"25-Apr", "Jan-25", or a standard date such as "1/1/2026" or "2026-01-01".'
                            )
                        }
        
        return {'valid': True, 'error': None}
        
    except Exception as e:
        return {'valid': False, 'error': f'Validation error: {str(e)}'}

def validate_data_type_columns(df, data_type):
    """
    Validate columns for any data type and check for mapping issues
    """
    issues = []
    warnings = []
    
    # Get model class and fields for the data type
    model_mapping = {
        'yield': 'YieldData',
        'bess': 'BESSData',
        'aoc': 'AOCData',
        'ice': 'ICEData',
        'icvsexvscur': 'ICVSEXVSCURData',
        'map': 'MapData',
        'minamata': 'MinamataStringLossData',
        'loss_calculation': 'LossCalculationData',
        'actual_generation_daily': 'ActualGenerationDailyData',
        'expected_budget_daily': 'ExpectedBudgetDailyData',
        'budget_gii_daily': 'BudgetGIIDailyData',
        'actual_gii_daily': 'ActualGIIDailyData',
        'ic_approved_budget_daily': 'ICApprovedBudgetDailyData'
    }
    
    if data_type not in model_mapping:
        issues.append(f'Unknown data type: {data_type}')
        return {'issues': issues, 'warnings': warnings, 'mapped_columns': [], 'unmapped_columns': []}
    
    # Import the model dynamically
    from ... import models
    model_class = getattr(models, model_mapping[data_type])
    model_fields = [field.name for field in model_class._meta.fields]
    
    # Check original column names before normalization
    original_columns = df.columns.tolist()
    
    # Apply normalization to see what we get
    normalized_columns = []
    for col in original_columns:
        normalized_col = col.strip().lower().replace(' ', '_').replace('(', '').replace(')', '').replace('/', '_').replace('-', '_')
        
        # Special handling for dollar sign
        if normalized_col.endswith('_$'):
            normalized_col = normalized_col.replace('_$', '_dollar')
        else:
            normalized_col = normalized_col.replace('$', '_dollar')
        
        # Clean up any double underscores
        while '__' in normalized_col:
            normalized_col = normalized_col.replace('__', '_')
        
        # Special handling for Loss Calculation columns
        if data_type == 'loss_calculation':
            # Fix common column mapping issues
            if normalized_col == 's_no':
                normalized_col = 'l'  # Map S No to l (Loss ID)
            elif normalized_col == 'start_dae':
                normalized_col = 'start_date'  # Fix typo in "Start Dae"
            elif normalized_col == 'subcatergory':
                normalized_col = 'subcategory'  # Fix typo in "Subcatergory"
            elif normalized_col == 'budget_pr_%':
                normalized_col = 'budget_pr_percent'  # Fix percentage column
            elif normalized_col == 'ppa_rate_in_usd':
                normalized_col = 'ppa_rate_usd'  # Fix PPA rate column
            elif normalized_col == 'revenue_loss_in_usd':
                normalized_col = 'revenue_loss_usd'  # Fix revenue loss column
            
        normalized_columns.append(normalized_col)
    
    # Check which columns will be mapped successfully
    mapped_columns = []
    unmapped_columns = []
    
    for i, (orig_col, norm_col) in enumerate(zip(original_columns, normalized_columns)):
        if norm_col in model_fields:
            mapped_columns.append((orig_col, norm_col))
        else:
            unmapped_columns.append((orig_col, norm_col))
    
    # Report unmapped columns as warnings or issues
    for orig_col, norm_col in unmapped_columns:
        if orig_col.lower() in ['id', 'created_at', 'updated_at']:
            # These are auto-generated fields, it's okay to skip them
            warnings.append(f'Column "{orig_col}" will be ignored (auto-generated field)')
        else:
            issues.append(f'Column "{orig_col}" → "{norm_col}" does not match any model field')
    
    # Check for important missing columns based on data type
    important_columns = get_important_columns(data_type)
    missing_important = []
    
    for imp_col in important_columns:
        if imp_col not in normalized_columns:
            missing_important.append(imp_col)
    
    if missing_important:
        issues.extend([f'Important column "{col}" is missing' for col in missing_important])
    
    # Success message for mapped columns
    if mapped_columns:
        warnings.append(f'{len(mapped_columns)} columns will be successfully mapped to database fields')
    
    return {
        'issues': issues,
        'warnings': warnings,
        'mapped_columns': mapped_columns,
        'unmapped_columns': unmapped_columns
    }
    
    
    
def get_important_columns(data_type):
    """
    Get important columns for each data type
    """
    important_columns_mapping = {
        'yield': ['month', 'country', 'portfolio', 'assetno'],
        'bess': ['date', 'month', 'country', 'portfolio', 'asset_no'],
        'aoc': ['s_no', 'month', 'asset_no', 'country', 'portfolio'],
        'ice': ['month', 'portfolio'],
        'icvsexvscur': ['country', 'portfolio', 'month'],
        'map': ['asset_no', 'country', 'site_name', 'portfolio'],
        'minamata': ['month'],
        'loss_calculation': ['month', 'asset_no'],
        'actual_generation_daily': ['date'],
        'expected_budget_daily': ['date'],
        'budget_gii_daily': ['date'],
        'actual_gii_daily': ['date'],
        'ic_approved_budget_daily': ['date']
    }
    
    return important_columns_mapping.get(data_type, [])


def validate_data_content(df, data_type):
    """
    Validate the content of any data type for common issues
    """
    warnings = []
    issues = []
    critical_issues = []
    
    # Get essential columns for this data type
    essential_columns = get_important_columns(data_type)
    
    # Check for completely empty essential columns
    for col in essential_columns:
        if col in df.columns:
            empty_count = df[col].isna().sum()
            if empty_count == len(df):
                critical_issues.append(f'Essential column "{col}" is completely empty')
            elif empty_count > len(df) * 0.5:  # More than 50% empty
                warnings.append(f'Column "{col}" has {empty_count} empty values ({empty_count/len(df)*100:.1f}%)')
    
    # Data type specific validations
    if data_type == 'yield':
        # Check for reasonable data ranges
        if 'actual_generation' in df.columns:
            actual_gen = pd.to_numeric(df['actual_generation'], errors='coerce')
            negative_count = (actual_gen < 0).sum()
            if negative_count > 0:
                warnings.append(f'{negative_count} records have negative actual generation values')
            
            extremely_high = (actual_gen > 10000).sum()  # Assuming values > 10000 MWh are suspicious
            if extremely_high > 0:
                warnings.append(f'{extremely_high} records have extremely high actual generation values (>10000)')
        
        # Check month format
        if 'month' in df.columns:
            invalid_months = []
            for idx, month_val in df['month'].head(10).items():
                if pd.isna(month_val):
                    continue
                month_str = str(month_val)
                # Check if it looks like a proper date format
                if not any(char in month_str for char in ['-', '/', ' ']):
                    invalid_months.append(month_str)
            
            if invalid_months:
                issues.extend([f'Invalid month format: "{month}"' for month in invalid_months[:5]])
    
    elif data_type == 'bess':
        # Check for reasonable BESS data ranges
        if 'discharge_energy_kwh' in df.columns:
            discharge = pd.to_numeric(df['discharge_energy_kwh'], errors='coerce')
            negative_count = (discharge < 0).sum()
            if negative_count > 0:
                warnings.append(f'{negative_count} records have negative discharge energy values')
        
        if 'battery_capacity_mw' in df.columns:
            capacity = pd.to_numeric(df['battery_capacity_mw'], errors='coerce')
            zero_capacity = (capacity == 0).sum()
            if zero_capacity > len(df) * 0.5:
                warnings.append(f'{zero_capacity} records have zero battery capacity')
        
        if 'rte' in df.columns:
            rte = pd.to_numeric(df['rte'], errors='coerce')
            invalid_rte = ((rte < 0) | (rte > 1)).sum()
            if invalid_rte > 0:
                issues.append(f'{invalid_rte} records have invalid RTE values (should be between 0 and 1)')
    
    elif data_type == 'aoc':
        # Check for AOC specific issues - AOC data mainly contains text remarks
        if 'remarks' in df.columns:
            empty_remarks = df['remarks'].isna().sum()
            if empty_remarks > len(df) * 0.8:
                warnings.append(f'{empty_remarks} records have empty remarks (most AOC records should have descriptions)')
    
    elif data_type == 'map':
        # Check for map data issues
        if 'latitude' in df.columns:
            lat = pd.to_numeric(df['latitude'], errors='coerce')
            invalid_lat = ((lat < -90) | (lat > 90)).sum()
            if invalid_lat > 0:
                issues.append(f'{invalid_lat} records have invalid latitude values (must be between -90 and 90)')
        
        if 'longitude' in df.columns:
            lon = pd.to_numeric(df['longitude'], errors='coerce')
            invalid_lon = ((lon < -180) | (lon > 180)).sum()
            if invalid_lon > 0:
                issues.append(f'{invalid_lon} records have invalid longitude values (must be between -180 and 180)')
    
    elif data_type in ['actual_generation_daily', 'expected_budget_daily', 'budget_gii_daily', 'actual_gii_daily', 'ic_approved_budget_daily']:
        # Check for daily data issues
        if len(df.columns) < 2:
            critical_issues.append('Daily CSV files must have at least 2 columns: Date and asset columns')
        
        # Check if first column contains dates
        if len(df.columns) > 0:
            date_col = df.columns[0]
            try:
                sample_dates = df[date_col].dropna().head(5)
                invalid_dates = 0
                for date_val in sample_dates:
                    try:
                        pd.to_datetime(date_val)
                    except:
                        invalid_dates += 1
                
                if invalid_dates > 0:
                    issues.append(f'{invalid_dates} invalid date values found in first column')
            except Exception as e:
                issues.append(f'Error validating date column: {str(e)}')
    
    return {
        'warnings': warnings,
        'issues': issues,
        'critical_issues': critical_issues
    }
    
    
def get_required_columns(data_type):
    """
    Get required columns for each data type
    """
    column_mapping = {
        'yield': ['month', 'country', 'portfolio', 'assetno'],
        'bess': ['date', 'month', 'country', 'portfolio', 'asset_no'],
        'aoc': ['s_no', 'month', 'asset_no', 'country', 'portfolio'],
        'ice': ['month', 'portfolio'],
        'icvsexvscur': ['country', 'portfolio', 'month'],
        'map': ['asset_no', 'country', 'site_name', 'portfolio'],
        'minamata': ['month'],
        'loss_calculation': ['month', 'asset_no'],
        # Daily CSV files are in wide format - only require first column to be date-like
        'actual_generation_daily': [],  # Wide format: Date + asset columns
        'expected_budget_daily': [],    # Wide format: Date + asset columns
        'budget_gii_daily': [],         # Wide format: Date + asset columns
        'actual_gii_daily': [],         # Wide format: Date + asset columns
        'ic_approved_budget_daily': []  # Wide format: Date + asset columns
    }
    
    return column_mapping.get(data_type, [])