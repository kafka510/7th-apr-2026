from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt, ensure_csrf_cookie
from django.views.decorators.http import require_http_methods
from django.contrib.auth.models import User
from django.contrib.auth.tokens import default_token_generator
from django.utils.http import urlsafe_base64_encode
from django.utils.encoding import force_bytes
from django.core.mail import send_mail
from django.urls import reverse
from django.contrib import messages
from django.db import transaction, models
from django.conf import settings
import math
import json

from accounts.decorators import role_required, feature_required
import logging
from functools import wraps

# Security decorator for superuser-only operations
def superuser_required(view_func):
    """Decorator to ensure only superusers can access a view"""
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if not request.user.is_superuser:
            logger = logging.getLogger(__name__)
            logger.warning(f"Unauthorized superuser operation attempt by user {request.user.username} (ID: {request.user.id}) on {view_func.__name__}")
            return JsonResponse({'error': 'Only superusers can perform this operation'}, status=403)
        return view_func(request, *args, **kwargs)
    return _wrapped_view

from .models import (
    YieldData, BESSData, AOCData, ICEData, FeedbackImage, ICVSEXVSCURData, MapData, 
    MinamataStringLossData, DataImportLog, AssetList, device_list, device_mapping, budget_values, timeseries_data, UserProfile,
    ActualGenerationDailyData, ExpectedBudgetDailyData, BudgetGIIDailyData, ActualGIIDailyData,
    ICApprovedBudgetDailyData, LossCalculationData, RealTimeKPI, Feedback, ic_budget
)
from .forms import FeedbackForm

import csv, json, os, pandas as pd, io, math, pytz, chardet
from datetime import datetime, timezone, timedelta
from django.http import HttpResponse
from django.core.paginator import Paginator

def validate_csv_structure(df, table_name):
    """
    Validate that CSV structure matches the expected table schema
    Returns (is_valid, error_message, missing_required_fields, extra_fields)
    """
    expected_schemas = {
        'asset_list': {
            'required_fields': ['asset_code', 'asset_name', 'country', 'portfolio'],
            'optional_fields': ['capacity', 'address', 'latitude', 'longitude', 
                              'contact_person', 'contact_method', 'grid_connection_date', 
                              'asset_number', 'timezone', 'asset_name_oem', 'cod', 'operational_cod', 
                              'portfolio', 'y1_degradation', 'anual_degradation', 'api_name', 'api_key'],
            'unique_identifier': 'asset_code'
        },
        'device_list': {
            'required_fields': ['device_id', 'device_name', 'device_type', 'country'],
            'optional_fields': ['device_code', 'device_type_id', 'device_serial', 
                              'device_model', 'device_make', 'latitude', 'longitude',
                              'optimizer_no', 'parent_code', 'software_version',
                              'string_no', 'connected_strings', 'device_sub_group', 
                              'device_source'],
            'unique_identifier': 'device_id'
        },
        'device_mapping': {
            'required_fields': ['asset_code', 'device_type', 'metric', 'oem_tag'],
            'optional_fields': ['id', 'discription', 'description', 
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
        }
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
    
    if critical_mismatches:
        is_valid = False
        error_messages.append(f"CSV appears to be for a different table. Suspicious fields: {', '.join(sorted(critical_mismatches))}")
    
    # Check data consistency for unique identifiers
    if is_valid and not df.empty:
        if isinstance(schema['unique_identifier'], list):
            # Composite key
            for key_field in schema['unique_identifier']:
                if key_field.lower() in csv_columns:
                    if df[key_field].isna().any():
                        error_messages.append(f"Unique identifier '{key_field}' contains empty values")
                        is_valid = False
        else:
            # Single key
            key_field = schema['unique_identifier']
            if key_field.lower() in csv_columns:
                if df[key_field].isna().any():
                    error_messages.append(f"Unique identifier '{key_field}' contains empty values")
                    is_valid = False
                
                # Check for duplicates
                duplicates = df[df[key_field].duplicated()][key_field].tolist()
                if duplicates:
                    error_messages.append(f"Duplicate values in '{key_field}': {', '.join(map(str, duplicates[:5]))}")
                    is_valid = False
    
    error_message = '; '.join(error_messages) if error_messages else ''
    
    return is_valid, error_message, list(missing_required), list(extra_fields)

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

def ensure_unicode_string(value):
    """
    Ensure a value is properly encoded as Unicode string with enhanced debugging
    """
    if value is None:
        return ''
    if pd.isna(value):
        return ''
    
    # Convert to string and ensure proper Unicode handling
    str_value = str(value).strip()
    
        
    
    # If it's already a proper Unicode string, return it
    if isinstance(str_value, str):
        # Ensure it doesn't contain replacement characters (indicating previous corruption)
        if '\ufffd' in str_value or '?' in str_value:
            print(f"Warning - Found replacement characters in: {repr(str_value)}")
        return str_value
    
    # Handle bytes objects
    if isinstance(str_value, bytes):
        encodings_to_try = ['utf-8', 'shift_jis', 'cp932', 'euc-jp', 'iso-2022-jp']
        for encoding in encodings_to_try:
            try:
                decoded = str_value.decode(encoding)
                
                return decoded
            except UnicodeDecodeError:
                continue
        
        # Last resort - use latin1 with replacement
        result = str_value.decode('latin1', errors='replace')
        print(f"Warning - Used latin1 fallback for: {repr(result)}")
        return result
    
    return str_value

def detect_file_encoding(file_obj):
    """
    Detect the encoding of a file using chardet library with improved Japanese support
    """
    try:
        # Read a larger sample of the file to detect encoding
        sample = file_obj.read(50000)  # Read first 50KB for better detection
        file_obj.seek(0)  # Reset file pointer
        
        # Detect encoding
        result = chardet.detect(sample)
        detected_encoding = result['encoding']
        confidence = result['confidence']
        
        print(f"Detected encoding: {detected_encoding} (confidence: {confidence})")
        
        # Special handling for Japanese encodings
        if detected_encoding:
            # Normalize encoding names
            detected_encoding = detected_encoding.lower()
            
            # Map common Japanese encoding aliases
            japanese_encoding_map = {
                'shift_jis': 'shift_jis',
                'shift-jis': 'shift_jis',
                'sjis': 'shift_jis',
                'shiftjis': 'shift_jis',
                'euc-jp': 'euc-jp',
                'eucjp': 'euc-jp',
                'iso-2022-jp': 'iso-2022-jp',
                'jis': 'iso-2022-jp',
                'cp932': 'cp932',
                'windows-31j': 'cp932'
            }
            
            # Check if it's a known Japanese encoding
            for alias, canonical in japanese_encoding_map.items():
                if alias in detected_encoding:
                    print(f"Japanese encoding detected: {canonical}")
                    return canonical
        
        # Return detected encoding if confidence is reasonable
        if detected_encoding and confidence > 0.3:  # Lower threshold for better detection
            return detected_encoding
        
        # Fallback to UTF-8 (most common for modern files)
        return 'utf-8'
    except Exception as e:
        print(f"Error detecting encoding: {e}")
        return 'utf-8'

def try_read_csv_with_encoding(file_obj, encoding):
    """
    Try to read CSV with specific encoding and return detailed error info
    """
    try:
        file_obj.seek(0)  # Reset file pointer
        df = pd.read_csv(file_obj, encoding=encoding)
        return {'success': True, 'df': df, 'encoding': encoding}
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

"""

# Create your views here.
def read_csv_data():
    csv_path = os.path.join(settings.BASE_DIR, 'data', 'yield.csv')
    data = []
    
    # Try different encodings
    encodings_to_try = ['utf-8', 'latin-1', 'cp1252', 'iso-8859-1', 'windows-1252']
    
    for encoding in encodings_to_try:
        try:
            with open(csv_path, newline='', encoding=encoding) as f:
                reader = csv.DictReader(f)
                for row in reader:
                    cleaned = {}
                    for key, val in row.items():
                        norm_key = key.strip().lower()
                        val = val.strip() if isinstance(val, str) else val
                        cleaned[norm_key] = val
                        if norm_key in ['country', 'portfolio', 'assetno']:
                            cleaned[norm_key + '_norm'] = str(val).strip().lower()
                    if 'assetno' in cleaned:
                        cleaned['assetno'] = str(cleaned['assetno']).strip()
                    data.append(cleaned)
                    #print(cleaned)
            print(f"Successfully read CSV with encoding: {encoding}")
            return data
        except UnicodeDecodeError:
            print(f"Failed to read with encoding: {encoding}")
            continue
        except Exception as e:
            print(f"Error reading with encoding {encoding}: {e}")
            continue
    
    print("Could not read CSV file with any supported encoding")
    return []

def home_view(request):
    
    return render(request, 'main/home.html')


@login_required
def dashboard_view(request):
    all_data = read_csv_data()
    #print(all_data)
    # Optional: If you want to debug it
    all_data = json.dumps(all_data)
    return render(request, 'main/UNIFIED_OPERATIONS_DASHBOARD.html', {'all_data': all_data})
"""


def dt_to_utc(ts, tz):   
    #print(ts, type(ts), str(ts))
    try:
        dt = datetime.strptime(ts, '%Y-%m-%d %H:%M:%S%z')
    except ValueError:
        try:
            dt = datetime.strptime(ts, '%Y-%m-%d %H:%M:%S.%f%z')
        except ValueError:
            dt = datetime.strptime(ts, '%Y-%m-%dT%H:%M')

    dt_utc = dt.astimezone(pytz.utc)
    offset_str = tz

    # Convert offset string to a timedelta object
    sign = 1 if offset_str[0] == '+' else -1
    hours, minutes = map(int, offset_str[1:].split(':'))
    offset_timedelta = timedelta(hours=hours * sign, minutes=minutes * sign)

    # Create a datetime.timezone object
    offset_timezone = timezone(offset_timedelta)
    dt_tar = dt_utc.astimezone((offset_timezone)) 
    return(dt_tar)



def get_user_accessible_sites(request):
    """
    Get the list of asset codes that the user has access to.
    Implements hierarchical access control:
    1. If user has specific sites assigned, return only those sites
    2. If user has portfolios assigned, return all sites in those portfolios
    3. If user has countries assigned, return all sites in those countries
    4. If user is admin, return all sites
    """
    try:
        user_profile = UserProfile.objects.get(user=request.user)
        
        
        # Admin users get access to all sites
        if user_profile.role == 'admin':
            sites = AssetList.objects.all()
            
            return sites
        
        # Use the UserProfile's get_accessible_sites method for consistency
        accessible_sites = user_profile.get_accessible_sites()
        
        return accessible_sites
        
    except UserProfile.DoesNotExist:
        print(f"get_user_accessible_sites: No UserProfile found for user {request.user.username}")
        return AssetList.objects.none()

def get_user_accessible_asset_numbers(request):
    """
    Get the list of asset_number values that the user has access to.
    This is a helper function for views that need asset_number values.
    """
    accessible_sites = get_user_accessible_sites(request)
    if accessible_sites.exists():
        return accessible_sites.values_list('asset_number', flat=True)
    return []

def get_user_accessible_sites_debug(request):
    """
    Debug version to see what's happening with user access
    """
    try:
        user_profile = UserProfile.objects.get(user=request.user)
        
        
        if user_profile.role == 'admin':
            sites = AssetList.objects.values_list('asset_number', flat=True)
          
            return sites
        
        # Use the hierarchical access control logic from the UserProfile model
        accessible_sites = user_profile.get_accessible_sites()
        site_numbers = accessible_sites.values_list('asset_number', flat=True)
       
        return site_numbers
        
    except UserProfile.DoesNotExist:
     
        return []

def filter_data_by_user_sites(queryset, asset_field_name, request):
    """
    Filter queryset based on user's accessible sites.
    asset_field_name: The field name in the model that contains the asset code
    """
    accessible_sites = get_user_accessible_sites(request)
    
    
    if accessible_sites and accessible_sites.exists():
        # Extract asset_number values from AssetList objects
        asset_numbers = list(accessible_sites.values_list('asset_number', flat=True))
        
        
        # Also get asset_code values for debugging
        asset_codes = list(accessible_sites.values_list('asset_code', flat=True))
        
        
        # Filter by accessible sites using asset_number values
        filter_kwargs = {f"{asset_field_name}__in": asset_numbers}
        
        filtered_queryset = queryset.filter(**filter_kwargs)
        
        
        # If no results with asset_number, try with asset_code
        if filtered_queryset.count() == 0 and asset_codes:
            
            filter_kwargs_code = {f"{asset_field_name}__in": asset_codes}
            
            filtered_queryset = queryset.filter(**filter_kwargs_code)
            
        
        return filtered_queryset
    else:
        # If no sites assigned, return empty queryset
        print(f"filter_data_by_user_sites: No accessible sites, returning empty queryset")
        return queryset.none()



@ensure_csrf_cookie
def home_view(request):
    """
    Default landing page that redirects users based on authentication status:
    - Logged in users -> Unified Operations Dashboard  
    - Non-logged in users -> Login page
    """
    # Ensure session is saved
    if request.user.is_authenticated:
        # Force session save to ensure CSRF token is properly set
        request.session.save()
        return redirect('main:unified_operations_dashboard')
    else:
        return redirect('accounts:login')

@ensure_csrf_cookie
def csrf_test_view(request):
    """Simple view to test CSRF token functionality"""
    if request.method == 'POST':
        return JsonResponse({'status': 'success', 'message': 'CSRF token is working!'})
    return render(request, 'main/csrf_test.html')

def simple_csrf_test_view(request):
    """Simple view without decorators to test CSRF"""
    if request.method == 'POST':
        return JsonResponse({'status': 'success', 'message': 'Simple CSRF test working!'})
    return render(request, 'main/simple_csrf_test.html')

#@role_required(allowed_roles=['admin','om','customer','management'])
@feature_required('unified_operations_dashboard')
@login_required
@ensure_csrf_cookie
def dashboard_view(request):
    return render(request, 'main/UNIFIED_OPERATIONS_DASHBOARD.html')

#@role_required(allowed_roles=['admin','om','customer','management'])
@feature_required('unified_operations_dashboard')
@login_required
@ensure_csrf_cookie
def unified_operations_dashboard_view(request):
    from django.utils import timezone
    return render(request, 'main/UNIFIED_OPERATIONS_DASHBOARD.html', {
        'timestamp': int(timezone.now().timestamp())
    })

@feature_required('portfolio_map')
@login_required
def portfolio_map_view(request):
    """Portfolio map view with data passed directly to template"""
    try:
        # Use the filter_data_by_user_sites function for proper access control
        map_data_queryset = filter_data_by_user_sites(MapData.objects.all(), 'asset_no', request)
        yield_data_queryset = filter_data_by_user_sites(YieldData.objects.all(), 'assetno', request)
       
        
       
        map_data = []
        for record in map_data_queryset:
            def safe_val(val):
                return "" if val is None or (isinstance(val, float) and math.isnan(val)) else val
            map_data.append({
                'id': record.id,
                'asset_no': safe_val(record.asset_no),
                'country': safe_val(record.country),
                'site_name': safe_val(record.site_name),
                'portfolio': safe_val(record.portfolio),
                'installation_type': safe_val(record.installation_type),
                'dc_capacity_mwp': safe_val(record.dc_capacity_mwp),
                'pcs_capacity': safe_val(record.pcs_capacity),
                'battery_capacity_mw': safe_val(record.battery_capacity_mw),
                'plant_type': safe_val(record.plant_type),
                'offtaker': safe_val(record.offtaker),
                'cod': safe_val(record.cod),
                'latitude': safe_val(record.latitude),
                'longitude': safe_val(record.longitude),
                'created_at': record.created_at.isoformat() if record.created_at else None,
                'updated_at': record.updated_at.isoformat() if record.updated_at else None,
            })
       
        # Process yield data for performance calculations
        yield_data = []
        for record in yield_data_queryset:
            def safe_val(val):
                return "" if val is None or (isinstance(val, float) and math.isnan(val)) else val
            yield_data.append({
                'month': safe_val(record.month),
                'country': safe_val(record.country),
                'portfolio': safe_val(record.portfolio),
                'assetno': safe_val(record.assetno),
                'dc_capacity_mw': safe_val(record.dc_capacity_mw),
                'ic_approved_budget': safe_val(record.ic_approved_budget),
                'expected_budget': safe_val(record.expected_budget),
                'actual_generation': safe_val(record.actual_generation),
                'created_at': record.created_at.isoformat() if record.created_at else "",
                'updated_at': record.updated_at.isoformat() if record.updated_at else "",
            })
       
        return render(request, 'main/map portfolio_v2.html', {
            'map_data_json': json.dumps(map_data),
            'yield_data_json': json.dumps(yield_data)
        })
    except Exception as e:
        return render(request, 'main/map portfolio_v2.html', {
            'map_data_json': json.dumps([]),
            'yield_data_json': json.dumps([]),
            'error_message': str(e)
        })
        
        
@feature_required('yield_report')
@login_required
def yield_report_view(request):
    """Yield report view with data passed directly to template"""
    try:
        # Use the filter_data_by_user_sites function for proper access control
        data = filter_data_by_user_sites(YieldData.objects.all(), 'assetno', request)
        
        # Debug: Calculate database sums
        total_ic_approved_budget = sum(record.ic_approved_budget or 0 for record in data if record.ic_approved_budget is not None and not math.isnan(record.ic_approved_budget))
        total_expected_budget = sum(record.expected_budget or 0 for record in data if record.expected_budget is not None and not math.isnan(record.expected_budget))
        total_actual_generation = sum(record.actual_generation or 0 for record in data if record.actual_generation is not None and not math.isnan(record.actual_generation))
        
                
        yield_data = []
        for record in data:
            def safe_val(val):
                return "" if val is None or (isinstance(val, float) and math.isnan(val)) else val
            yield_data.append({
                'month': safe_val(record.month),
                'country': safe_val(record.country),
                'portfolio': safe_val(record.portfolio),
                'assetno': safe_val(record.assetno),
                'dc_capacity_mw': safe_val(record.dc_capacity_mw),
                'ic_approved_budget': safe_val(record.ic_approved_budget),
                'expected_budget': safe_val(record.expected_budget),
                'weather_loss_or_gain': safe_val(record.weather_loss_or_gain),
                'grid_curtailment': safe_val(record.grid_curtailment),
                'grid_outage': safe_val(record.grid_outage),
                'operation_budget': safe_val(record.operation_budget),
                'breakdown_loss': safe_val(record.breakdown_loss),
                'unclassified_loss': safe_val(record.unclassified_loss),
                'actual_generation': safe_val(record.actual_generation),
                'string failure': safe_val(record.string_failure),
                'inverter failure': safe_val(record.inverter_failure),
                'ac_failure': safe_val(record.ac_failure),
                'expected_pr': safe_val(record.expected_pr),
                'actual_pr': safe_val(record.actual_pr),
                'pr_gap': safe_val(record.pr_gap),
                'pr_gap_observation': safe_val(record.pr_gap_observation),
                'pr_gap_action_need_to_taken': safe_val(record.pr_gap_action_need_to_taken),
                'revenue_loss': safe_val(record.revenue_loss),
                'revenue_loss_observation': safe_val(record.revenue_loss_observation),
                'revenue_loss_action_need_to_taken': safe_val(record.revenue_loss_action_need_to_taken),
                'actual_irradiation': safe_val(record.actual_irradiation),
                'ac_capacity_mw': safe_val(record.ac_capacity_mw),
                'bess_capacity_mwh': safe_val(record.bess_capacity_mwh),
                'bess_generation_mwh': safe_val(record.bess_generation_mwh),
                # Add the new dollar fields
                'ppa_rate': safe_val(record.ppa_rate),
                'ic_approved_budget_dollar': safe_val(record.ic_approved_budget_dollar),
                'expected_budget_dollar': safe_val(record.expected_budget_dollar),
                'actual_generation_dollar': safe_val(record.actual_generation_dollar),
                'created_at': record.created_at.isoformat() if record.created_at else "",
                'updated_at': record.updated_at.isoformat() if record.updated_at else "",
                'remarks': '',
            })
        
        return render(request, 'main/Yield Report_v2.html', {
            'yield_data_json': json.dumps(yield_data)
        })
    except Exception as e:
        return render(request, 'main/Yield Report_v2.html', {
            'yield_data_json': json.dumps([]),
            'error_message': str(e)
        })

@login_required
def yield_report_edited_view(request):
    return render(request, 'main/Yield Report_v1_edited.html')

@feature_required('pr_gap')
@login_required
def pr_gap_view(request):
    """PR Gap view - data is loaded via API endpoints"""
    return render(request, 'main/PR_Gap.html')

@feature_required('revenue_loss')
@login_required
def revenue_loss_view(request):
    """Revenue loss view with data passed directly to template"""
    try:
        # Use the filter_data_by_user_sites function for proper access control
        data = filter_data_by_user_sites(YieldData.objects.all(), 'assetno', request)
        
        
        yield_data = []
        for record in data:
            def safe_val(val):
                return "" if val is None or (isinstance(val, float) and math.isnan(val)) else val
            yield_data.append({
                'month': safe_val(record.month),
                'country': safe_val(record.country),
                'portfolio': safe_val(record.portfolio),
                'assetno': safe_val(record.assetno),
                'dc_capacity_mw': safe_val(record.dc_capacity_mw),
                'ic_approved_budget': safe_val(record.ic_approved_budget),
                'expected_budget': safe_val(record.expected_budget),
                'weather_loss_or_gain': safe_val(record.weather_loss_or_gain),
                'grid_curtailment': safe_val(record.grid_curtailment),
                'grid_outage': safe_val(record.grid_outage),
                'operation_budget': safe_val(record.operation_budget),
                'breakdown_loss': safe_val(record.breakdown_loss),
                'unclassified_loss': safe_val(record.unclassified_loss),
                'actual_generation': safe_val(record.actual_generation),
                'string failure': safe_val(record.string_failure),
                'inverter failure': safe_val(record.inverter_failure),
                'ac_failure': safe_val(record.ac_failure),
                'expected_pr': safe_val(record.expected_pr),
                'actual_pr': safe_val(record.actual_pr),
                'pr_gap': safe_val(record.pr_gap),
                'pr_gap_observation': safe_val(record.pr_gap_observation),
                'pr_gap_action_need_to_taken': safe_val(record.pr_gap_action_need_to_taken),
                'revenue_loss': safe_val(record.revenue_loss),
                'revenue_loss_observation': safe_val(record.revenue_loss_observation),
                'revenue_loss_action_need_to_taken': safe_val(record.revenue_loss_action_need_to_taken),
                'actual_irradiation': safe_val(record.actual_irradiation),
                'ac_capacity_mw': safe_val(record.ac_capacity_mw),
                'bess_capacity_mwh': safe_val(record.bess_capacity_mwh),
                'bess_generation_mwh': safe_val(record.bess_generation_mwh),
                # Add the new dollar fields
                'ppa_rate': safe_val(record.ppa_rate),
                'ic_approved_budget_dollar': safe_val(record.ic_approved_budget_dollar),
                'expected_budget_dollar': safe_val(record.expected_budget_dollar),
                'actual_generation_dollar': safe_val(record.actual_generation_dollar),
                'created_at': record.created_at.isoformat() if record.created_at else "",
                'updated_at': record.updated_at.isoformat() if record.updated_at else "",
                'remarks': '',
            })
        
        
        
        return render(request, 'main/revenue_loss.html', {
            'yield_data_json': json.dumps(yield_data)
        })
    except Exception as e:
        print(f"DEBUG: Revenue Loss - Error: {str(e)}")
        return render(request, 'main/revenue_loss.html', {
            'yield_data_json': json.dumps([]),
            'error_message': str(e)
        })

@feature_required('areas_of_concern')
@login_required
def areas_of_concern_view(request):
    """Areas of concern view with data passed directly to template"""
    try:
        # Debug: Check total AOC data available
        total_aoc_data = AOCData.objects.count()
        
        
        # Debug: Check what asset numbers are in AOCData
        aoc_asset_numbers = AOCData.objects.values_list('asset_no', flat=True).distinct()
        
        
        # Debug: Check user accessible sites
        accessible_sites = get_user_accessible_sites(request)
        
        if accessible_sites and accessible_sites.exists():
            accessible_asset_numbers = list(accessible_sites.values_list('asset_number', flat=True))
            
        # Use the filter_data_by_user_sites function for proper access control
        data = filter_data_by_user_sites(AOCData.objects.all(), 'asset_no', request)
        
        
        aoc_data = []
        for record in data:
            def safe_val(val):
                return "" if val is None or (isinstance(val, float) and math.isnan(val)) else val
            aoc_data.append({
                'id': record.id,
                's_no': safe_val(record.s_no),
                'month': safe_val(record.month),
                'asset_no': safe_val(record.asset_no),
                'country': safe_val(record.country),
                'portfolio': safe_val(record.portfolio),
                'remarks': safe_val(record.remarks),
                'created_at': record.created_at.isoformat() if record.created_at else None,
                'updated_at': record.updated_at.isoformat() if record.updated_at else None,
            })
        
        
        
        # Check if the JSON is being created correctly
        json_data = json.dumps(aoc_data)
        
        
        return render(request, 'main/AOC.html', {
            'aoc_data_json': json_data
        })
    except Exception as e:
        print(f"DEBUG: AOC - Error: {str(e)}")
        return render(request, 'main/AOC.html', {
            'aoc_data_json': json.dumps([]),
            'error_message': str(e)
        })

@feature_required('bess_performance')
@login_required
def bess_performance_view(request):
    """BESS performance view with data passed directly to template"""
    try:
        # Check if user is admin
        try:
            user_profile = UserProfile.objects.get(user=request.user)
            is_admin = user_profile.role == 'admin'
            
        except UserProfile.DoesNotExist:
            is_admin = False
            
        
        if is_admin:
            # For admin users, show all BESS data (including records without energy data)
            data = BESSData.objects.all()
            
        else:
            # For non-admin users, filter by accessible sites
            accessible_asset_numbers = get_user_accessible_asset_numbers(request)
            
            
            if accessible_asset_numbers:
                # Filter by accessible sites - BESSData uses asset_no, AssetList uses asset_number
                # Include all records, even those without energy data
                data = BESSData.objects.filter(
                    asset_no__in=accessible_asset_numbers
                )
                
            else:
                # If no sites assigned, return empty queryset
                data = BESSData.objects.none()
                
        
        # Debug: Check total BESS data available
        total_bess_data = BESSData.objects.count()
        
        
        # Debug: Check what asset numbers are in BESSData
        bess_asset_numbers = BESSData.objects.values_list('asset_no', flat=True).distinct()
        
        
        # Debug: Check what asset numbers are in AssetList
        asset_list_numbers = AssetList.objects.values_list('asset_number', flat=True).distinct()
        
        
        bess_data = []
        for record in data:
            def safe_val(val):
                if val is None:
                    return None
                elif isinstance(val, float) and math.isnan(val):
                    return None
                else:
                    return val  # Return the original value
            
                        
            bess_data.append({
                'id': record.id,
                'asset_no': safe_val(record.asset_no),
                'date': safe_val(record.date),
                'month': safe_val(record.month),
                'country': safe_val(record.country),
                'portfolio': safe_val(record.portfolio),
                'battery_capacity_mw': safe_val(record.battery_capacity_mw),
                'export_energy_kwh': safe_val(record.export_energy_kwh),
                'pv_energy_kwh': safe_val(record.pv_energy_kwh),
                'charge_energy_kwh': safe_val(record.charge_energy_kwh),
                'discharge_energy_kwh': safe_val(record.discharge_energy_kwh),
                'min_soc': safe_val(record.min_soc),
                'max_soc': safe_val(record.max_soc),
                'min_ess_temperature': safe_val(record.min_ess_temperature),
                'max_ess_temperature': safe_val(record.max_ess_temperature),
                'min_ess_humidity': safe_val(record.min_ess_humidity),
                'max_ess_humidity': safe_val(record.max_ess_humidity),
                'rte': safe_val(record.rte),
                'created_at': record.created_at.isoformat() if record.created_at else None,
                'updated_at': record.updated_at.isoformat() if record.updated_at else None,
            })
        
        return render(request, 'main/bess_v2.html', {
            'bess_data_json': json.dumps(bess_data)
        })
    except Exception as e:
        print(f"BESS API Error: {str(e)}")
        return render(request, 'main/bess_v2.html', {
            'bess_data_json': json.dumps([]),
            'error_message': str(e)
        })

@feature_required('minamata_typhoon_damage')
@login_required
def minamata_typhoon_damage_view(request):
    """Minamata typhoon damage view with data passed directly to template"""
    try:
        # MinamataStringLossData doesn't have asset_no field, so return all data for now
        # TODO: Add asset_no field to MinamataStringLossData model if needed for filtering
        data = MinamataStringLossData.objects.all()
        
        minamata_data = []
        for record in data:
            def safe_val(val):
                return "" if val is None or (isinstance(val, float) and math.isnan(val)) else val
            minamata_data.append({
                'id': record.id,
                'month': safe_val(record.month),
                'no_of_strings_breakdown': safe_val(record.no_of_strings_breakdown),
                'no_of_strings_modules_damaged': safe_val(record.no_of_strings_modules_damaged),
                'designed_dc_capacity_mwh': safe_val(record.designed_dc_capacity_mwh),
                'breakdown_dc_capacity_mwh': safe_val(record.breakdown_dc_capacity_mwh),
                'operational_dc_capacity_mwh': safe_val(record.operational_dc_capacity_mwh),
                'budgeted_gen_mwh': safe_val(record.budgeted_gen_mwh),
                'actual_gen_mwh': safe_val(record.actual_gen_mwh),
                'loss_due_to_string_failure_mwh': safe_val(record.loss_due_to_string_failure_mwh),
                'loss_in_jpy': safe_val(record.loss_in_jpy),
                'loss_in_usd': safe_val(record.loss_in_usd),
                'created_at': record.created_at.isoformat() if record.created_at else None,
                'updated_at': record.updated_at.isoformat() if record.updated_at else None,
            })
        
        return render(request, 'main/Minamata_string_loss.html', {
            'minamata_data_json': json.dumps(minamata_data)
        })
    except Exception as e:
        return render(request, 'main/Minamata_string_loss.html', {
            'minamata_data_json': json.dumps([]),
            'error_message': str(e)
        })

@feature_required('ic_budget_vs_expected')
@login_required
def ic_budget_vs_expected_view(request):
    """IC Budget vs Expected view with data passed directly to template"""
    try:
        # Get user accessible sites
        accessible_sites = get_user_accessible_sites(request)
        
        if accessible_sites:
            # Filter by accessible sites - ICVSEXVSCURData uses portfolio, we'll filter by portfolio
            # Get portfolios from accessible sites
            accessible_portfolios = []
            for site in accessible_sites:
                try:
                    asset = AssetList.objects.get(asset_number=site)
                    accessible_portfolios.append(asset.portfolio)
                except AssetList.DoesNotExist:
                    continue
            
            if accessible_portfolios:
                icvsexvscur_data = ICVSEXVSCURData.objects.filter(portfolio__in=accessible_portfolios)
            else:
                icvsexvscur_data = ICVSEXVSCURData.objects.all()
        else:
            # If no sites assigned, return all data
            icvsexvscur_data = ICVSEXVSCURData.objects.all()
        
        icvsexvscur_data_list = []
        for record in icvsexvscur_data:
            def safe_val(val):
                return "" if val is None or (isinstance(val, float) and math.isnan(val)) else val
            icvsexvscur_data_list.append({
                'id': record.id,
                'country': safe_val(record.country),
                'portfolio': safe_val(record.portfolio),
                'dc_capacity_mwp': safe_val(record.dc_capacity_mwp),
                'month': record.month.strftime('%b %Y') if record.month else "",  # Format as "Apr 2025"
                'month_sort': record.month.isoformat() if record.month else "",  # For sorting purposes
                'ic_approved_budget_mwh': safe_val(record.ic_approved_budget_mwh),
                'expected_budget_mwh': safe_val(record.expected_budget_mwh),
                'actual_generation_mwh': safe_val(record.actual_generation_mwh),
                'grid_curtailment_budget_mwh': safe_val(record.grid_curtailment_budget_mwh),
                'actual_curtailment_mwh': safe_val(record.actual_curtailment_mwh),
                'budget_irradiation_kwh_m2': safe_val(record.budget_irradiation_kwh_m2),
                'actual_irradiation_kwh_m2': safe_val(record.actual_irradiation_kwh_m2),
                'expected_pr_percent': safe_val(record.expected_pr_percent),
                'actual_pr_percent': safe_val(record.actual_pr_percent),
                'created_at': record.created_at.isoformat() if record.created_at else None,
                'updated_at': record.updated_at.isoformat() if record.updated_at else None,
            })
        
        print(f"IC Budget vs Expected - ICVSEXVSCUR data: {len(icvsexvscur_data_list)} records")
        
        return render(request, 'main/IC Budget Vs Expected.html', {
            'icvsexvscur_data_json': json.dumps(icvsexvscur_data_list)
        })
    except Exception as e:
        print(f"Error in ic_budget_vs_expected_view: {str(e)}")
        import traceback
        traceback.print_exc()
        return render(request, 'main/IC Budget Vs Expected.html', {
            'icvsexvscur_data_json': json.dumps([]),
            'error_message': str(e)
        })

# ... existing code ...

@feature_required('kpi_dashboard')
@login_required
def kpi_dashboard_view(request):
    """KPI dashboard view using real-time KPI data instead of old YieldData"""
    try:
        # Get user accessible asset numbers
        accessible_asset_numbers = get_user_accessible_asset_numbers(request)
        
        if accessible_asset_numbers:
            # Get accessible asset codes for RealTimeKPI filtering
            accessible_assets = AssetList.objects.filter(asset_number__in=accessible_asset_numbers)
            accessible_asset_codes = [asset.asset_code for asset in accessible_assets]
            
            # Get real-time KPI data
            real_time_data = RealTimeKPI.objects.filter(asset_code__in=accessible_asset_codes)
        else:
            # If no sites assigned, return empty queryset
            real_time_data = RealTimeKPI.objects.none()
        
        kpi_data = []
        
        # Process RealTimeKPI data directly
        for rt_record in real_time_data:
            # Find corresponding asset by asset_code
            try:
                asset = AssetList.objects.get(asset_code=rt_record.asset_code)
            except AssetList.DoesNotExist:
                # Try to find by asset_number as fallback
                try:
                    asset = AssetList.objects.get(asset_number=rt_record.asset_code)
                except AssetList.DoesNotExist:
                    asset = None
            
            def safe_val(val):
                return "" if val is None or (isinstance(val, float) and math.isnan(val)) else val
            
            # Convert date to month format for compatibility with frontend
            month_str = rt_record.date.strftime('%Y-%m') if rt_record.date else ""
            
            kpi_data.append({
                'month': month_str,
                'country': asset.country if asset else '',
                'portfolio': asset.portfolio if asset else '',
                'assetno': asset.asset_number if asset else rt_record.asset_code,
                'dc_capacity_mw': safe_val(rt_record.dc_capacity_mw),
                'ic_approved_budget': safe_val(rt_record.daily_ic_mwh),
                'expected_budget': safe_val(rt_record.daily_expected_mwh),
                'weather_loss_or_gain': 0,  # Not available in RealTimeKPI
                'grid_curtailment': 0,  # Not available in RealTimeKPI
                'grid_outage': 0,  # Not available in RealTimeKPI
                'operation_budget': 0,  # Not available in RealTimeKPI
                'breakdown_loss': 0,  # Not available in RealTimeKPI
                'unclassified_loss': 0,  # Not available in RealTimeKPI
                'actual_generation': safe_val(rt_record.daily_generation_mwh),
                'string failure': 0,  # Not available in RealTimeKPI
                'inverter failure': 0,  # Not available in RealTimeKPI
                'mv_failure': 0,  # Not available in RealTimeKPI
                'hv_failure': 0,  # Not available in RealTimeKPI
                'expected_pr': safe_val(rt_record.expect_pr) / 100 if rt_record.expect_pr else 0,  # Convert percentage to decimal
                'actual_pr': safe_val(rt_record.actual_pr) / 100 if rt_record.actual_pr else 0,  # Convert percentage to decimal
                'pr_gap': (safe_val(rt_record.actual_pr) - safe_val(rt_record.expect_pr)) / 100 if (rt_record.actual_pr and rt_record.expect_pr) else 0,
                'pr_gap_observation': '',  # Not available in RealTimeKPI
                'pr_gap_action_need_to_taken': '',  # Not available in RealTimeKPI
                'revenue_loss': 0,  # Not available in RealTimeKPI
                'revenue_loss_observation': '',  # Not available in RealTimeKPI
                'revenue_loss_action_need_to_taken': '',  # Not available in RealTimeKPI
                'actual_irradiation': safe_val(rt_record.daily_irradiation_mwh),
                'budgeted_irradiation': safe_val(rt_record.daily_budget_irradiation_mwh),
                'ac_capacity_mw': float(asset.capacity) if asset and asset.capacity else 0,
                'bess_capacity_mwh': 0,  # Not available in RealTimeKPI
                'bess_generation_mwh': 0,  # Not available in RealTimeKPI
                # Add the new dollar fields (not available in RealTimeKPI, set to 0)
                'ppa_rate': 0,
                'ic_approved_budget_dollar': 0,
                'expected_budget_dollar': 0,
                'actual_generation_dollar': 0,
                'created_at': rt_record.last_updated.isoformat() if rt_record.last_updated else "",
                'updated_at': rt_record.last_updated.isoformat() if rt_record.last_updated else "",
                'remarks': '',
            })
        # Also load YieldData for historical data (January-September)
        yield_data_list = []
        if accessible_asset_numbers:
            yield_data = YieldData.objects.filter(assetno__in=accessible_asset_numbers)
            for record in yield_data:
                def safe_val(val):
                    return "" if val is None or (isinstance(val, float) and math.isnan(val)) else val
                yield_data_list.append({
                    'month': safe_val(record.month),
                    'country': safe_val(record.country),
                    'portfolio': safe_val(record.portfolio),
                    'assetno': safe_val(record.assetno),
                    'dc_capacity_mw': safe_val(record.dc_capacity_mw),
                    'ic_approved_budget': safe_val(record.ic_approved_budget),
                    'expected_budget': safe_val(record.expected_budget),
                    'weather_loss_or_gain': safe_val(record.weather_loss_or_gain),
                    'grid_curtailment': safe_val(record.grid_curtailment),
                    'grid_outage': safe_val(record.grid_outage),
                    'operation_budget': safe_val(record.operation_budget),
                    'breakdown_loss': safe_val(record.breakdown_loss),
                    'unclassified_loss': safe_val(record.unclassified_loss),
                    'actual_generation': safe_val(record.actual_generation),
                    'string_failure': safe_val(record.string_failure),
                    'inverter_failure': safe_val(record.inverter_failure),
                    'mv_failure': safe_val(record.mv_failure),
                    'hv_failure': safe_val(record.hv_failure),
                    'ac_failure': safe_val(record.ac_failure),
                    'budgeted_irradiation': safe_val(record.budgeted_irradiation),
                    'actual_irradiation': safe_val(record.actual_irradiation),
                    'ac_capacity_mw': safe_val(record.ac_capacity_mw),
                    'bess_capacity_mwh': safe_val(record.bess_capacity_mwh),
                    'bess_generation_mwh': safe_val(record.bess_generation_mwh),
                    'expected_pr': safe_val(record.expected_pr),
                    'actual_pr': safe_val(record.actual_pr),
                    'pr_gap': safe_val(record.pr_gap),
                    'pr_gap_observation': safe_val(record.pr_gap_observation),
                    'pr_gap_action_need_to_taken': safe_val(record.pr_gap_action_need_to_taken),
                    'revenue_loss': safe_val(record.revenue_loss),
                    'revenue_loss_observation': safe_val(record.revenue_loss_observation),
                    'revenue_loss_action_need_to_taken': safe_val(record.revenue_loss_action_need_to_taken),
                    'ppa_rate': safe_val(record.ppa_rate),
                    'ic_approved_budget_dollar': safe_val(record.ic_approved_budget_dollar),
                    'expected_budget_dollar': safe_val(record.expected_budget_dollar),
                    'actual_generation_dollar': safe_val(record.actual_generation_dollar),
                    'created_at': record.created_at.isoformat() if record.created_at else "",
                    'updated_at': record.updated_at.isoformat() if record.updated_at else "",
                })
        
        return render(request, 'main/KPI.html', {
            'kpi_data_json': json.dumps(kpi_data),
            'yield_data_json': json.dumps(yield_data_list)
        })
    except Exception as e:
        return render(request, 'main/KPI.html', {
            'kpi_data_json': json.dumps([]),
            'error_message': str(e)
        })




@feature_required('kpi_dashboard')
@login_required
def api_real_time_kpi_data(request):
    """API endpoint to get real-time KPI data"""
    try:
        # Get user accessible asset codes
        accessible_asset_numbers = get_user_accessible_asset_numbers(request)
        
        # Since real_time_kpi.asset_code matches asset_list.asset_number, 
        # we can use accessible_asset_numbers directly as accessible_asset_codes
        accessible_asset_codes = accessible_asset_numbers if accessible_asset_numbers else []
        
        # Get filters from request
        date_filter = request.GET.get('date', '')
        asset_codes = request.GET.get('asset_codes', '').split(',') if request.GET.get('asset_codes') else []
        countries = request.GET.get('countries', '').split(',') if request.GET.get('countries') else []
        portfolios = request.GET.get('portfolios', '').split(',') if request.GET.get('portfolios') else []
        
        # Base query
        if accessible_asset_codes:
            kpi_query = RealTimeKPI.objects.filter(asset_code__in=accessible_asset_codes)
        else:
            kpi_query = RealTimeKPI.objects.none()
        
        # Apply filters
        if date_filter:
            kpi_query = kpi_query.filter(date=date_filter)
        
        if asset_codes and asset_codes[0]:  # Check if first element is not empty
            kpi_query = kpi_query.filter(asset_code__in=asset_codes)
        
        # Filter by countries/portfolios through AssetList
        # Since real_time_kpi.asset_code matches asset_list.asset_number, we need to get asset_number values
        if countries and countries[0]:  # Check if first element is not empty
            asset_numbers_in_countries = AssetList.objects.filter(country__in=countries).values_list('asset_number', flat=True)
            kpi_query = kpi_query.filter(asset_code__in=asset_numbers_in_countries)
            
        if portfolios and portfolios[0]:  # Check if first element is not empty
            asset_numbers_in_portfolios = AssetList.objects.filter(portfolio__in=portfolios).values_list('asset_number', flat=True)
            kpi_query = kpi_query.filter(asset_code__in=asset_numbers_in_portfolios)
        
        # Get the data
        kpi_records = kpi_query.select_related().order_by('date', 'asset_code')  # Limit to recent 100 records
        
        # Format the data
        kpi_data = []
        for record in kpi_records:
            # Find asset by matching asset_number with record.asset_code
            # Since real_time_kpi.asset_code should match asset_list.asset_number
            asset = None
            try:
                asset = AssetList.objects.get(asset_number=record.asset_code)
            except AssetList.DoesNotExist:
                # Fallback: try matching asset_code with asset_code
                try:
                    asset = AssetList.objects.get(asset_code=record.asset_code)
                except AssetList.DoesNotExist:
                    asset = None
            
            # Helper function to safely handle NaN values
            def safe_float(val):
                if val is None:
                    return 0
                try:
                    if math.isnan(val):
                        return 0
                    return float(val)
                except (TypeError, ValueError):
                    return 0
            
            kpi_data.append({
                'asset_code': record.asset_code,
                'asset_name': asset.asset_name if asset else record.asset_code,
                'country': asset.country if asset else '',
                'portfolio': asset.portfolio if asset else '',
                'date': record.date.isoformat(),
                'daily_kwh': safe_float(record.daily_kwh),
                'daily_irr': safe_float(record.daily_irr),
                'daily_generation_mwh': safe_float(record.daily_generation_mwh),
                'daily_irradiation_mwh': safe_float(record.daily_irradiation_mwh),
                'daily_ic_mwh': safe_float(record.daily_ic_mwh),
                'daily_expected_mwh': safe_float(record.daily_expected_mwh),
                'daily_budget_irradiation_mwh': safe_float(record.daily_budget_irradiation_mwh),
                'expect_pr': safe_float(record.expect_pr),
                'actual_pr': safe_float(record.actual_pr),
                'dc_capacity_mw': safe_float(record.dc_capacity_mw),
                'last_updated': record.last_updated.isoformat(),
                'is_frozen': record.is_frozen,
                'capacity': float(asset.capacity) if asset and asset.capacity else 0,
                'timezone': asset.timezone if asset else '+00:00',
            })
        
        return JsonResponse({
            'success': True,
            'data': kpi_data,
            'count': len(kpi_data)
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@feature_required('kpi_dashboard') 
@login_required
def api_kpi_summary_stats(request):
    """API endpoint to get KPI summary statistics"""
    try:
        # Get user accessible asset codes
        accessible_asset_numbers = get_user_accessible_asset_numbers(request)
        
        if not accessible_asset_numbers:
            return JsonResponse({
                'success': True,
                'data': {
                    'total_assets': 0,
                    'total_daily_kwh': 0,
                    'avg_daily_irr': 0,
                    'last_updated': None
                }
            })
            
        accessible_assets = AssetList.objects.filter(asset_number__in=accessible_asset_numbers)
        accessible_asset_codes = [asset.asset_code for asset in accessible_assets]
        
        # Get today's date
        today = timezone.now().date()
        
        # Get today's KPI data
        today_kpi = RealTimeKPI.objects.filter(
            asset_code__in=accessible_asset_codes,
            date=today
        )
        
        # Calculate summary stats
        total_assets = today_kpi.count()
        total_daily_kwh = sum([record.daily_kwh or 0 for record in today_kpi])
        avg_daily_irr = sum([record.daily_irr or 0 for record in today_kpi]) / max(total_assets, 1)
        
        # Get last update time
        latest_record = today_kpi.order_by('-last_updated').first()
        last_updated = latest_record.last_updated.isoformat() if latest_record else None
        
        return JsonResponse({
            'success': True,
            'data': {
                'total_assets': total_assets,
                'total_daily_kwh': round(total_daily_kwh, 2),
                'avg_daily_irr': round(avg_daily_irr, 3),
                'last_updated': last_updated
            }
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)

@feature_required('sales')
@login_required
def sales_dashboard_view(request):
    """Sales dashboard view with data passed directly to template"""
    try:
        # Get user accessible asset numbers
        accessible_asset_numbers = get_user_accessible_asset_numbers(request)
        
        if accessible_asset_numbers:
            # Filter by accessible sites - YieldData uses assetno, AssetList uses asset_number
            yield_data = YieldData.objects.filter(assetno__in=accessible_asset_numbers)
            map_data = MapData.objects.filter(asset_no__in=accessible_asset_numbers)
        else:
            # If no sites assigned, return empty queryset
            yield_data = YieldData.objects.none()
            map_data = MapData.objects.none()
        
        yield_data_list = []
        for record in yield_data:
            def safe_val(val):
                return "" if val is None or (isinstance(val, float) and math.isnan(val)) else val
            yield_data_list.append({
                'month': safe_val(record.month),
                'country': safe_val(record.country),
                'portfolio': safe_val(record.portfolio),
                'assetno': safe_val(record.assetno),
                'dc_capacity_mw': safe_val(record.dc_capacity_mw),
                'ic_approved_budget': safe_val(record.ic_approved_budget),
                'expected_budget': safe_val(record.expected_budget),
                'weather_loss_or_gain': safe_val(record.weather_loss_or_gain),
                'grid_curtailment': safe_val(record.grid_curtailment),
                'grid_outage': safe_val(record.grid_outage),
                'operation_budget': safe_val(record.operation_budget),
                'breakdown_loss': safe_val(record.breakdown_loss),
                'unclassified_loss': safe_val(record.unclassified_loss),
                'actual_generation': safe_val(record.actual_generation),
                'string_failure': safe_val(record.string_failure),
                'inverter_failure': safe_val(record.inverter_failure),
                'mv_failure': safe_val(record.mv_failure),
                'hv_failure': safe_val(record.hv_failure),
                'expected_pr': safe_val(record.expected_pr),
                'actual_pr': safe_val(record.actual_pr),
                'pr_gap': safe_val(record.pr_gap),
                'pr_gap_observation': safe_val(record.pr_gap_observation),
                'pr_gap_action_need_to_taken': safe_val(record.pr_gap_action_need_to_taken),
                'revenue_loss': safe_val(record.revenue_loss),
                'revenue_loss_observation': safe_val(record.revenue_loss_observation),
                'revenue_loss_action_need_to_taken': safe_val(record.revenue_loss_action_need_to_taken),
                'actual_irradiation': safe_val(record.actual_irradiation),
                'ac_capacity_mw': safe_val(record.ac_capacity_mw),
                'bess_capacity_mwh': safe_val(record.bess_capacity_mwh),
                'bess_generation_mwh': safe_val(record.bess_generation_mwh),
                # Add the new dollar fields
                'ppa_rate': safe_val(record.ppa_rate),
                'ic_approved_budget_dollar': safe_val(record.ic_approved_budget_dollar),
                'expected_budget_dollar': safe_val(record.expected_budget_dollar),
                'actual_generation_dollar': safe_val(record.actual_generation_dollar),
                'created_at': record.created_at.isoformat() if record.created_at else "",
                'updated_at': record.updated_at.isoformat() if record.updated_at else "",
                'remarks': '',
            })
        
        map_data_list = []
        for record in map_data:
            def safe_val(val):
                return "" if val is None or (isinstance(val, float) and math.isnan(val)) else val
            map_data_list.append({
                'asset_no': safe_val(record.asset_no),
                'country': safe_val(record.country),
                'portfolio': safe_val(record.portfolio),
                'site_name': safe_val(record.site_name),
                'dc_capacity_mwp': safe_val(record.dc_capacity_mwp),
                'battery_capacity_mw': safe_val(record.battery_capacity_mw),
                'plant_type': safe_val(record.plant_type),
                'installation_type': safe_val(record.installation_type),
                'latitude': safe_val(record.latitude),
                'longitude': safe_val(record.longitude),
            })
        
        return render(request, 'main/sales.html', {
            'yield_data_json': json.dumps(yield_data_list),
            'map_data_json': json.dumps(map_data_list)
        })
    except Exception as e:
        return render(request, 'main/sales.html', {
            'yield_data_json': json.dumps([]),
            'map_data_json': json.dumps([]),
            'error_message': str(e)
        })

@feature_required('generation_report')
@login_required
def generation_report_view(request):
    """Generation Report view with optimized data processing"""
    try:
        # Get user accessible sites
        accessible_sites = get_user_accessible_sites(request)
        
        if not accessible_sites.exists():
            return render(request, 'main/Generation Report.html', {
                'error_message': 'No accessible sites found for your account.'
            })
        
        # Get asset_number values from accessible_sites
        accessible_asset_numbers = accessible_sites.values_list('asset_number', flat=True)
        
        # Fetch all required data
        # 1. YieldData for revenue table
        yield_data_records = YieldData.objects.filter(
            assetno__in=accessible_asset_numbers
        )
        
        # Create yield data list
        yield_data_list = []
        for record in yield_data_records:
            def safe_val(val):
                return "" if val is None or (isinstance(val, float) and math.isnan(val)) else val
            yield_data_list.append({
                'assetno': safe_val(record.assetno),
                'dc_capacity_mw': safe_val(record.dc_capacity_mw),
                'month': safe_val(record.month),
                'country': safe_val(record.country),
                'portfolio': safe_val(record.portfolio),
                'ic_approved_budget_dollar': safe_val(record.ic_approved_budget_dollar),
                'expected_budget_dollar': safe_val(record.expected_budget_dollar),
                'actual_generation_dollar': safe_val(record.actual_generation_dollar),
                'ppa_rate': safe_val(record.ppa_rate),
            })
        
        # 2. IC Approved Budget Daily data
        ic_approved_budget_daily_data = ICApprovedBudgetDailyData.objects.filter(
            asset_code__in=accessible_asset_numbers
        )
        
        # Transform to wide format
        ic_approved_budget_daily_wide = {}
        for record in ic_approved_budget_daily_data:
            def safe_val(val):
                return "" if val is None or (isinstance(val, float) and math.isnan(val)) else val
            date_key = record.date.isoformat() if record.date else "unknown"
            if date_key not in ic_approved_budget_daily_wide:
                ic_approved_budget_daily_wide[date_key] = {'Date': date_key}
            asset_key = record.asset_code if record.asset_code else "unknown"
            ic_approved_budget_daily_wide[date_key][asset_key] = safe_val(record.ic_approved_budget_kwh)
        
        ic_approved_budget_daily_list = list(ic_approved_budget_daily_wide.values())
        
        # 3. Actual Generation Daily data - CORRECTED FIELD NAME
        actual_gen_data = ActualGenerationDailyData.objects.filter(
            asset_code__in=accessible_asset_numbers
        )
        
        # Transform to wide format
        actual_gen_wide = {}
        for record in actual_gen_data:
            def safe_val(val):
                return "" if val is None or (isinstance(val, float) and math.isnan(val)) else val
            date_key = record.date.isoformat() if record.date else "unknown"
            if date_key not in actual_gen_wide:
                actual_gen_wide[date_key] = {'Date': date_key}
            asset_key = record.asset_code if record.asset_code else "unknown"
            actual_gen_wide[date_key][asset_key] = safe_val(record.generation_kwh)  # CORRECTED: generation_kwh not actual_generation_kwh
        
        actual_gen_list = list(actual_gen_wide.values())
        
        # 4. Expected Budget Daily data - CORRECTED FIELD NAME
        expected_budget_data = ExpectedBudgetDailyData.objects.filter(
            asset_code__in=accessible_asset_numbers
        )
        
        # Transform to wide format
        expected_budget_wide = {}
        for record in expected_budget_data:
            def safe_val(val):
                return "" if val is None or (isinstance(val, float) and math.isnan(val)) else val
            date_key = record.date.isoformat() if record.date else "unknown"
            if date_key not in expected_budget_wide:
                expected_budget_wide[date_key] = {'Date': date_key}
            asset_key = record.asset_code if record.asset_code else "unknown"
            expected_budget_wide[date_key][asset_key] = safe_val(record.expected_budget_kwh)  # CORRECTED: expected_budget_kwh
        
        expected_budget_list = list(expected_budget_wide.values())
        
        # 5. Budget GII Daily data - CORRECTED FIELD NAME
        budget_gii_data = BudgetGIIDailyData.objects.filter(
            asset_code__in=accessible_asset_numbers
        )
        
        # Transform to wide format
        budget_gii_wide = {}
        for record in budget_gii_data:
            def safe_val(val):
                return "" if val is None or (isinstance(val, float) and math.isnan(val)) else val
            date_key = record.date.isoformat() if record.date else "unknown"
            if date_key not in budget_gii_wide:
                budget_gii_wide[date_key] = {'Date': date_key}
            asset_key = record.asset_code if record.asset_code else "unknown"
            budget_gii_wide[date_key][asset_key] = safe_val(record.budget_gii_kwh)  # CORRECTED: budget_gii_kwh
        
        budget_gii_list = list(budget_gii_wide.values())
        
        # 6. Actual GII Daily data - CORRECTED FIELD NAME
        actual_gii_data = ActualGIIDailyData.objects.filter(
            asset_code__in=accessible_asset_numbers
        )
        
        # Transform to wide format
        actual_gii_wide = {}
        for record in actual_gii_data:
            def safe_val(val):
                return "" if val is None or (isinstance(val, float) and math.isnan(val)) else val
            date_key = record.date.isoformat() if record.date else "unknown"
            if date_key not in actual_gii_wide:
                actual_gii_wide[date_key] = {'Date': date_key}
            asset_key = record.asset_code if record.asset_code else "unknown"
            actual_gii_wide[date_key][asset_key] = safe_val(record.actual_gii_kwh)  # CORRECTED: actual_gii_kwh
        
        actual_gii_list = list(actual_gii_wide.values())
        
        # 7. Map data for DC capacity
        map_data = MapData.objects.filter(
            asset_no__in=accessible_asset_numbers
        )
        
        map_data_list = []
        for record in map_data:
            def safe_val(val):
                return "" if val is None or (isinstance(val, float) and math.isnan(val)) else val
            map_data_list.append({
                'asset_no': safe_val(record.asset_no),
                'dc_capacity_mwp': safe_val(record.dc_capacity_mwp),
                'country': safe_val(record.country),
                'portfolio': safe_val(record.portfolio),
            })
        
        return render(request, 'main/Generation Report.html', {
            'map_data_json': json.dumps(map_data_list),
            'ic_approved_budget_daily_json': json.dumps(ic_approved_budget_daily_list),
            'actual_gen_data_json': json.dumps(actual_gen_list),
            'expected_budget_data_json': json.dumps(expected_budget_list),
            'budget_gii_data_json': json.dumps(budget_gii_list),
            'actual_gii_data_json': json.dumps(actual_gii_list),
            'yield_data_json': json.dumps(yield_data_list),
        })
        
    except Exception as e:
        return render(request, 'main/Generation Report.html', {
            'map_data_json': json.dumps([]),
            'ic_approved_budget_daily_json': json.dumps([]),
            'actual_gen_data_json': json.dumps([]),
            'expected_budget_data_json': json.dumps([]),
            'budget_gii_data_json': json.dumps([]),
            'actual_gii_data_json': json.dumps([]),
            'yield_data_json': json.dumps([]),
            'error_message': f'An error occurred while loading the generation report: {str(e)}'
        })

@feature_required('data_upload')
@login_required
@csrf_exempt
def data_upload_view(request):
    print(f"Data upload view accessed - Method: {request.method}")
    if request.method == 'GET':
        print("Rendering data_upload.html template")
        return render(request, 'main/data_upload.html')
    
    print(f"POST request received to data_upload_view")
    try:
        if 'csv_file' not in request.FILES:
            print("No csv_file in request.FILES")
            messages.error(request, 'No file uploaded')
            return render(request, 'main/data_upload.html')
        
        file = request.FILES['csv_file']
        data_type = request.POST.get('data_type', 'unknown')
        upload_mode = request.POST.get('upload_mode', 'append')
        
        print(f"Processing upload: file={file.name}, data_type={data_type}, upload_mode={upload_mode}")
        
        # Use the process_csv_upload function which has proper logging
        result = process_csv_upload(
            csv_file=file,
            data_type=data_type,
            upload_mode=upload_mode,
            user=request.user
        )
        
        print(f"Upload result: {result}")
        
        if result.get('success', False):
            records_imported = result.get('records_imported', 0)
            records_skipped = result.get('records_skipped', 0)
            records_updated = result.get('records_updated', 0)
            
            # Build success message with detailed statistics
            success_parts = [f'✅ Successfully processed {file.name}']
            success_parts.append(f'📊 Statistics: {records_imported} imported, {records_updated} updated, {records_skipped} skipped')
            
            # Add warnings if any
            if result.get('warnings'):
                success_parts.append('⚠️ Warnings:')
                for warning in result['warnings'][:3]:  # Show first 3 warnings
                    success_parts.append(f'  • {warning}')
                if len(result['warnings']) > 3:
                    success_parts.append(f'  • ... and {len(result["warnings"]) - 3} more warnings')
            
            messages.success(request, '\n'.join(success_parts))
        else:
            error_msg = result.get('error', 'Upload failed')
            
            # Check if this is a validation error with detailed information
            validation_details = result.get('validation_details')
            if validation_details:
                # Build comprehensive error message
                error_parts = [f'❌ Upload failed: {error_msg}']
                
                # Add statistics if available
                if validation_details.get('statistics'):
                    stats = validation_details['statistics']
                    error_parts.append(f'📊 File Statistics: {stats["total_rows"]} rows, {stats["total_columns"]} columns')
                    if stats['empty_rows'] > 0:
                        error_parts.append(f'⚠️ {stats["empty_rows"]} empty rows found')
                    if stats['missing_data_count'] > 0:
                        error_parts.append(f'⚠️ {stats["missing_data_count"]} missing values found')
                
                messages.error(request, '\n'.join(error_parts))
            else:
                messages.error(request, f'❌ Upload failed: {error_msg}')
            
    except Exception as e:
        print(f"Exception in data_upload_view: {str(e)}")
        import traceback
        traceback.print_exc()
        messages.error(request, f'❌ Error during upload: {str(e)}')
    
    return render(request, 'main/data_upload.html')

@feature_required('data_upload')
@login_required
@csrf_exempt
def data_upload_help_view(request):
    """Help page for data upload with templates and instructions"""
    return render(request, 'main/data_upload_help.html')

def process_csv_upload(csv_file, data_type, upload_mode='append', start_date=None, end_date=None, 
                      skip_duplicates=True, validate_data=True, batch_size=1000, user=None):
    """
    Process CSV file upload with append/replace functionality
    """
    import time
    start_time = time.time()
    
    try:
        # Read CSV file with intelligent encoding detection and detailed error reporting
        detected_encoding = detect_file_encoding(csv_file)
        encodings_to_try = [
            detected_encoding, 'utf-8', 'latin-1', 'cp1252', 'iso-8859-1', 'windows-1252',
            'ascii', 'utf-8-sig', 'utf-16', 'utf-16le', 'utf-16be', 'big5', 'gbk', 'shift_jis'
        ]
        df = None
        error_details = []
        
        print(f"Trying to read CSV file: {csv_file.name if hasattr(csv_file, 'name') else 'Unknown'}")
        print(f"Detected encoding: {detected_encoding}")
        
        for encoding in encodings_to_try:
            if encoding is None:
                continue
                
            result = try_read_csv_with_encoding(csv_file, encoding)
            if result['success']:
                df = result['df']
                print(f"✅ Successfully read CSV with encoding: {encoding}")
                break
            else:
                error_details.append(f"{encoding}: {result['error']}")
                print(f"❌ Failed with {encoding}: {result['error']}")
        
        if df is None:
            # Try cleaning the file content to remove problematic characters
            print("Attempting to clean file content...")
            cleaned_file = clean_file_content(csv_file)
            
            # Try reading the cleaned file
            for encoding in ['utf-8', 'latin-1', 'cp1252']:
                result = try_read_csv_with_encoding(cleaned_file, encoding)
                if result['success']:
                    df = result['df']
                    print(f"✅ Successfully read cleaned CSV with encoding: {encoding}")
                    break
                else:
                    print(f"❌ Failed with cleaned file and {encoding}: {result['error']}")
            
            if df is None:
                # Try decoding with error handling
                print("Attempting to decode with error handling...")
                for encoding in ['cp1252', 'latin-1', 'utf-8']:
                    decoded_file = try_decode_with_errors(csv_file, encoding)
                    if decoded_file:
                        try:
                            df = pd.read_csv(decoded_file)
                            print(f"✅ Successfully read decoded CSV with encoding: {encoding}")
                            break
                        except Exception as e:
                            print(f"❌ Failed to read decoded file with {encoding}: {e}")
                
                if df is None:
                    # Analyze the file to provide specific guidance
                    analysis = analyze_file_encoding(csv_file)
                    error_message = f"Could not read CSV file with any supported encoding.\n\nFile analysis: {analysis}\n\nTried encodings: {', '.join([e for e in encodings_to_try if e is not None])}\n\nError details:\n" + "\n".join(error_details[:5])  # Show first 5 errors
                    error_message += "\n\nSolutions:\n1. Open the file in a text editor (like Notepad++) and save as UTF-8\n2. If using Excel, save as 'CSV UTF-8 (Comma delimited)'\n3. Check if the file contains special characters or corrupted data\n4. Try opening the file in a text editor and removing any special characters\n5. The file contains smart quotes or special characters that need to be converted"
                    return {'success': False, 'error': error_message}
        
        if df.empty:
            return {'success': False, 'error': 'CSV file is empty'}
        
        # Clean column names - preserve asset codes for daily data types
        if data_type in ['actual_generation_daily', 'expected_budget_daily', 'budget_gii_daily', 'actual_gii_daily', 'ic_approved_budget_daily']:
            # For daily data, only normalize the first column (Date), preserve asset columns
            original_columns = df.columns.tolist()
            normalized_columns = []
            
            for i, col in enumerate(original_columns):
                if i == 0:  # First column (Date column)
                    normalized_columns.append(col.strip().lower().replace(' ', '_').replace('(', '').replace(')', '').replace('/', '_').replace('-', '_'))
                else:  # Asset columns - preserve original case but clean spaces and special chars
                    normalized_columns.append(col.strip().replace(' ', '_').replace('(', '').replace(')', '').replace('/', '_'))
            
            df.columns = normalized_columns
        else:
            # For other data types, normalize all columns as before
            normalized_columns = []
            for col in df.columns:
                normalized_col = col.strip().lower().replace(' ', '_').replace('(', '').replace(')', '').replace('/', '_').replace('-', '_')
                
                # Special handling for dollar sign - replace _$ with _dollar and $ with _dollar
                if normalized_col.endswith('_$'):
                    normalized_col = normalized_col.replace('_$', '_dollar')
                else:
                    normalized_col = normalized_col.replace('$', '_dollar')
                
                # Clean up any double underscores
                while '__' in normalized_col:
                    normalized_col = normalized_col.replace('__', '_')
                
                # Special handling for ICVSEXVSCUR percentage columns
                if data_type == 'icvsexvscur':
                    if 'expected_pr' in normalized_col and 'percent' not in normalized_col:
                        normalized_col = 'expected_pr_percent'
                    elif 'actual_pr' in normalized_col and 'percent' not in normalized_col:
                        normalized_col = 'actual_pr_percent'
                
                normalized_columns.append(normalized_col)
            
            df.columns = normalized_columns
                
        # Validate data if requested
        if validate_data:
            # First, check basic CSV requirements
            file_name = csv_file.name if hasattr(csv_file, 'name') else ''
            requirements_result = validate_csv_requirements(df, data_type, file_name)
            
            # Then do detailed validation
            validation_result = validate_csv_data(df, data_type)
            
            # Combine results
            if not requirements_result.get('valid', False) or not validation_result.get('valid', False):
                # Build comprehensive error message
                primary_error = requirements_result.get('error') or validation_result.get('error', 'Unknown validation error')
                error_parts = [f'Data validation failed: {primary_error}']
                
                # Add requirements failures
                if requirements_result.get('requirements_failed'):
                    error_parts.append('\nRequirements Not Met:')
                    for req in requirements_result['requirements_failed'][:5]:
                        error_parts.append(f'  • {req}')
                
                # Add column issues
                if validation_result.get('column_issues'):
                    error_parts.append('\nColumn Issues:')
                    for issue in validation_result['column_issues'][:5]:  # Show first 5 issues
                        error_parts.append(f'  • {issue}')
                    if len(validation_result['column_issues']) > 5:
                        error_parts.append(f'  • ... and {len(validation_result["column_issues"]) - 5} more column issues')
                
                if validation_result.get('data_issues'):
                    error_parts.append('\nData Issues:')
                    for issue in validation_result['data_issues'][:5]:  # Show first 5 issues
                        error_parts.append(f'  • {issue}')
                    if len(validation_result['data_issues']) > 5:
                        error_parts.append(f'  • ... and {len(validation_result["data_issues"]) - 5} more data issues')
                
                # Add suggestions from requirements and validation
                all_suggestions = []
                if requirements_result.get('suggestions'):
                    all_suggestions.extend(requirements_result['suggestions'])
                if validation_result.get('warnings'):
                    all_suggestions.extend([f'Warning: {w}' for w in validation_result['warnings']])
                
                if all_suggestions:
                    error_parts.append('\nSuggestions:')
                    for suggestion in all_suggestions[:5]:
                        error_parts.append(f'  • {suggestion}')
                    if len(all_suggestions) > 5:
                        error_parts.append(f'  • ... and {len(all_suggestions) - 5} more suggestions')
                
                # Add specific suggestions for yield data
                if data_type == 'yield':
                    error_parts.append('\nYield CSV Requirements:')
                    error_parts.append('  • Required columns: "month", "country", "portfolio", "assetno"')
                    error_parts.append('  • Column naming: Use underscores instead of spaces')
                    error_parts.append('  • Dollar columns: End with "_dollar" instead of "$"')
                    error_parts.append('  • Month format: Use "2025-01" or similar date format')
                
                return {
                    'success': False, 
                    'error': '\n'.join(error_parts),
                    'validation_details': validation_result
                }
        
        # Process based on upload mode
        if upload_mode == 'replace':
            # For replace mode, we want to update existing records instead of skipping them
            skip_duplicates = False
            # Delete existing data in date range if specified
            if start_date and end_date:
                delete_result = delete_data_by_date_range(data_type, start_date, end_date)
                if not delete_result['success']:
                    return {'success': False, 'error': f'Failed to delete existing data: {delete_result["error"]}'}
        
        # Import data
        import_result = import_csv_data(df, data_type, skip_duplicates, batch_size, user)
        
        # Add validation warnings to import result if validation passed but had warnings
        if validate_data and validation_result.get('warnings'):
            if 'warnings' not in import_result:
                import_result['warnings'] = []
            import_result['warnings'].extend(validation_result['warnings'])
        
        # Calculate processing time
        processing_time = time.time() - start_time
        
        # Log the import
        if user:
            try:
                print(f"Attempting to log import for user: {user.username}")
                # Create log entry with fallback for missing data_type column
                log_data = {
                    'file_name': csv_file.name,
                    'upload_mode': upload_mode,
                    'records_imported': import_result.get('records_imported', 0),
                    'records_skipped': import_result.get('records_skipped', 0),
                    'status': 'success' if import_result.get('success', False) else 'failed',
                    'error_message': import_result.get('error', ''),
                    'imported_by': user,
                    'file_size': csv_file.size,
                    'processing_time': processing_time
                }
                
                # Try to add data_type if the column exists
                try:
                    log_data['data_type'] = data_type
                except:
                    # If data_type column doesn't exist, skip it
                    pass
                
                print(f"Creating DataImportLog with data: {log_data}")
                log_entry = DataImportLog.objects.create(**log_data)
                print(f"Successfully created log entry with ID: {log_entry.id}")
            except Exception as log_error:
                print(f"Error logging import: {log_error}")
                import traceback
                traceback.print_exc()
        
        return import_result
        
    except Exception as e:
        # Log failed import
        if user:
            try:
                processing_time = time.time() - start_time
                log_data = {
                    'file_name': csv_file.name if hasattr(csv_file, 'name') else 'Unknown',
                    'upload_mode': upload_mode,
                    'records_imported': 0,
                    'records_skipped': 0,
                    'status': 'failed',
                    'error_message': str(e),
                    'imported_by': user,
                    'file_size': csv_file.size if hasattr(csv_file, 'size') else 0,
                    'processing_time': processing_time
                }
                
                # Try to add data_type if the column exists
                try:
                    log_data['data_type'] = data_type
                except:
                    # If data_type column doesn't exist, skip it
                    pass
                
                DataImportLog.objects.create(**log_data)
            except Exception as log_error:
                print(f"Error logging failed import: {log_error}")
        
        return {'success': False, 'error': str(e)}

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
        
        elif data_type in ['actual_generation_daily', 'expected_budget_daily', 'budget_gii_daily', 'actual_gii_daily']:
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
            # Validate ICVSEXVSCUR data - check month format
            if 'month' in df.columns:
                # Check that month values follow either "25-Apr" or "Jan-25" format
                sample_months = df['month'].dropna().astype(str).head(5)
                for month_val in sample_months:
                    if '-' not in month_val:
                        return {
                            'valid': False, 
                            'error': f'Invalid month format "{month_val}". Expected format: "25-Apr" or "Jan-25"'
                        }
                    parts = month_val.split('-')
                    if len(parts) != 2:
                        return {
                            'valid': False, 
                            'error': f'Invalid month format "{month_val}". Expected format: "25-Apr" or "Jan-25"'
                        }
                    
                    part1, part2 = parts
                    valid_months = ['jan', 'feb', 'mar', 'apr', 'may', 'jun', 'jul', 'aug', 'sep', 'oct', 'nov', 'dec']
                    
                    # Check if it's "25-Apr" format (year-month)
                    if part1.isdigit() and len(part1) == 2 and part2.lower() in valid_months:
                        continue  # Valid "25-Apr" format
                    # Check if it's "Jan-25" format (month-year)
                    elif part1.lower() in valid_months and part2.isdigit() and len(part2) == 2:
                        continue  # Valid "Jan-25" format
                    else:
                        return {
                            'valid': False, 
                            'error': f'Invalid month format "{month_val}". Expected format: "25-Apr" or "Jan-25"'
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
    from . import models
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

def validate_yield_columns(df):
    """
    Validate yield data columns and check for mapping issues (legacy function for backward compatibility)
    """
    return validate_data_type_columns(df, 'yield')

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

def validate_yield_data_content(df):
    """
    Validate the content of yield data for common issues (legacy function for backward compatibility)
    """
    return validate_data_content(df, 'yield')

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
        'asset_list': ['asset_code', 'asset_name', 'country', 'portfolio'],
        'device_list': ['device_id', 'device_name', 'device_type', 'country'],
        'device_mapping': ['asset_code', 'device_type', 'metric', 'oem_tag'],
        'budget_values': ['asset_code', 'month_str', 'bd_production', 'bd_ghi', 'bd_gti'],
        'ic_budget': ['asset_code', 'asset_number', 'month_str', 'month_date', 'ic_bd_production']
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

def delete_data_by_date_range(data_type, start_date, end_date):
    """
    Delete data within specified date range
    """
    try:
        start_dt = datetime.strptime(start_date, '%Y-%m-%d').date()
        end_dt = datetime.strptime(end_date, '%Y-%m-%d').date()
        
        model_mapping = {
            'yield': YieldData,
            'bess': BESSData,
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
            'ic_approved_budget_daily': ICApprovedBudgetDailyData
        }
        
        model = model_mapping.get(data_type)
        if not model:
            return {'success': False, 'error': 'Invalid data type'}
        
        # Delete based on date field
        if data_type in ['actual_generation_daily', 'expected_budget_daily', 'budget_gii_daily', 'actual_gii_daily']:
            deleted_count = model.objects.filter(
                date__gte=start_dt,
                date__lte=end_dt
            ).delete()[0]
        elif data_type == 'bess':
            deleted_count = model.objects.filter(
                date__gte=start_date,
                date__lte=end_date
            ).delete()[0]
        else:
            # For other models, delete by month if available
            deleted_count = model.objects.filter(
                month__gte=start_date,
                month__lte=end_date
            ).delete()[0]
        
        return {'success': True, 'deleted_count': deleted_count}
        
    except Exception as e:
        return {'success': False, 'error': str(e)}

def import_csv_data(df, data_type, skip_duplicates=True, batch_size=1000, user=None):
    """
    Import CSV data into appropriate model
    """
    try:
        model_mapping = {
            'yield': YieldData,
            'bess': BESSData,
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
            'ic_approved_budget_daily': ICApprovedBudgetDailyData
        }
        
        model = model_mapping.get(data_type)
        if not model:
            return {'success': False, 'error': 'Invalid data type'}
        
        # Special handling for daily CSV files (wide format)
        if data_type in ['actual_generation_daily', 'expected_budget_daily', 'budget_gii_daily', 'actual_gii_daily', 'ic_approved_budget_daily']:
            return import_daily_csv_data(df, model, data_type, skip_duplicates, user)
        
        records_imported = 0
        records_skipped = 0
        records_updated = 0
        
        # Process data in batches for regular CSV files
        for i in range(0, len(df), batch_size):
            batch_df = df.iloc[i:i+batch_size]
            batch_records = []
            
            for _, row in batch_df.iterrows():
                try:
                    # Create model instance
                    instance = create_model_instance(model, row, data_type)
                    
                    if instance:
                        # Check for duplicates
                        if check_duplicate(instance, model, data_type):
                            if skip_duplicates:
                                # Skip if we're in append mode
                                records_skipped += 1
                                continue
                            else:
                                # Update existing record if we're in replace mode
                                existing_record = get_existing_record(instance, model, data_type)
                                if existing_record:
                                    update_record(existing_record, instance)
                                    records_updated += 1
                                    continue
                        
                        batch_records.append(instance)
                        records_imported += 1
                        
                except Exception as e:
                    print(f"Error processing row: {e}")
                    continue
            
            # Bulk create records
            if batch_records:
                model.objects.bulk_create(batch_records, ignore_conflicts=True)
        
        # Log the import
        if user:
            DataImportLog.objects.create(
                file_name=f"{data_type}_import_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                records_imported=records_imported,
                status='success',
                imported_by=user
            )
        
        # Add detailed feedback about the import process
        result = {
            'success': True,
            'records_imported': records_imported,
            'records_skipped': records_skipped,
            'records_updated': records_updated,
            'warnings': []
        }
        
        # Add warnings about skipped/updated records
        if records_skipped > 0:
            result['warnings'].append(f'{records_skipped} duplicate records were skipped')
        
        if records_updated > 0:
            result['warnings'].append(f'{records_updated} existing records were updated')
        
        # Add column mapping information for all data types
        if hasattr(df, 'columns'):
            column_validation = validate_data_type_columns(df, data_type)
            mapped_columns = column_validation['mapped_columns']
            unmapped_columns = column_validation['unmapped_columns']
            
            if mapped_columns:
                result['warnings'].append(f'{len(mapped_columns)} columns successfully mapped to database fields')
            
            if unmapped_columns:
                # Filter out auto-generated fields
                significant_unmapped = [orig_col for orig_col, norm_col in unmapped_columns if orig_col.lower() not in ['id', 'created_at', 'updated_at']]
                if significant_unmapped:
                    result['warnings'].append(f'{len(significant_unmapped)} columns could not be mapped: {", ".join(list(significant_unmapped)[:3])}{"..." if len(significant_unmapped) > 3 else ""}')
        
        return result
        
    except Exception as e:
        return {'success': False, 'error': str(e)}

def import_daily_csv_data(df, model, data_type, skip_duplicates=True, user=None):
    """
    Import daily CSV data from wide format (dates as rows, assets as columns)
    """
    try:
        records_imported = 0
        records_skipped = 0
        records_updated = 0
        
        # Get the date column (first column)
        date_col = df.columns[0]
        
        # Get asset columns (all except first column)
        asset_cols = df.columns[1:]
        
        print(f"Processing daily CSV: Date column: {date_col}, Asset columns: {len(asset_cols)} assets")
        
        # Define value column name based on data type
        value_column_mapping = {
            'actual_generation_daily': 'generation_kwh',
            'expected_budget_daily': 'expected_budget_kwh',
            'budget_gii_daily': 'budget_gii_kwh',
            'actual_gii_daily': 'actual_gii_kwh',
            'ic_approved_budget_daily': 'ic_approved_budget_kwh'
        }
        
        value_column_name = value_column_mapping.get(data_type, 'value')
        
        batch_records = []
        
        for _, row in df.iterrows():
            try:
                # Parse date from first column
                date_str = str(row[date_col])
                if ' ' in date_str:
                    date_str = date_str.split(' ')[0]  # Remove time part if present
                
                # Try different date formats
                date_obj = None
                for fmt in ['%m/%d/%Y', '%Y-%m-%d', '%d/%m/%Y']:
                    try:
                        date_obj = pd.to_datetime(date_str, format=fmt).date()
                        break
                    except:
                        continue
                
                if not date_obj:
                    try:
                        date_obj = pd.to_datetime(date_str).date()
                    except:
                        print(f"Could not parse date: {date_str}")
                        continue
                
                # Process each asset column
                for asset_col in asset_cols:
                    asset_code = asset_col.strip()
                    value = row[asset_col]
                    
                    # Skip empty or null values
                    if pd.isna(value) or value == '' or value == 0:
                        continue
                    
                    try:
                        value_float = float(value)
                    except (ValueError, TypeError):
                        continue
                    
                    # Check if record already exists
                    existing_record = model.objects.filter(
                        date=date_obj,
                        asset_code=asset_code
                    ).first()
                    
                    if existing_record:
                        if skip_duplicates:
                            records_skipped += 1
                            continue
                        else:
                            # Update existing record
                            setattr(existing_record, value_column_name, value_float)
                            existing_record.save()
                            records_updated += 1
                            continue
                    
                    # Create new record
                    record_data = {
                        'date': date_obj,
                        'asset_code': asset_code,
                        value_column_name: value_float
                    }
                    
                    batch_records.append(model(**record_data))
                    records_imported += 1
                    
                    # Bulk create in batches of 1000
                    if len(batch_records) >= 1000:
                        model.objects.bulk_create(batch_records, ignore_conflicts=True)
                        batch_records = []
                        
            except Exception as e:
                print(f"Error processing row: {e}")
                continue
        
        # Create remaining records
        if batch_records:
            model.objects.bulk_create(batch_records, ignore_conflicts=True)
        
        # Log the import
        if user:
            try:
                DataImportLog.objects.create(
                    file_name=f"{data_type}_import_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                    data_type=data_type,
                    records_imported=records_imported,
                    records_skipped=records_skipped,
                    status='success',
                    imported_by=user
                )
            except Exception as log_error:
                print(f"Error logging import: {log_error}")
        
        return {
            'success': True,
            'records_imported': records_imported,
            'records_skipped': records_skipped,
            'records_updated': records_updated
        }
        
    except Exception as e:
        print(f"Error importing daily CSV data: {e}")
        import traceback
        traceback.print_exc()
        return {'success': False, 'error': str(e)}

def get_existing_record(instance, model, data_type):
    """
    Get existing record for update
    """
    try:
        if data_type in ['actual_generation_daily', 'expected_budget_daily', 'budget_gii_daily', 'actual_gii_daily']:
            return model.objects.filter(
                date=instance.date,
                asset_code=instance.asset_code
            ).first()
        elif data_type == 'yield':
            return model.objects.filter(
                month=instance.month,
                country=instance.country,
                portfolio=instance.portfolio,
                assetno=instance.assetno
            ).first()
        elif data_type == 'bess':
            return model.objects.filter(
                date=instance.date,
                asset_no=instance.asset_no
            ).first()
        elif data_type == 'aoc':
            return model.objects.filter(
                s_no=instance.s_no,
                month=instance.month,
                asset_no=instance.asset_no
            ).first()
        elif data_type == 'ice':
            return model.objects.filter(
                month=instance.month,
                portfolio=instance.portfolio
            ).first()
        elif data_type == 'icvsexvscur':
            return model.objects.filter(
                month=instance.month,
                country=instance.country,
                portfolio=instance.portfolio
            ).first()
        elif data_type == 'map':
            return model.objects.filter(
                asset_no=instance.asset_no
            ).first()
        elif data_type == 'minamata':
            return model.objects.filter(
                month=instance.month
            ).first()
        
        return None
        
    except Exception as e:
        print(f"Error getting existing record: {e}")
        return None

def update_record(existing_record, new_instance):
    """
    Update existing record with new data
    """
    try:
        # Get all fields from the model
        fields = [field.name for field in existing_record._meta.fields if not field.primary_key]
        
        # Update each field
        for field_name in fields:
            if hasattr(new_instance, field_name):
                new_value = getattr(new_instance, field_name)
                if new_value is not None:
                    setattr(existing_record, field_name, new_value)
        
        # Save the updated record
        existing_record.save()
        
    except Exception as e:
        print(f"Error updating record: {e}")

def create_model_instance(model, row, data_type):
    """
    Create model instance from row data
    """
    try:
        data = {}
        
        # Map row data to model fields
        for field in model._meta.fields:
            if field.name in row and pd.notna(row[field.name]):
                value = row[field.name]
                
                # Convert data types
                if field.get_internal_type() == 'FloatField':
                    try:
                        # Handle percentage values by removing % symbol
                        if isinstance(value, str) and value.strip().endswith('%'):
                            # Remove % and convert to float
                            value = float(value.strip().rstrip('%'))
                        else:
                            value = float(value)
                    except:
                        value = 0.0
                elif field.get_internal_type() == 'IntegerField':
                    try:
                        value = int(value)
                    except:
                        value = 0
                elif field.get_internal_type() == 'DateField':
                    try:
                        # Special handling for month field in ICVSEXVSCUR data
                        if data_type == 'icvsexvscur' and field.name == 'month':
                            value = parse_month_to_date(value)
                        else:
                            value = pd.to_datetime(value).date()
                    except:
                        continue
                
                data[field.name] = value
        
        return model(**data)
        
    except Exception as e:
        print(f"Error creating model instance: {e}")
        return None

def parse_month_to_date(month_str):
    """
    Parse month string like '25-Apr' or 'Jan-25' to date object like '2025-04-01'
    """
    from datetime import datetime
    
    month_mapping = {
        'jan': 1, 'feb': 2, 'mar': 3, 'apr': 4, 'may': 5, 'jun': 6,
        'jul': 7, 'aug': 8, 'sep': 9, 'oct': 10, 'nov': 11, 'dec': 12
    }
    
    try:
        if isinstance(month_str, str) and '-' in month_str:
            parts = month_str.split('-')
            if len(parts) == 2:
                part1 = parts[0].strip()
                part2 = parts[1].strip()
                
                # Check if it's "25-Apr" format (year-month)
                if part1.isdigit() and len(part1) == 2 and part2.lower() in month_mapping:
                    year_part = part1
                    month_part = part2.lower()
                # Check if it's "Jan-25" format (month-year)  
                elif part1.lower() in month_mapping and part2.isdigit() and len(part2) == 2:
                    year_part = part2
                    month_part = part1.lower()
                else:
                    print(f"Invalid month format: {month_str}")
                    return datetime.now().replace(day=1).date()
                
                # Determine year (assuming 25 means 2025)
                if year_part.isdigit():
                    year = 2000 + int(year_part) if int(year_part) < 100 else int(year_part)
                else:
                    year = 2025  # Default fallback
                
                # Get month number
                month_num = month_mapping.get(month_part, 1)
                
                # Return date object for 1st day of the month
                return datetime(year, month_num, 1).date()
    except Exception as e:
        print(f"Error parsing month '{month_str}': {e}")
    
    # Fallback to current date if parsing fails
    return datetime.now().replace(day=1).date()

def check_duplicate(instance, model, data_type):
    """
    Check if record already exists
    """
    try:
        if data_type in ['actual_generation_daily', 'expected_budget_daily', 'budget_gii_daily', 'actual_gii_daily']:
            return model.objects.filter(
                date=instance.date,
                asset_code=instance.asset_code
            ).exists()
        elif data_type == 'yield':
            return model.objects.filter(
                month=instance.month,
                country=instance.country,
                portfolio=instance.portfolio,
                assetno=instance.assetno
            ).exists()
        elif data_type == 'bess':
            return model.objects.filter(
                date=instance.date,
                asset_no=instance.asset_no
            ).exists()
        elif data_type == 'aoc':
            return model.objects.filter(
                s_no=instance.s_no,
                month=instance.month,
                asset_no=instance.asset_no
            ).exists()
        elif data_type == 'ice':
            return model.objects.filter(
                month=instance.month,
                portfolio=instance.portfolio
            ).exists()
        elif data_type == 'icvsexvscur':
            return model.objects.filter(
                month=instance.month,
                country=instance.country,
                portfolio=instance.portfolio
            ).exists()
        elif data_type == 'map':
            return model.objects.filter(
                asset_no=instance.asset_no
            ).exists()
        elif data_type == 'minamata':
            return model.objects.filter(
                month=instance.month
            ).exists()
        
        return False
        
    except Exception as e:
        print(f"Error checking duplicate: {e}")
        return False

# API endpoints for data management
@csrf_exempt
@login_required
def api_data_counts(request):
    """Get data counts for all data types"""
    try:
        counts = {
            'yield_count': YieldData.objects.count(),
            'bess_count': BESSData.objects.count(),
            'aoc_count': AOCData.objects.count(),
            'ice_count': ICEData.objects.count(),
            'icvsexvscur_count': ICVSEXVSCURData.objects.count(),
            'map_count': MapData.objects.count(),
            'minamata_count': MinamataStringLossData.objects.count(),
            'actual_generation_daily_count': ActualGenerationDailyData.objects.count(),
            'expected_budget_daily_count': ExpectedBudgetDailyData.objects.count(),
            'budget_gii_daily_count': BudgetGIIDailyData.objects.count(),
            'actual_gii_daily_count': ActualGIIDailyData.objects.count(),
            'ic_approved_budget_daily_count': ICApprovedBudgetDailyData.objects.count(),
        }
        return JsonResponse(counts)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

@login_required
def api_upload_history(request):
    """API endpoint to get upload history"""
    try:
        print(f"Fetching upload history for user: {request.user.username}")
        # Try to get uploads for the current user or all uploads if admin
        try:
            if request.user.is_superuser:
                uploads = DataImportLog.objects.all()[:50]  # Limit to 50 most recent
                print(f"Admin user - found {uploads.count()} total uploads")
            else:
                uploads = DataImportLog.objects.filter(imported_by=request.user)[:50]
                print(f"Regular user - found {uploads.count()} uploads for user")
            
            uploads_data = []
            for upload in uploads:
                try:
                    # Use getattr with fallbacks for all fields that might be missing
                    data_type = getattr(upload, 'data_type', 'unknown')
                    if data_type == 'unknown':
                        # Try to infer from file name
                        if 'yield' in upload.file_name.lower():
                            data_type = 'yield'
                        elif 'bess' in upload.file_name.lower():
                            data_type = 'bess'
                        elif 'aoc' in upload.file_name.lower():
                            data_type = 'aoc'
                        else:
                            data_type = 'unknown'
                    
                    uploads_data.append({
                        'file_name': upload.file_name,
                        'data_type': data_type,
                        'upload_mode': getattr(upload, 'upload_mode', 'append'),
                        'import_date': getattr(upload, 'import_date', None),
                        'records_imported': getattr(upload, 'records_imported', 0),
                        'records_skipped': getattr(upload, 'records_skipped', 0),
                        'status': getattr(upload, 'status', 'success'),
                        'imported_by': getattr(upload.imported_by, 'username', 'Unknown') if hasattr(upload, 'imported_by') and upload.imported_by else 'Unknown',
                        'file_size_mb': getattr(upload, 'file_size_mb', 0),
                        'processing_time': round(getattr(upload, 'processing_time', 0), 2),
                        'success_rate': getattr(upload, 'success_rate', 0)
                    })
                except Exception as upload_error:
                    # Skip problematic records
                    print(f"Error processing upload record: {upload_error}")
                    continue
            
            print(f"Returning {len(uploads_data)} upload records")
            return JsonResponse({'uploads': uploads_data})
            
        except Exception as db_error:
            # If table doesn't exist or other database issues, return empty list
            print(f"Database error in upload history: {db_error}")
            return JsonResponse({
                'uploads': [], 
                'message': 'No upload history available yet. Upload some data to see history here.'
            })
            
    except Exception as e:
        print(f"Error in api_upload_history: {str(e)}")
        return JsonResponse({
            'uploads': [], 
            'message': 'Unable to load upload history. Please try again later.'
        })

@login_required
def api_recent_uploads(request):
    """API endpoint to get recent uploads (for backward compatibility)"""
    return api_upload_history(request)

@login_required
def api_data_preview(request, data_type):
    """API endpoint to preview data"""
    try:
        model_mapping = {
            'yield': YieldData,
            'bess': BESSData,
            'aoc': AOCData,
            'ice': ICEData,
            'map': MapData,
            'minamata': MinamataStringLossData,
            'actual_generation_daily': ActualGenerationDailyData,
            'expected_budget_daily': ExpectedBudgetDailyData,
            'budget_gii_daily': BudgetGIIDailyData,
            'actual_gii_daily': ActualGIIDailyData
        }
        
        model = model_mapping.get(data_type)
        if not model:
            return JsonResponse({'error': 'Invalid data type'}, status=400)
        
        # Get first 10 records
        records = model.objects.all()[:10]
        data = []
        for record in records:
            record_data = {}
            for field in model._meta.fields:
                value = getattr(record, field.name)
                if hasattr(value, 'isoformat'):
                    record_data[field.name] = value.isoformat()
                else:
                    record_data[field.name] = str(value) if value is not None else ''
            data.append(record_data)
        
        return JsonResponse({'data': data})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

@login_required
def api_delete_data(request):
    """API endpoint to delete data"""
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)
    
    try:
        data = json.loads(request.body)
        data_type = data.get('data_type')
        delete_option = data.get('delete_option')
        start_date = data.get('start_date')
        end_date = data.get('end_date')
        
        if not data_type:
            return JsonResponse({'success': False, 'error': 'Data type is required'})
        
        model_mapping = {
            'yield': YieldData,
            'bess': BESSData,
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
            'ic_approved_budget_daily': ICApprovedBudgetDailyData
        }
        
        model = model_mapping.get(data_type)
        if not model:
            return JsonResponse({'success': False, 'error': 'Invalid data type'})
        
        if delete_option == 'all':
            deleted_count = model.objects.all().delete()[0]
        elif delete_option == 'date_range':
            if not start_date or not end_date:
                return JsonResponse({'success': False, 'error': 'Start and end dates are required'})
            
            result = delete_data_by_date_range(data_type, start_date, end_date)
            if not result['success']:
                return JsonResponse({'success': False, 'error': result['error']})
            deleted_count = result['deleted_count']
        else:
            return JsonResponse({'success': False, 'error': 'Invalid delete option'})
        
        return JsonResponse({
            'success': True,
            'deleted_count': deleted_count,
            'message': f'Successfully deleted {deleted_count} records'
        })
        
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@login_required
def api_yield_data(request):
    """API endpoint for yield data"""
    try:
      
        
        # Get accessible sites for debugging
        accessible_sites = get_user_accessible_sites(request)
        
        
        # Check total yield data count
        total_yield_data = YieldData.objects.all()
        
        
        data = filter_data_by_user_sites(YieldData.objects.all(), 'assetno', request)
        
        
        # If no data after filtering, show some sample data for debugging
        if data.count() == 0:
            
            sample_data = YieldData.objects.all()[:5]
            for record in sample_data:
                print(f"  - Asset: {record.assetno}, Month: {record.month}, Country: {record.country}")
        
        yield_data = []
        for record in data:
            def safe_val(val):
                return "" if val is None or (isinstance(val, float) and math.isnan(val)) else val
            yield_data.append({
                'month': safe_val(record.month),
                'country': safe_val(record.country),
                'portfolio': safe_val(record.portfolio),
                'assetno': safe_val(record.assetno),
                'dc_capacity_mw': safe_val(record.dc_capacity_mw),
                'ic_approved_budget': safe_val(record.ic_approved_budget),
                'expected_budget': safe_val(record.expected_budget),
                'weather_loss_or_gain': safe_val(record.weather_loss_or_gain),
                'grid_curtailment': safe_val(record.grid_curtailment),
                'grid_outage': safe_val(record.grid_outage),
                'operation_budget': safe_val(record.operation_budget),
                'breakdown_loss': safe_val(record.breakdown_loss),
                'unclassified_loss': safe_val(record.unclassified_loss),
                'actual_generation': safe_val(record.actual_generation),
                'string failure': safe_val(record.string_failure),
                'inverter failure': safe_val(record.inverter_failure),
                'mv_failure': safe_val(record.mv_failure),
                'hv_failure': safe_val(record.hv_failure),
                'expected_pr': safe_val(record.expected_pr),
                'actual_pr': safe_val(record.actual_pr),
                'pr_gap': safe_val(record.pr_gap),
                'pr_gap_observation': safe_val(record.pr_gap_observation),
                'pr_gap_action_need_to_taken': safe_val(record.pr_gap_action_need_to_taken),
                'revenue_loss': safe_val(record.revenue_loss),
                'revenue_loss_observation': safe_val(record.revenue_loss_observation),
                'revenue_loss_action_need_to_taken': safe_val(record.revenue_loss_action_need_to_taken),
                'actual_irradiation': safe_val(record.actual_irradiation),
                'ac_capacity_mw': safe_val(record.ac_capacity_mw),
                'bess_capacity_mwh': safe_val(record.bess_capacity_mwh),
                'bess_generation_mwh': safe_val(record.bess_generation_mwh),
                'created_at': record.created_at.isoformat() if record.created_at else "",
                'updated_at': record.updated_at.isoformat() if record.updated_at else "",
                'remarks': '',
            })
        print(f"Yield API: Returning {len(yield_data)} records")
        return JsonResponse(yield_data, safe=False)
    except Exception as e:
        print(f"Yield API Error: {str(e)}")
        return JsonResponse({'error': str(e)}, status=500)

@login_required
def api_yield_data_sales(request):
    """API endpoint for yield data specifically for Sales page"""
    try:
        data = filter_data_by_user_sites(YieldData.objects.all(), 'assetno', request)
        yield_data = []
        for record in data:
            def safe_val(val):
                return "" if val is None or (isinstance(val, float) and math.isnan(val)) else val
            yield_data.append({
                'month': safe_val(record.month),
                'country': safe_val(record.country),
                'portfolio': safe_val(record.portfolio),
                'assetno': safe_val(record.assetno),
                'dc_capacity_mw': safe_val(record.dc_capacity_mw),
                'ic_approved_budget': safe_val(record.ic_approved_budget),
                'expected_budget': safe_val(record.expected_budget),
                'weather_loss_or_gain': safe_val(record.weather_loss_or_gain),
                'grid_curtailment': safe_val(record.grid_curtailment),
                'grid_outage': safe_val(record.grid_outage),
                'operation_budget': safe_val(record.operation_budget),
                'breakdown_loss': safe_val(record.breakdown_loss),
                'unclassified_loss': safe_val(record.unclassified_loss),
                'actual_generation': safe_val(record.actual_generation),
                'string_failure': safe_val(record.string_failure),
                'inverter_failure': safe_val(record.inverter_failure),
                'mv_failure': safe_val(record.mv_failure),
                'hv_failure': safe_val(record.hv_failure),
                'expected_pr': safe_val(record.expected_pr),
                'actual_pr': safe_val(record.actual_pr),
                'pr_gap': safe_val(record.pr_gap),
                'pr_gap_observation': safe_val(record.pr_gap_observation),
                'pr_gap_action_need_to_taken': safe_val(record.pr_gap_action_need_to_taken),
                'revenue_loss': safe_val(record.revenue_loss),
                'revenue_loss_observation': safe_val(record.revenue_loss_observation),
                'revenue_loss_action_need_to_taken': safe_val(record.revenue_loss_action_need_to_taken),
                'actual_irradiation': safe_val(record.actual_irradiation),
                'ac_capacity_mw': safe_val(record.ac_capacity_mw),
                'bess_capacity_mwh': safe_val(record.bess_capacity_mwh),
                'bess_generation_mwh': safe_val(record.bess_generation_mwh),
                'created_at': record.created_at.isoformat() if record.created_at else "",
                'updated_at': record.updated_at.isoformat() if record.updated_at else "",
                'remarks': '',
            })
        return JsonResponse({'data': yield_data})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

@login_required
def api_bess_data(request):
    """API endpoint for BESS data"""
    try:
        # Debug: Print user info
       
        
        # Check if user is admin
        try:
            user_profile = UserProfile.objects.get(user=request.user)
            is_admin = user_profile.role == 'admin'
          
        except UserProfile.DoesNotExist:
            is_admin = False
         
        
        # Get accessible sites for debugging
        accessible_sites = get_user_accessible_sites(request)
     
        
        # Check total BESS data count
        total_bess_data = BESSData.objects.all()
     
        
        # Show some sample BESS data asset numbers
        if total_bess_data.count() > 0:
            sample_assets = total_bess_data.values_list('asset_no', flat=True).distinct()[:10]
     
        
        # Show accessible asset numbers
        if accessible_sites and accessible_sites.exists():
            accessible_asset_numbers = list(accessible_sites.values_list('asset_number', flat=True))
         
        else:
            print(f"BESS API: No accessible sites found")
        
        # Use the filter_data_by_user_sites function for proper access control
        data = filter_data_by_user_sites(BESSData.objects.all(), 'asset_no', request)
        
        # Additional filtering for energy data (only show records with actual energy values)
        data = data.filter(
            pv_energy_kwh__isnull=False,
            charge_energy_kwh__isnull=False,
            discharge_energy_kwh__isnull=False,
            export_energy_kwh__isnull=False
        )

        bess_data = []
        for record in data:
            def safe_val(val):
                if val is None:
                    return None
                elif isinstance(val, float) and math.isnan(val):
                    return None
                else:
                    return val  # Return the original value
            

            bess_data.append({
                'id': record.id,
                'asset_no': safe_val(record.asset_no),
                'date': safe_val(record.date),
                'month': safe_val(record.month),
                'country': safe_val(record.country),
                'portfolio': safe_val(record.portfolio),
                'battery_capacity_mw': safe_val(record.battery_capacity_mw),
                'export_energy_kwh': safe_val(record.export_energy_kwh),
                'pv_energy_kwh': safe_val(record.pv_energy_kwh),
                'charge_energy_kwh': safe_val(record.charge_energy_kwh),
                'discharge_energy_kwh': safe_val(record.discharge_energy_kwh),
                'min_soc': safe_val(record.min_soc),
                'max_soc': safe_val(record.max_soc),
                'min_ess_temperature': safe_val(record.min_ess_temperature),
                'max_ess_temperature': safe_val(record.max_ess_temperature),
                'min_ess_humidity': safe_val(record.min_ess_humidity),
                'max_ess_humidity': safe_val(record.max_ess_humidity),
                'rte': safe_val(record.rte),
                'created_at': record.created_at.isoformat() if record.created_at else None,
                'updated_at': record.updated_at.isoformat() if record.updated_at else None,
            })
     
        return render(request, 'main/bess_v2.html', {
            'bess_data_json': json.dumps(bess_data)
        })
    except Exception as e:
        print(f"BESS API Error: {str(e)}")
        return render(request, 'main/bess_v2.html', {
            'bess_data_json': json.dumps([]),
            'error_message': str(e)
        })

@login_required
def api_aoc_data(request):
    """API endpoint for Areas of Concern data"""
    try:

        
        # Get accessible sites for debugging
        accessible_sites = get_user_accessible_sites(request)
   
        
        # Check total AOC data count
        total_aoc_data = AOCData.objects.all()

        
        data = filter_data_by_user_sites(AOCData.objects.all(), 'asset_no', request)

        
        aoc_data = []
        for record in data:
            def safe_val(val):
                return "" if val is None or (isinstance(val, float) and math.isnan(val)) else val
            aoc_data.append({
                'id': record.id,
                's_no': safe_val(record.s_no),
                'month': safe_val(record.month),
                'asset_no': safe_val(record.asset_no),
                'country': safe_val(record.country),
                'portfolio': safe_val(record.portfolio),
                'remarks': safe_val(record.remarks),
                'created_at': record.created_at.isoformat() if record.created_at else None,
                'updated_at': record.updated_at.isoformat() if record.updated_at else None,
            })

        return JsonResponse({'data': aoc_data})
    except Exception as e:
        print(f"AOC API Error: {str(e)}")
        return JsonResponse({'error': str(e)}, status=500)

@login_required
def api_ice_data(request):
    """API endpoint for IC Budget vs Expected data"""
    try:
        # ICE data doesn't have asset-specific filtering, but we can filter by portfolio
        # Get user's accessible portfolios
        try:
            user_profile = UserProfile.objects.get(user=request.user)
            if user_profile.role == 'admin':
                data = ICEData.objects.all()
            else:
                # Filter by accessible portfolios
                accessible_portfolios = user_profile.get_accessible_portfolios()
                if accessible_portfolios:
                    data = ICEData.objects.filter(portfolio__in=accessible_portfolios)
                else:
                    data = ICEData.objects.none()
        except UserProfile.DoesNotExist:
            data = ICEData.objects.none()

        ice_data = []
        for record in data:
            try:
                def safe_val(val):
                    return "" if val is None or (isinstance(val, float) and math.isnan(val)) else val
                ice_data.append({
                    'month': safe_val(record.month),
                    'portfolio': safe_val(record.portfolio),
                    'ic_approved': safe_val(record.ic_approved),
                    'expected': safe_val(record.expected),
                    'created_at': record.created_at.isoformat() if record.created_at else None,
                    'updated_at': record.updated_at.isoformat() if record.updated_at else None,
                })
            except Exception as record_error:
                print(f"ICE API: Error processing record {record.id}: {str(record_error)}")
                continue
        
        
        return JsonResponse({'data': ice_data})
    except Exception as e:
        print(f"ICE API Error: {str(e)}")
        import traceback
        print(f"ICE API Error traceback: {traceback.format_exc()}")
        return JsonResponse({'error': str(e)}, status=500)

@login_required
def api_map_data(request):
    """API endpoint for map data"""
    try:

        accessible_sites = get_user_accessible_sites(request)

        
        # Check total map data count
        total_map_data = MapData.objects.all()

 
        
        # Use the filter_data_by_user_sites function for proper access control
        data = filter_data_by_user_sites(MapData.objects.all(), 'asset_no', request)

        
        map_data = []
        for record in data:
            def safe_val(val):
                return "" if val is None or (isinstance(val, float) and math.isnan(val)) else val
            map_data.append({
                'id': record.id,
                'asset_no': safe_val(record.asset_no),
                'country': safe_val(record.country),
                'site_name': safe_val(record.site_name),
                'portfolio': safe_val(record.portfolio),
                'installation_type': safe_val(record.installation_type),
                'dc_capacity_mwp': safe_val(record.dc_capacity_mwp),
                'pcs_capacity': safe_val(record.pcs_capacity),
                'battery_capacity_mw': safe_val(record.battery_capacity_mw),
                'plant_type': safe_val(record.plant_type),
                'offtaker': safe_val(record.offtaker),
                'cod': safe_val(record.cod),
                'latitude': safe_val(record.latitude),
                'longitude': safe_val(record.longitude),
                'created_at': record.created_at.isoformat() if record.created_at else None,
                'updated_at': record.updated_at.isoformat() if record.updated_at else None,
            })
  
        return JsonResponse({'data': map_data})
    except Exception as e:
        print(f"Map Data API Error: {str(e)}")
        return JsonResponse({'error': str(e)}, status=500)    




@login_required
def api_minamata_string_loss_data(request):
    """API endpoint for Minamata string loss data"""
    try:
        # MinamataStringLossData doesn't have asset_no field, so return all data for now
        # TODO: Add asset_no field to MinamataStringLossData model if needed for filtering
        data = MinamataStringLossData.objects.all()

        string_loss_data = []
        for record in data:
            def safe_val(val):
                return "" if val is None or (isinstance(val, float) and math.isnan(val)) else val
            string_loss_data.append({
                'id': record.id,
                'month': safe_val(record.month),
                'no_of_strings_breakdown': safe_val(record.no_of_strings_breakdown),
                'no_of_strings_modules_damaged': safe_val(record.no_of_strings_modules_damaged),
                'designed_dc_capacity_mwh': safe_val(record.designed_dc_capacity_mwh),
                'breakdown_dc_capacity_mwh': safe_val(record.breakdown_dc_capacity_mwh),
                'operational_dc_capacity_mwh': safe_val(record.operational_dc_capacity_mwh),
                'budgeted_gen_mwh': safe_val(record.budgeted_gen_mwh),
                'actual_gen_mwh': safe_val(record.actual_gen_mwh),
                'loss_due_to_string_failure_mwh': safe_val(record.loss_due_to_string_failure_mwh),
                'loss_in_jpy': safe_val(record.loss_in_jpy),
                'loss_in_usd': safe_val(record.loss_in_usd),
                'created_at': record.created_at.isoformat() if record.created_at else None,
                'updated_at': record.updated_at.isoformat() if record.updated_at else None,
            })
        return JsonResponse({'data': string_loss_data})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

@login_required
def api_ic_approved_budget_daily(request):
    """API endpoint for daily IC approved budget data"""
    try:
        # Use the filter_data_by_user_sites function for proper access control
        data = filter_data_by_user_sites(YieldData.objects.all(), 'assetno', request)

        
        daily_data = []
        for record in data:
            def safe_val(val):
                return "" if val is None or (isinstance(val, float) and math.isnan(val)) else val
            daily_data.append({
                'id': record.id,
                'date': record.month,  # YieldData uses month field
                'asset_code': safe_val(record.assetno),  # YieldData uses assetno field
                'ic_approved_budget_kwh': safe_val(record.ic_approved_budget),
                'created_at': record.created_at.isoformat() if record.created_at else "",
                'updated_at': record.updated_at.isoformat() if record.updated_at else "",
            })
        return JsonResponse(daily_data, safe=False)
    except Exception as e:
        print(f"IC Approved Budget Daily API Error: {str(e)}")
        return JsonResponse({'error': str(e)}, status=500)
    

@csrf_exempt
@login_required
@require_http_methods(["POST"])
def api_upload_csv(request):
    """API endpoint for uploading CSV data with enhanced encoding support"""
    try:
        if 'file' not in request.FILES:
            return JsonResponse({'error': 'No file uploaded'}, status=400)
        
        file = request.FILES['file']
        file_name = file.name
        

        
        # Determine data type based on file name
        data_type = 'unknown'
        if 'yield' in file_name.lower():
            data_type = 'yield'
        elif 'bess' in file_name.lower():
            data_type = 'bess'
        elif 'aoc' in file_name.lower():
            data_type = 'aoc'
        elif 'ice' in file_name.lower():
            data_type = 'ice'
        elif 'map' in file_name.lower():
            data_type = 'map'
        elif 'minamata' in file_name.lower():
            data_type = 'minamata'
        elif 'icvsexvscur' in file_name.lower() or 'ic_budget' in file_name.lower():
            data_type = 'icvsexvscur'
        elif 'loss' in file_name.lower():
            data_type = 'loss_calculation'
        

        
        # Use the process_csv_upload function which has enhanced encoding detection
        result = process_csv_upload(
            csv_file=file,
            data_type=data_type,
            upload_mode='append',
            user=request.user
        )
        
        if result.get('success', False):
            # Build comprehensive success response
            response_data = {
                'success': True,
                'message': f'✅ Successfully processed {file_name}',
                'statistics': {
                    'records_imported': result.get('records_imported', 0),
                    'records_updated': result.get('records_updated', 0),
                    'records_skipped': result.get('records_skipped', 0),
                    'data_type': data_type
                }
            }
            
            # Add warnings if any
            if result.get('warnings'):
                response_data['warnings'] = result['warnings'][:5]  # Show first 5 warnings
                response_data['message'] += f' • {len(result["warnings"])} validation notes'
            
            return JsonResponse(response_data)
        else:
            # Build comprehensive error response
            error_response = {
                'error': result.get('error', 'Upload failed'),
                'data_type': data_type,
                'file_name': file_name
            }
            
            # Add validation details if available
            validation_details = result.get('validation_details')
            if validation_details:
                error_response['validation_details'] = {
                    'column_issues': validation_details.get('column_issues', [])[:5],
                    'data_issues': validation_details.get('data_issues', [])[:5],
                    'statistics': validation_details.get('statistics', {})
                }
            
            return JsonResponse(error_response, status=400)
        
    except Exception as e:
        print(f"Error in api_upload_csv: {e}")
        import traceback
        traceback.print_exc()
        return JsonResponse({'error': f'Upload failed: {str(e)}'}, status=500)

@csrf_exempt
@login_required
@require_http_methods(["POST"])
def api_analyze_file_encoding(request):
    """API endpoint for analyzing file encoding issues"""
    try:
        if 'file' not in request.FILES:
            return JsonResponse({'error': 'No file uploaded'}, status=400)
        
        file = request.FILES['file']
        analysis = analyze_file_encoding(file)
        
        return JsonResponse({
            'success': True,
            'analysis': analysis,
            'filename': file.name
        })
        
    except Exception as e:
        return JsonResponse({'error': f'Analysis failed: {str(e)}'}, status=500)
    
    
# ... existing code ...

# Removed duplicate data_upload_view function - using the one above with proper functionality

##############################################################################
##############################################################################
##############################################################################


# Time Series Dashboard Views
@feature_required('time_series_dashboard')
@login_required
def time_series_dashboard_view(request):
    """Time series dashboard view with data passed directly to template"""
    try:
        # Get user accessible sites
        accessible_sites = get_user_accessible_sites(request)
        
        if accessible_sites:
            # Filter by accessible sites - MapData uses asset_no, AssetList uses asset_number
            data = MapData.objects.filter(asset_no__in=accessible_sites)
        else:
            # If no sites assigned, return empty queryset
            data = MapData.objects.none()
        
        map_data = []
        for record in data:
            def safe_val(val):
                return "" if val is None or (isinstance(val, float) and math.isnan(val)) else val
            map_data.append({
                'id': record.id,
                'asset_no': safe_val(record.asset_no),
                'country': safe_val(record.country),
                'site_name': safe_val(record.site_name),
                'portfolio': safe_val(record.portfolio),
                'installation_type': safe_val(record.installation_type),
                'dc_capacity_mwp': safe_val(record.dc_capacity_mwp),
                'pcs_capacity': safe_val(record.pcs_capacity),
                'battery_capacity_mw': safe_val(record.battery_capacity_mw),
                'plant_type': safe_val(record.plant_type),
                'offtaker': safe_val(record.offtaker),
                'cod': safe_val(record.cod),
                'latitude': safe_val(record.latitude),
                'longitude': safe_val(record.longitude),
                'created_at': record.created_at.isoformat() if record.created_at else None,
                'updated_at': record.updated_at.isoformat() if record.updated_at else None,
            })
        
        return render(request, 'main/Energy_Monitoring.html', {
            'map_data_json': json.dumps(map_data)
        })
    except Exception as e:
        return render(request, 'main/Energy_Monitoring.html', {
            'map_data_json': json.dumps([]),
            'error_message': str(e)
        })

from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
# Import models with error handling for activity logging features
try:
    from .models import UserProfile, AssetList, ActiveUserSession, UserActivityLog, SecurityAlert
except ImportError:
    # Handle case where new models haven't been migrated yet
    from .models import UserProfile, AssetList
    ActiveUserSession = None
    UserActivityLog = None
    SecurityAlert = None
from django.db.models import Q, Count
from django.utils import timezone
from datetime import timedelta

@feature_required('user_management')
@login_required
@csrf_exempt
def user_management_view(request):
    try:
        user_profile = UserProfile.objects.get(user=request.user)
    except UserProfile.DoesNotExist:
        print("DEBUG: No user profile found")
    
    # Only admin can see all assets, others see only their assigned assets
    try:
        current_user_profile = UserProfile.objects.get(user=request.user)
        is_admin = current_user_profile.role == 'admin'
    except UserProfile.DoesNotExist:
        is_admin = False
    
    if is_admin:
        assets = AssetList.objects.all()
        countries = sorted(set(country.strip() for country in AssetList.objects.values_list('country', flat=True) if country))
        portfolios = sorted(set(portfolio.strip() for portfolio in AssetList.objects.values_list('portfolio', flat=True) if portfolio))
    else:
        try:
            user_profile = UserProfile.objects.get(user=request.user)
            accessible_sites = user_profile.get_accessible_sites()
            assets = accessible_sites
            countries = sorted(set(country.strip() for country in accessible_sites.values_list('country', flat=True) if country))
            portfolios = sorted(set(portfolio.strip() for portfolio in accessible_sites.values_list('portfolio', flat=True) if portfolio))
        except UserProfile.DoesNotExist:
            assets = AssetList.objects.none()
            countries = []
            portfolios = []
    
    # Get filter parameters
    search_query = request.GET.get('search', '').strip()
    role_filter = request.GET.get('role', '').strip()
    
    # Filter users based on search and role
    users_queryset = UserProfile.objects.select_related('user').all()
    
    if search_query:
        users_queryset = users_queryset.filter(
            Q(user__username__icontains=search_query) |
            Q(user__email__icontains=search_query) |
            Q(user__first_name__icontains=search_query) |
            Q(user__last_name__icontains=search_query)
        )
    
    if role_filter:
        users_queryset = users_queryset.filter(role=role_filter)
    
    users = users_queryset.order_by('-created_at')
    
    # Get activity statistics
    now = timezone.now()
    twenty_four_hours_ago = now - timedelta(hours=24)
    
    # Initialize default values
    active_users_count = 0
    activity_data = []
    security_alerts = 0
    suspicious_activities = []
    user_activity_summary = []
    
    # Only get activity data if models are available (migrated)
    if ActiveUserSession and UserActivityLog and SecurityAlert:
        # Active users (sessions active in last 30 minutes)
        thirty_minutes_ago = now - timedelta(minutes=30)
        active_users_count = ActiveUserSession.objects.filter(
            is_active=True,
            last_activity__gte=thirty_minutes_ago
        ).count()
        
        # Activity data for last 24 hours (hourly breakdown)
        # Get user's timezone from request header or use India timezone as default
        import pytz
        
        # Try to get timezone from request or default to India
        user_timezone_str = request.GET.get('timezone')
        if not user_timezone_str:
            # Default to India timezone since you mentioned Indian time
            user_timezone = pytz.timezone('Asia/Kolkata')
        else:
            try:
                user_timezone = pytz.timezone(user_timezone_str)
            except:
                user_timezone = pytz.timezone('Asia/Kolkata')
        
        # Calculate 24 hours ago in user's timezone
        now_local = timezone.now().astimezone(user_timezone)
        twenty_four_hours_ago_local = now_local - timedelta(hours=24)
        
        for i in range(24):
            # Calculate hour in user's local timezone
            hour_start_local = twenty_four_hours_ago_local + timedelta(hours=i)
            hour_end_local = hour_start_local + timedelta(hours=1)
            
            # Convert back to UTC for database query
            hour_start_utc = hour_start_local.astimezone(pytz.UTC)
            hour_end_utc = hour_end_local.astimezone(pytz.UTC)
            
            hour_activity = UserActivityLog.objects.filter(
                timestamp__gte=hour_start_utc,
                timestamp__lt=hour_end_utc
            ).count()
            
            activity_data.append({
                'hour': hour_start_local.strftime('%H:00'),
                'hour_full': hour_start_local.strftime('%Y-%m-%d %H:00'),
                'timestamp': hour_start_local.isoformat(),
                'count': hour_activity,
                'timezone': str(user_timezone)
            })
        
        # Security alerts summary
        security_alerts = SecurityAlert.objects.filter(
            created_at__gte=twenty_four_hours_ago,
            status='open'
        ).count()
        
        # Recent suspicious activities
        suspicious_activities = UserActivityLog.objects.filter(
            is_suspicious=True,
            timestamp__gte=twenty_four_hours_ago
        ).order_by('-timestamp')[:10]
        
        # User activity summary
        user_activity_summary = UserActivityLog.objects.filter(
            timestamp__gte=twenty_four_hours_ago
        ).values('action').annotate(count=Count('id')).order_by('-count')
    else:
        # Default empty activity data for 24 hours
        import pytz
        user_timezone = pytz.timezone('Asia/Kolkata')  # Default to India timezone
        
        now_local = timezone.now().astimezone(user_timezone)
        twenty_four_hours_ago_local = now_local - timedelta(hours=24)
        
        for i in range(24):
            hour_start_local = twenty_four_hours_ago_local + timedelta(hours=i)
            activity_data.append({
                'hour': hour_start_local.strftime('%H:00'),
                'hour_full': hour_start_local.strftime('%Y-%m-%d %H:00'),
                'timestamp': hour_start_local.isoformat(),
                'count': 0,
                'timezone': str(user_timezone)
            })
    
    error = None

    if request.method == 'POST':
        username = request.POST.get('username')
        email = request.POST.get('email')
        password = request.POST.get('password')
        role = request.POST.get('role')
        country_names = request.POST.getlist('countries')
        portfolio_names = request.POST.getlist('portfolios')
        site_ids = request.POST.getlist('sites')

        if not username or not email or not password or not role:
            error = "All fields are required."
        elif User.objects.filter(username=username).exists():
            error = "Username already exists."
        elif User.objects.filter(email=email).exists():
            error = "Email already exists."
        else:
            try:
                # Create user and profile in a transaction
                with transaction.atomic():
                    user = User.objects.create_user(username=username, email=email, password=password)
                    profile = UserProfile.objects.create(
                        user=user,
                        role=role,
                        created_by=request.user
                    )
                    
                    # Apply hierarchical access control logic using TextField approach
                    if site_ids and site_ids != ['']:
                        # If specific sites are selected, assign only those sites
                        profile.accessible_sites = ','.join(site_ids)
                        profile.accessible_countries = ''  # Clear country assignments
                        profile.accessible_portfolios = ''  # Clear portfolio assignments
                    elif portfolio_names and portfolio_names != ['']:
                        # If portfolios are selected, assign those portfolios
                        profile.accessible_portfolios = ','.join(portfolio_names)
                        profile.accessible_sites = ''  # Clear site assignments
                        profile.accessible_countries = ''  # Clear country assignments
                    elif country_names and country_names != ['']:
                        # If countries are selected, assign those countries
                        profile.accessible_countries = ','.join(country_names)
                        profile.accessible_sites = ''  # Clear site assignments
                        profile.accessible_portfolios = ''  # Clear portfolio assignments
                    else:
                        # No access assigned
                        profile.accessible_sites = ''
                        profile.accessible_countries = ''
                        profile.accessible_portfolios = ''
                    
                    profile.save()
                    
                    messages.success(request, f'User {username} created successfully!')
                return redirect('main:user_management')
            except Exception as e:
                error = f"Error creating user: {str(e)}"
                if user and user.pk:
                    user.delete()  # Cleanup if profile creation failed

    return render(request, 'main/user_management.html', {
        'users': users,
        'assets': assets,
        'countries': countries,
        'portfolios': portfolios,
        'error': error,
        'search_query': search_query,
        'role_filter': role_filter,
        'active_users_count': active_users_count,
        'activity_data': activity_data,
        'security_alerts_count': security_alerts,
        'suspicious_activities': suspicious_activities,
        'user_activity_summary': user_activity_summary,
        'role_choices': UserProfile.ROLE_CHOICES,
    })


@login_required
@role_required(allowed_roles=['admin'])  # ADMIN ONLY ACCESS
def user_activity_api(request):
    """API endpoint for user activity chart data - ADMIN ONLY"""
    # Check if models are available
    if not UserActivityLog:
        return JsonResponse({
            'success': False,
            'error': 'Activity logging not available. Please run migrations.'
        }, status=503)
        
    try:
        now = timezone.now()
        twenty_four_hours_ago = now - timedelta(hours=24)
        
        # Get activity data for last 24 hours (hourly breakdown)
        # Use India timezone for display
        import pytz
        user_timezone = pytz.timezone('Asia/Kolkata')  # India timezone
        
        # Calculate 24 hours ago in India timezone
        now_local = timezone.now().astimezone(user_timezone)
        twenty_four_hours_ago_local = now_local - timedelta(hours=24)
        
        activity_data = []
        for i in range(24):
            # Calculate hour in India timezone
            hour_start_local = twenty_four_hours_ago_local + timedelta(hours=i)
            hour_end_local = hour_start_local + timedelta(hours=1)
            
            # Convert back to UTC for database query
            hour_start_utc = hour_start_local.astimezone(pytz.UTC)
            hour_end_utc = hour_end_local.astimezone(pytz.UTC)
            
            hour_activity = UserActivityLog.objects.filter(
                timestamp__gte=hour_start_utc,
                timestamp__lt=hour_end_utc
            ).count()
            
            activity_data.append({
                'hour': hour_start_local.strftime('%H:00'),
                'hour_full': hour_start_local.strftime('%Y-%m-%d %H:00'),
                'timestamp': hour_start_local.isoformat(),
                'count': hour_activity,
                'timezone': 'Asia/Kolkata'
            })
        
        return JsonResponse({
            'success': True,
            'data': activity_data
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@login_required
@role_required(allowed_roles=['admin'])  # ADMIN ONLY ACCESS
def download_user_activity(request):
    """Download user activity data with filters - ADMIN ONLY"""
    # Check if models are available
    if not UserActivityLog:
        # Return a simple HTML page with error message instead of JSON
        html_content = '''
        <!DOCTYPE html>
        <html>
        <head><title>Download Error</title></head>
        <body>
            <h3>Activity logging not available</h3>
            <p>Please run migrations first.</p>
            <script>
                setTimeout(() => window.close(), 3000);
            </script>
        </body>
        </html>
        '''
        return HttpResponse(html_content, content_type='text/html')
    
    try:
        # Get filter parameters
        start_date = request.GET.get('start_date')
        end_date = request.GET.get('end_date')
        user_filter = request.GET.get('user')
        action_filter = request.GET.get('action')
        ip_filter = request.GET.get('ip')
        include_suspicious = request.GET.get('include_suspicious', 'false') == 'true'
        
        # Build queryset - start with all activity logs
        queryset = UserActivityLog.objects.select_related('user').all()
        
        # Apply date filters - default to current date if no dates specified
        import pytz
        user_timezone = pytz.timezone('Asia/Kolkata')  # India timezone
        
        if start_date:
            try:
                start_dt = timezone.datetime.strptime(start_date, '%Y-%m-%d')
                start_dt = timezone.make_aware(start_dt, user_timezone)
                queryset = queryset.filter(timestamp__gte=start_dt)
            except ValueError:
                pass
        else:
            # Default to current date if no start date specified
            today = timezone.now().astimezone(user_timezone).replace(hour=0, minute=0, second=0, microsecond=0)
            queryset = queryset.filter(timestamp__gte=today)
        
        if end_date:
            try:
                end_dt = timezone.datetime.strptime(end_date, '%Y-%m-%d')
                end_dt = timezone.make_aware(end_dt, user_timezone) + timedelta(days=1)  # Include full day
                queryset = queryset.filter(timestamp__lt=end_dt)
            except ValueError:
                pass
        else:
            # Default to end of current date if no end date specified
            if not start_date:  # Only apply if no custom start date
                tomorrow = timezone.now().astimezone(user_timezone).replace(hour=23, minute=59, second=59, microsecond=999999)
                queryset = queryset.filter(timestamp__lte=tomorrow)
        
        if user_filter:
            queryset = queryset.filter(user__username__icontains=user_filter)
        
        if action_filter:
            queryset = queryset.filter(action=action_filter)
        
        if ip_filter:
            queryset = queryset.filter(ip_address__icontains=ip_filter)
        
        if include_suspicious:
            queryset = queryset.filter(is_suspicious=True)
        
        # Order by timestamp
        queryset = queryset.order_by('-timestamp')
        
        # Use the same approach as site onboarding (WORKING METHOD)
        filename = f'user_activity_{timezone.now().strftime("%Y%m%d_%H%M%S")}.csv'
        response = HttpResponse(content_type='text/csv; charset=utf-8')
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        
        # Add UTF-8 BOM for better Excel compatibility
        response.write('\ufeff')
        
        writer = csv.writer(response)
        
        # Write header - ALL available columns from UserActivityLog model
        headers = [
            'ID',
            'Timestamp (IST)',
            'Timestamp (UTC)',
            'Username',
            'User ID',
            'User Email',
            'Session Key',
            'IP Address',
            'User Agent',
            'Action',
            'Action Display',
            'Resource (URL Path)',
            'HTTP Method',
            'Status Code',
            'Response Time (seconds)',
            'Response Size (bytes)',
            'Country',
            'City', 
            'Region',
            'Is Suspicious',
            'Risk Level',
            'Risk Level Display',
            'Security Flags',
            'Request Data (JSON)',
            'Request GET Parameters',
            'Request POST Parameters',
            'Content Type',
            'Content Length'
        ]
        writer.writerow(headers)
        
        # Convert to India timezone for timestamp display
        import pytz
        ist_timezone = pytz.timezone('Asia/Kolkata')
        
        # Write data - ALL available columns
        for log in queryset:
            # Convert timestamp to IST for display
            timestamp_ist = log.timestamp.astimezone(ist_timezone)
            
            # Extract request data details
            request_data = log.request_data or {}
            get_params = request_data.get('get_params', {})
            post_params = request_data.get('post_params', {})
            content_type = request_data.get('content_type', '')
            content_length = request_data.get('content_length', 0)
            
            row = [
                log.id,
                timestamp_ist.strftime('%Y-%m-%d %H:%M:%S'),
                log.timestamp.strftime('%Y-%m-%d %H:%M:%S'),
                log.user.username if log.user else 'Anonymous',
                log.user.id if log.user else '',
                log.user.email if log.user else '',
                log.session_key,
                log.ip_address,
                log.user_agent,
                log.action,
                log.get_action_display(),
                log.resource,
                log.method,
                log.status_code,
                round(log.response_time, 3),
                log.response_size,
                log.country,
                log.city,
                log.region,
                'Yes' if log.is_suspicious else 'No',
                log.risk_level,
                log.get_risk_level_display(),
                ', '.join(log.security_flags) if log.security_flags else '',
                json.dumps(log.request_data) if log.request_data else '',
                json.dumps(get_params) if get_params else '',
                json.dumps(post_params) if post_params else '',
                content_type,
                content_length
            ]
            writer.writerow(row)
        
        # Add headers to ensure download starts automatically
        response['Cache-Control'] = 'no-cache, no-store, must-revalidate'
        response['Pragma'] = 'no-cache'
        response['Expires'] = '0'
        
        return response
        
    except Exception as e:
        # Return HTML error page instead of JSON
        html_content = f'''
        <!DOCTYPE html>
        <html>
        <head><title>Download Error</title></head>
        <body>
            <h3>Download Error</h3>
            <p>Error: {str(e)}</p>
            <script>
                setTimeout(() => window.close(), 3000);
            </script>
        </body>
        </html>
        '''
        return HttpResponse(html_content, content_type='text/html')


@login_required
@role_required(allowed_roles=['admin'])  # ADMIN ONLY ACCESS
def download_user_activity_auto(request):
    """Auto-download page that starts download immediately"""
    # Check if models are available
    if not UserActivityLog:
        return HttpResponse('''
        <!DOCTYPE html>
        <html>
        <head><title>Download Error</title></head>
        <body>
            <h3>Activity logging not available</h3>
            <p>Please run migrations first.</p>
            <script>setTimeout(() => window.close(), 3000);</script>
        </body>
        </html>
        ''', content_type='text/html')
    
    try:
        # Get filter parameters
        start_date = request.GET.get('start_date')
        end_date = request.GET.get('end_date')
        user_filter = request.GET.get('user')
        action_filter = request.GET.get('action')
        ip_filter = request.GET.get('ip')
        include_suspicious = request.GET.get('include_suspicious', 'false') == 'true'
        
        # Build download URL for the actual CSV download
        params = []
        if start_date: params.append(f'start_date={start_date}')
        if end_date: params.append(f'end_date={end_date}')
        if user_filter: params.append(f'user={user_filter}')
        if action_filter: params.append(f'action={action_filter}')
        if ip_filter: params.append(f'ip={ip_filter}')
        if include_suspicious: params.append('include_suspicious=true')
        
        query_string = '&'.join(params)
        download_url = f"/download-user-activity/?{query_string}"
        
        # Return HTML page that automatically triggers download
        html_content = f'''
        <!DOCTYPE html>
        <html>
        <head>
            <title>Downloading User Activity Data...</title>
            <meta http-equiv="refresh" content="0; url={download_url}">
        </head>
        <body>
            <div style="text-align: center; padding: 50px; font-family: Arial, sans-serif;">
                <h3>🔄 Preparing Download...</h3>
                <p>Your download should start automatically.</p>
                <p><a href="{download_url}">Click here if download doesn't start</a></p>
                <script>
                    // Multiple methods to trigger download
                    setTimeout(() => {{
                        window.location.href = '{download_url}';
                    }}, 500);
                    
                    // Close window after download starts
                    setTimeout(() => {{
                        window.close();
                    }}, 3000);
                </script>
            </div>
        </body>
        </html>
        '''
        
        return HttpResponse(html_content, content_type='text/html')
        
    except Exception as e:
        return HttpResponse(f'''
        <!DOCTYPE html>
        <html>
        <head><title>Download Error</title></head>
        <body>
            <h3>Download Error</h3>
            <p>Error: {str(e)}</p>
            <script>setTimeout(() => window.close(), 3000);</script>
        </body>
        </html>
        ''', content_type='text/html')


@login_required
@role_required(allowed_roles=['admin'])  # ADMIN ONLY ACCESS
def security_alerts_view(request):
    """View for managing security alerts - ADMIN ONLY"""
    # Check if models are available
    if not SecurityAlert:
        messages.error(request, 'Security alerts not available. Please run migrations.')
        return redirect('main:user_management')
        
    try:
        # Get filter parameters
        status_filter = request.GET.get('status', 'open')
        severity_filter = request.GET.get('severity', '')
        alert_type_filter = request.GET.get('alert_type', '')
        
        # Build queryset
        queryset = SecurityAlert.objects.select_related('user', 'resolved_by').all()
        
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        
        if severity_filter:
            queryset = queryset.filter(severity=severity_filter)
        
        if alert_type_filter:
            queryset = queryset.filter(alert_type=alert_type_filter)
        
        alerts = queryset.order_by('-created_at')
        
        # Handle POST requests (resolve alerts)
        if request.method == 'POST':
            alert_id = request.POST.get('alert_id')
            action = request.POST.get('action')
            notes = request.POST.get('notes', '')
            
            try:
                alert = SecurityAlert.objects.get(id=alert_id)
                if action == 'resolve':
                    alert.status = 'resolved'
                    alert.resolved_by = request.user
                    alert.resolved_at = timezone.now()
                    alert.resolution_notes = notes
                    alert.save()
                    messages.success(request, 'Alert resolved successfully.')
                elif action == 'false_positive':
                    alert.status = 'false_positive'
                    alert.resolved_by = request.user
                    alert.resolved_at = timezone.now()
                    alert.resolution_notes = notes
                    alert.save()
                    messages.success(request, 'Alert marked as false positive.')
                
                return redirect('main:security_alerts')
                
            except SecurityAlert.DoesNotExist:
                messages.error(request, 'Alert not found.')
        
        return render(request, 'main/security_alerts.html', {
            'alerts': alerts,
            'status_filter': status_filter,
            'severity_filter': severity_filter,
            'alert_type_filter': alert_type_filter,
            'status_choices': SecurityAlert.STATUS_CHOICES,
            'severity_choices': SecurityAlert.SEVERITY_CHOICES,
            'alert_type_choices': SecurityAlert.ALERT_TYPE_CHOICES,
        })
        
    except Exception as e:
        messages.error(request, f'Error loading security alerts: {str(e)}')
        return redirect('main:user_management')


@feature_required('user_management')
@login_required
def download_page(request):
    """Simple download page that opens in new window to bypass iframe restrictions"""
    return render(request, 'main/download_page.html')

@login_required
def api_time_series_data(request):
    """API endpoint for time series data with enhanced filtering"""
    try:
        #from django.utils import timezone
        import pytz
        from datetime import datetime

        # Get filter parameters
        start_date = request.GET.get('start_date')
        end_date = request.GET.get('end_date')
        timezone_name = request.GET.get('timezone', 'UTC')
        #print(timezone_name,'***************')
        asset_code = request.GET.get('asset_code', '')
        device_id = request.GET.get('device', '')
        metric = request.GET.get('metric', '')

        # Build lookup dicts - filtered by user access
        accessible_sites = get_user_accessible_sites(request)
        if accessible_sites:
            device_lookup = {d.device_id: d for d in device_list.objects.filter(parent_code__in=accessible_sites)}
            asset_lookup = {a.asset_code: a for a in AssetList.objects.filter(asset_code__in=accessible_sites)}
        else:
            device_lookup = {}
            asset_lookup = {}

        # Validate required parameters
        if not start_date or not end_date or not metric:
            return JsonResponse({
                'success': False,
                'error': 'Missing required parameters: start_date, end_date, or metric'
            }, status=400)

        # Parse dates
        #st = dt_to_utc(start_date, timezone_name)
        # Parse datetime
        #print(start_date, type(start_date),timezone_name,type(timezone_name),timezone_name[0])
        naive_dt = datetime.strptime(start_date, "%Y-%m-%dT%H:%M")
        

        # Convert offset to timedelta
        sign = 1 if timezone_name[0] == '+' else -1
        
        hours, minutes = map(int, timezone_name[1:].split(":"))
        #print('asgdadhdafh546dafh345dfh6s4d')
        tz_off = sign * timedelta(hours=hours, minutes=minutes)
        #print('asgdadhdafh546dafh345dfh6s4d',tz_off)
        tz_offset = timezone(tz_off)
        # Make timezone-aware datetime
        st = naive_dt.replace(tzinfo=tz_offset)
        #print('asgdadhdafh546dafh345dfh6s4d',st)
        
       # ed = dt_to_utc(end_date, timezone_name)
               # Parse datetime
        naive_dt = datetime.strptime(end_date, "%Y-%m-%dT%H:%M")

        # Convert offset to timedelta
        sign = 1 if timezone_name[0] == '+' else -1
        hours, minutes = map(int, timezone_name[1:].split(":"))
        tz_offset = timezone(sign * timedelta(hours=hours, minutes=minutes))

        # Make timezone-aware datetime
        ed = naive_dt.replace(tzinfo=tz_offset)
        #print(start_date,'**********************',end_date)
        try:
            start_dt =  st   # datetime.fromisoformat(start_date.replace('Z', timezone_name))
            end_dt =  ed   #  datetime.fromisoformat(end_date.replace('Z', timezone_name))
        except ValueError:
            return JsonResponse({
                'success': False,
                'error': 'Invalid date format'
            }, status=400)

        # Get data from timeseries_data with proper filtering
        queryset = timeseries_data.objects.filter(
            ts__gte=start_dt,
            ts__lte=end_dt,
            metric=metric
        )
        #print(queryset)
        #print(start_dt,'------------',end_dt)
        #print(st,'*****************',ed)
        # Get all device IDs for the selected site
        if asset_code:
            # Get all device IDs for this site
            device_ids = list(device_list.objects.filter(parent_code=asset_code).values_list('device_id', flat=True))
        else:
            device_ids = list(device_list.objects.all().values_list('device_id', flat=True))

        # Filter timeseries_data by device_id(s)
        if device_id:
            # If a specific device is selected
            queryset = queryset.filter(device_id=device_id)
        else:
            # If "All" devices, filter by all device_ids for the site
            queryset = queryset.filter(device_id__in=device_ids)
        # Build data
        data = []
        for record in queryset:
            device = device_lookup.get(record.device_id)
            asset = asset_lookup.get(getattr(device, 'parent_code', None)) if device else None

            # Timezone conversion
           
            local_ts = str(record.ts)               
            local_timestamp = dt_to_utc(local_ts, timezone_name)
           # print(local_ts,'------------',local_timestamp)
                            
            try:
                
                data.append({
                    'timestamp': local_timestamp.isoformat(),
                    'value': float(record.value),
                    'device_id': record.device_id,
                    'device_name': getattr(device, 'device_name', record.device_id) if device else record.device_id,
                    'asset_code': getattr(device, 'parent_code', None) if device else None,
                    'site_name': asset.asset_name if asset else getattr(device, 'parent_code', None),
                    'metric': record.metric,
                    'timezone': asset.timezone if asset else None,
                })
            except ValueError:
                continue
        # Sort data by timestamp
        data.sort(key=lambda x: x['timestamp'])
        #print(data)
        return JsonResponse({
            'success': True,
            'data': data,
            'count': len(data)
        })

    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)

@login_required
def api_devices(request):
    """API endpoint to get available devices from Device model"""
    try:
        asset_code = request.GET.get('asset_code', '')
        #print(asset_code)
        # Get devices from Device model
        queryset = device_list.objects.all()
        
        # Filter by asset code if provided
        accessible_sites = get_user_accessible_sites(request)
        if accessible_sites:
            queryset = queryset.filter(parent_code__in=accessible_sites)
        
        devices = []
        for device in queryset:
            devices.append({
                'id': str(device.device_id),
                'name': device.device_name,
                'site_name': device.parent_code,
                'site_timezone': device.parent_code,
                'country': device.country
            })
        
        return JsonResponse(devices, safe=False)
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

@login_required
def api_metrics(request):
    """API endpoint to get available metrics (static list)"""
    try:
        metrics = [
            {
                'key': 'inv_ac_ap',
                'name': 'Active Power',
                'unit': 'kW',
                'category': 'Inverter'
            },
            {
                'key': 'string_current',
                'name': 'String Current',
                'unit': 'A',
                'category': 'Inverter'
            },
            {
                'key': 'string_deviation',
                'name': 'Deviation',
                'unit': '%',
                'category': 'Inverter'
            },
           
            # Add more metrics as needed
        ]
        return JsonResponse(metrics, safe=False)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

@login_required
def api_sites(request):
    """API endpoint to get available sites from AssetList"""
    try:
        sites = []
        
        # Get sites from AssetList model - filtered by user access
        accessible_sites = get_user_accessible_sites(request)
        if accessible_sites:
            assets = AssetList.objects.filter(asset_code__in=accessible_sites)
        else:
            assets = AssetList.objects.none()
        
        
        for asset in assets:
            sites.append({
                #'id': asset.id,
                'name': asset.asset_name,
                'code': asset.asset_code,
                'country': asset.country,
                'timezone': asset.timezone,
                'capacity': str(asset.capacity) if asset.capacity else None,
                #'device_count': asset.device_count
            })
        print(sites)
        return JsonResponse(sites, safe=False)
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

@login_required
def api_actual_generation_daily(request):
    """API endpoint for daily actual generation data"""
    try:
        # Get user accessible sites
        accessible_sites = get_user_accessible_sites(request)
        
        if accessible_sites:
            # Filter by accessible sites - ActualGenerationDailyData uses asset_code, AssetList uses asset_number
            # We need to map asset_number to asset_code by getting the asset_code values from AssetList
            asset_codes = AssetList.objects.filter(asset_number__in=accessible_sites).values_list('asset_code', flat=True)
            data = ActualGenerationDailyData.objects.filter(asset_code__in=asset_codes)
        else:
            # If no sites assigned, return all data for debugging (remove this in production)
            data = ActualGenerationDailyData.objects.all()
            
        daily_data = []
        for record in data:
            def safe_val(val):
                return "" if val is None or (isinstance(val, float) and math.isnan(val)) else val
            daily_data.append({
                'id': record.id,
                'date': record.date.isoformat() if record.date else "",
                'asset_code': safe_val(record.asset_code),
                'generation_kwh': safe_val(record.generation_kwh),
                'created_at': record.created_at.isoformat() if record.created_at else "",
                'updated_at': record.updated_at.isoformat() if record.updated_at else "",
            })
        return JsonResponse(daily_data, safe=False)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

@login_required
def api_expected_budget_daily(request):
    """API endpoint for daily expected budget data"""
    try:
        # Get user accessible sites
        accessible_sites = get_user_accessible_sites(request)
        
        if accessible_sites:
            # Filter by accessible sites - ExpectedBudgetDailyData uses asset_code, AssetList uses asset_number
            # We need to map asset_number to asset_code by getting the asset_code values from AssetList
            asset_codes = AssetList.objects.filter(asset_number__in=accessible_sites).values_list('asset_code', flat=True)
            data = ExpectedBudgetDailyData.objects.filter(asset_code__in=asset_codes)
        else:
            # If no sites assigned, return all data for debugging (remove this in production)
            data = ExpectedBudgetDailyData.objects.all()
        
        daily_data = []
        for record in data:
            def safe_val(val):
                return "" if val is None or (isinstance(val, float) and math.isnan(val)) else val
            daily_data.append({
                'id': record.id,
                'date': record.date.isoformat() if record.date else "",
                'asset_code': safe_val(record.asset_code),
                'expected_budget_kwh': safe_val(record.expected_budget_kwh),
                'created_at': record.created_at.isoformat() if record.created_at else "",
                'updated_at': record.updated_at.isoformat() if record.updated_at else "",
            })
        return JsonResponse(daily_data, safe=False)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

@login_required
def api_budget_gii_daily(request):
    """API endpoint for daily budget GII data"""
    try:
        # Get user accessible sites
        accessible_sites = get_user_accessible_sites(request)
        
        if accessible_sites:
            # Filter by accessible sites - BudgetGIIDailyData uses asset_code, AssetList uses asset_number
            # We need to map asset_number to asset_code by getting the asset_code values from AssetList
            asset_codes = AssetList.objects.filter(asset_number__in=accessible_sites).values_list('asset_code', flat=True)
            data = BudgetGIIDailyData.objects.filter(asset_code__in=asset_codes)
        else:
            # If no sites assigned, return all data for debugging (remove this in production)
            data = BudgetGIIDailyData.objects.all()
        
        daily_data = []
        for record in data:
            def safe_val(val):
                return "" if val is None or (isinstance(val, float) and math.isnan(val)) else val
            daily_data.append({
                'id': record.id,
                'date': record.date.isoformat() if record.date else "",
                'asset_code': safe_val(record.asset_code),
                'budget_gii_kwh': safe_val(record.budget_gii_kwh),
                'created_at': record.created_at.isoformat() if record.created_at else "",
                'updated_at': record.updated_at.isoformat() if record.updated_at else "",
            })
        return JsonResponse(daily_data, safe=False)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

@login_required
def api_actual_gii_daily(request):
    """API endpoint for daily actual GII data"""
    try:
        # Get user accessible sites
        accessible_sites = get_user_accessible_sites(request)
        
        if accessible_sites:
            # Filter by accessible sites - ActualGIIDailyData uses asset_code, AssetList uses asset_number
            # We need to map asset_number to asset_code by getting the asset_code values from AssetList
            asset_codes = AssetList.objects.filter(asset_number__in=accessible_sites).values_list('asset_code', flat=True)
            data = ActualGIIDailyData.objects.filter(asset_code__in=asset_codes)
        else:
            # If no sites assigned, return all data for debugging (remove this in production)
            data = ActualGIIDailyData.objects.all()
        
        daily_data = []
        for record in data:
            def safe_val(val):
                return "" if val is None or (isinstance(val, float) and math.isnan(val)) else val
            daily_data.append({
                'id': record.id,
                'date': record.date.isoformat() if record.date else "",
                'asset_code': safe_val(record.asset_code),
                'actual_gii_kwh': safe_val(record.actual_gii_kwh),
                'created_at': record.created_at.isoformat() if record.created_at else "",
                'updated_at': record.updated_at.isoformat() if record.updated_at else "",
            })
        return JsonResponse(daily_data, safe=False)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)
    



def send_password_reset_email(request, user):
    token = default_token_generator.make_token(user)
    uid = urlsafe_base64_encode(force_bytes(user.pk))
    reset_url = request.build_absolute_uri(
        reverse('accounts:password_reset_confirm', kwargs={'uidb64': uid, 'token': token})
    )
    subject = "Set your password"
    message = f"""Hi {user.username}, 

Your username: {user.username}

Please set your password using the following link:
{reset_url}

This link will expire after use.

After setting your password, use this link to login: www.peakpulse-dev.xyz

Best regards,
Peak Pulse Team"""
    try:
        print(subject, "\n" ,message,'\n', settings.DEFAULT_FROM_EMAIL,'\\n', [user.email])
        send_mail(subject, message, settings.DEFAULT_FROM_EMAIL, [user.email])
    except Exception as e:
        return JsonResponse({'error EMAIL NOT SENT': str(e)}, status=500)
    

def send_password_reset(request, user_id):
    if request.method == 'POST':
        user = get_object_or_404(User, pk=user_id)
        print(user,'********************')
        send_password_reset_email(request, user)
        messages.success(request, f"Password reset link sent to {user.email}.")
    return redirect('main:user_management')

@login_required
def test_hierarchical_access(request):
    """Test view to debug hierarchical access issues"""
    try:
        # Get user info
        user_profile = UserProfile.objects.get(user=request.user)
        
        # Get some sample data
        yield_sample = YieldData.objects.first()
        bess_sample = BESSData.objects.first()
        aoc_sample = AOCData.objects.first()
        map_sample = MapData.objects.first()
        asset_sample = AssetList.objects.first()
        
        # Get accessible sites
        accessible_sites = user_profile.get_accessible_sites()
        accessible_site_numbers = list(accessible_sites.values_list('asset_number', flat=True))
        
        # Check data counts
        total_yield = YieldData.objects.count()
        total_bess = BESSData.objects.count()
        total_aoc = AOCData.objects.count()
        total_map = MapData.objects.count()
        total_assets = AssetList.objects.count()
        
        # Check filtered counts
        filtered_yield = YieldData.objects.filter(assetno__in=accessible_site_numbers).count() if accessible_site_numbers else 0
        filtered_bess = BESSData.objects.filter(asset_no__in=accessible_site_numbers).count() if accessible_site_numbers else 0
        filtered_aoc = AOCData.objects.filter(asset_no__in=accessible_site_numbers).count() if accessible_site_numbers else 0
        filtered_map = MapData.objects.filter(asset_no__in=accessible_site_numbers).count() if accessible_site_numbers else 0
        
        context = {
            'user_role': user_profile.role,
            'accessible_site_numbers': accessible_site_numbers,
            'accessible_site_count': len(accessible_site_numbers),
            'total_yield': total_yield,
            'total_bess': total_bess,
            'total_aoc': total_aoc,
            'total_map': total_map,
            'total_assets': total_assets,
            'filtered_yield': filtered_yield,
            'filtered_bess': filtered_bess,
            'filtered_aoc': filtered_aoc,
            'filtered_map': filtered_map,
            'yield_sample_assetno': getattr(yield_sample, 'assetno', 'N/A') if yield_sample else 'N/A',
            'bess_sample_asset_no': getattr(bess_sample, 'asset_no', 'N/A') if bess_sample else 'N/A',
            'aoc_sample_asset_no': getattr(aoc_sample, 'asset_no', 'N/A') if aoc_sample else 'N/A',
            'map_sample_asset_no': getattr(map_sample, 'asset_no', 'N/A') if map_sample else 'N/A',
            'asset_sample_number': getattr(asset_sample, 'asset_number', 'N/A') if asset_sample else 'N/A',
        }
        
        return render(request, 'main/test_permissions.html', context)
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

@login_required
def debug_asset_codes(request):
    """Debug endpoint to check asset codes and user access"""
    try:
        user_profile = UserProfile.objects.get(user=request.user)
        
        # Get all assets
        all_assets = AssetList.objects.all()
        
        # Get user's accessible assets
        accessible_assets = user_profile.get_accessible_sites()
        
        # Check what countries are in the database
        all_countries = list(AssetList.objects.values_list('country', flat=True).distinct())
        
        # Check what countries the user has access to
        user_countries = []
        if user_profile.accessible_countries:
            user_countries = [c.strip() for c in user_profile.accessible_countries.split(',') if c.strip()]
        
        # Check field mapping consistency
        asset_codes = list(AssetList.objects.values_list('asset_code', flat=True)[:10])
        asset_numbers = list(AssetList.objects.values_list('asset_number', flat=True)[:10])
        
        # Check MapData asset numbers
        map_data_assets = list(MapData.objects.values_list('asset_no', flat=True).distinct()[:10])
        
        # Check YieldData asset numbers
        yield_data_assets = list(YieldData.objects.values_list('assetno', flat=True).distinct()[:10])
        
        # Check BESSData asset numbers
        bess_data_assets = list(BESSData.objects.values_list('asset_no', flat=True).distinct()[:10])
        
        # Debug info
        debug_info = {
            'user': request.user.username,
            'role': user_profile.role,
            'accessible_countries': user_profile.accessible_countries,
            'user_countries_parsed': user_countries,
            'accessible_portfolios': user_profile.accessible_portfolios,
            'accessible_sites': user_profile.accessible_sites,
            'total_assets': all_assets.count(),
            'accessible_assets_count': accessible_assets.count(),
            'all_countries_in_db': all_countries,
            'asset_codes_sample': asset_codes,
            'asset_numbers_sample': asset_numbers,
            'map_data_assets_sample': map_data_assets,
            'yield_data_assets_sample': yield_data_assets,
            'bess_data_assets_sample': bess_data_assets,
            'all_assets_sample': [
                {
                    'asset_code': asset.asset_code,
                    'asset_number': asset.asset_number,
                    'country': asset.country,
                    'portfolio': asset.portfolio,
                    'asset_name': asset.asset_name
                }
                for asset in all_assets[:10]
            ],
            'accessible_assets_sample': [
                {
                    'asset_code': asset.asset_code,
                    'asset_number': asset.asset_number,
                    'country': asset.country,
                    'portfolio': asset.portfolio,
                    'asset_name': asset.asset_name
                }
                for asset in accessible_assets[:10]
            ]
        }
        
        return JsonResponse(debug_info)
        
    except UserProfile.DoesNotExist:
        return JsonResponse({'error': 'No UserProfile found'})
    except Exception as e:
        return JsonResponse({'error': str(e)})

@feature_required('user_management')
@login_required
@csrf_exempt
def edit_user_access(request, user_id):
    """
    Edit user access permissions (countries, portfolios, and sites)
    Only admin users can access this view
    """
    try:
        current_user_profile = UserProfile.objects.get(user=request.user)
        is_admin = current_user_profile.role == 'admin'
    except UserProfile.DoesNotExist:
        is_admin = False
    
    if not is_admin:
        messages.error(request, 'Only admin users can edit user access.')
        return redirect('main:user_management')
    
    try:
        user_profile = UserProfile.objects.select_related('user').get(user_id=user_id)
    except UserProfile.DoesNotExist:
        messages.error(request, 'User not found.')
        return redirect('main:user_management')
    
    # Get all available assets, countries, and portfolios for admin
    assets = AssetList.objects.all()
    countries = sorted(set(country.strip() for country in AssetList.objects.values_list('country', flat=True) if country))
    portfolios = sorted(set(portfolio.strip() for portfolio in AssetList.objects.values_list('portfolio', flat=True) if portfolio))
    
    if request.method == 'POST':
        country_names = request.POST.getlist('countries')
        portfolio_names = request.POST.getlist('portfolios')
        site_ids = request.POST.getlist('sites')
        
        try:
            with transaction.atomic():
                # Apply hierarchical access control logic using TextField approach
                if site_ids and site_ids != ['']:
                    # If specific sites are selected, assign only those sites
                    user_profile.accessible_sites = ','.join(site_ids)
                    user_profile.accessible_countries = ''  # Clear country assignments
                    user_profile.accessible_portfolios = ''  # Clear portfolio assignments
                elif portfolio_names and portfolio_names != ['']:
                    # If portfolios are selected, assign those portfolios
                    user_profile.accessible_portfolios = ','.join(portfolio_names)
                    user_profile.accessible_sites = ''  # Clear site assignments
                    user_profile.accessible_countries = ''  # Clear country assignments
                elif country_names and country_names != ['']:
                    # If countries are selected, assign those countries
                    user_profile.accessible_countries = ','.join(country_names)
                    user_profile.accessible_sites = ''  # Clear site assignments
                    user_profile.accessible_portfolios = ''  # Clear portfolio assignments
                else:
                    # No access assigned - clear everything
                    user_profile.accessible_sites = ''
                    user_profile.accessible_countries = ''
                    user_profile.accessible_portfolios = ''
                
                user_profile.save()
                messages.success(request, f'Access permissions updated for {user_profile.user.username}!')
                return redirect('main:user_management')
        except Exception as e:
            messages.error(request, f'Error updating user access: {str(e)}')
    
    return render(request, 'main/edit_user_access.html', {
        'user_profile': user_profile,
        'assets': assets,
        'countries': countries,
        'portfolios': portfolios,
    })

@login_required
def api_loss_calculation_data(request):
    """API endpoint for loss calculation data"""
    try:
           
        # Use the filter_data_by_user_sites function for proper access control
        data = filter_data_by_user_sites(LossCalculationData.objects.all(), 'asset_no', request)
        
        loss_data = []
        for record in data:
            def safe_val(val):
                if val is None or (isinstance(val, float) and math.isnan(val)):
                    return None  # Return None instead of empty string
                elif isinstance(val, float) and val == 0.0:
                    return 0.0  # Keep 0.0 as a number
                else:
                    return val
            loss_data.append({
                'id': record.id,
                'l': safe_val(record.l),
                'month': safe_val(record.month),
                'start_date': safe_val(record.start_date),
                'start_time': safe_val(record.start_time),
                'end_date': safe_val(record.end_date),
                'end_time': safe_val(record.end_time),
                'asset_no': safe_val(record.asset_no),
                'country': safe_val(record.country),
                'portfolio': safe_val(record.portfolio),
                'dc_capacity': safe_val(record.dc_capacity),
                'site_name': safe_val(record.site_name),
                'category': safe_val(record.category),
                'subcategory': safe_val(record.subcategory),
                'breakdown_equipment': safe_val(record.breakdown_equipment),
                'bd_description': safe_val(record.bd_description),
                'action_to_be_taken': safe_val(record.action_to_be_taken),
                'status_of_bd': safe_val(record.status_of_bd),
                'breakdown_dc_capacity_kw': safe_val(record.breakdown_dc_capacity_kw),
                'irradiation_during_breakdown_kwh_m2': safe_val(record.irradiation_during_breakdown_kwh_m2),
                'budget_pr_percent': safe_val(record.budget_pr_percent),
                'generation_loss_kwh': safe_val(record.generation_loss_kwh),
                'ppa_rate_usd': safe_val(record.ppa_rate_usd),
                'revenue_loss_usd': safe_val(record.revenue_loss_usd),
                'severity': safe_val(record.severity),
                'created_at': record.created_at.isoformat() if record.created_at else "",
                'updated_at': record.updated_at.isoformat() if record.updated_at else "",
            })
        
        
        return JsonResponse(loss_data, safe=False)
    except Exception as e:
        print(f"Loss Calculation API Error: {str(e)}")
        return JsonResponse({'error': str(e)}, status=500)


@login_required
def api_asset_options(request):
    """API endpoint to get asset options for filtering (countries, portfolios, asset numbers)"""
    try:
        # Get user accessible asset numbers
        accessible_asset_numbers = get_user_accessible_asset_numbers(request)
        
        # Get all assets (or filter by user access if needed)
        if accessible_asset_numbers:
            assets = AssetList.objects.filter(asset_number__in=accessible_asset_numbers)
        else:
            assets = AssetList.objects.all()
        
        # Extract unique values
        countries = list(assets.values_list('country', flat=True).distinct().exclude(country__isnull=True).exclude(country=''))
        portfolios = list(assets.values_list('portfolio', flat=True).distinct().exclude(portfolio__isnull=True).exclude(portfolio=''))
        asset_numbers = list(assets.values_list('asset_number', flat=True).distinct().exclude(asset_number__isnull=True).exclude(asset_number=''))
        
        return JsonResponse({
            'success': True,
            'countries': countries,
            'portfolios': portfolios,
            'assetNumbers': asset_numbers
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@login_required
def api_kpi_v1_asset_options(request):
    """API endpoint specifically for KPI_v1 page to get asset options from real_time_kpi and main_yielddata tables"""
    try:
        # Get user accessible asset numbers
        accessible_asset_numbers = get_user_accessible_asset_numbers(request)
        
        # Get data from both tables
        if accessible_asset_numbers:
            # Get accessible asset codes for RealTimeKPI filtering
            accessible_assets = AssetList.objects.filter(asset_number__in=accessible_asset_numbers)
            accessible_asset_codes = [asset.asset_code for asset in accessible_assets]
            
            # Filter data from both tables
            real_time_data = RealTimeKPI.objects.filter(asset_code__in=accessible_asset_codes)
            yield_data = YieldData.objects.filter(assetno__in=accessible_asset_numbers)
        else:
            real_time_data = RealTimeKPI.objects.none()
            yield_data = YieldData.objects.none()
        
        # Get unique values for gauge filters from AssetList (since real_time_kpi country/portfolio fields may be empty)
        # Get asset codes that have real-time data
        realtime_asset_codes = list(real_time_data.values_list('asset_code', flat=True).distinct())
        
        # Get countries and portfolios from AssetList for assets that have real-time data
        if realtime_asset_codes:
            realtime_assets = AssetList.objects.filter(asset_code__in=realtime_asset_codes)
            realtime_countries = list(realtime_assets.values_list('country', flat=True).distinct().exclude(country__isnull=True).exclude(country=''))
            realtime_portfolios = list(realtime_assets.values_list('portfolio', flat=True).distinct().exclude(portfolio__isnull=True).exclude(portfolio=''))
        else:
            realtime_countries = []
            realtime_portfolios = []
        
        # Get unique values from main_yielddata table for chart filters  
        yielddata_countries = list(yield_data.values_list('country', flat=True).distinct().exclude(country__isnull=True).exclude(country=''))
        yielddata_portfolios = list(yield_data.values_list('portfolio', flat=True).distinct().exclude(portfolio__isnull=True).exclude(portfolio=''))
        
        # Get asset numbers from yield data (since that's what the asset dropdowns use)
        asset_numbers = list(yield_data.values_list('assetno', flat=True).distinct().exclude(assetno__isnull=True).exclude(assetno=''))
        
        # Sort the lists for better user experience
        realtime_countries.sort()
        realtime_portfolios.sort()
        yielddata_countries.sort()
        yielddata_portfolios.sort()
        asset_numbers.sort()
        
        return JsonResponse({
            'success': True,
            # For backward compatibility, return combined data as default
            'countries': sorted(list(set(realtime_countries + yielddata_countries))),
            'portfolios': sorted(list(set(realtime_portfolios + yielddata_portfolios))),
            'assetNumbers': asset_numbers,
            # Also return separate data sources
            'realtimeFilter': {
                'countries': realtime_countries,
                'portfolios': realtime_portfolios
            },
            'yielddataFilter': {
                'countries': yielddata_countries,
                'portfolios': yielddata_portfolios
            }
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


# Feedback Views

@login_required
def feedback_submit_view(request):
    """
    View for users to submit feedback.
    Accessible to all authenticated users.
    """
    if request.method == 'POST':
        form = FeedbackForm(request.POST, request.FILES)
        if form.is_valid():
            feedback = form.save(commit=False)
            feedback.user = request.user
            feedback.user_email = request.user.email
            feedback.save()
            
            # Handle multiple images
            images = request.FILES.getlist('images')
            for image in images:
                if image:  # Check if image is not empty
                    FeedbackImage.objects.create(feedback=feedback, image=image)
            
            messages.success(request, 'Thank you for your feedback! It has been submitted successfully.')
            
            # Check if request is from an iframe (modal)
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest' or 'iframe' in request.META.get('HTTP_REFERER', ''):
                return JsonResponse({
                    'status': 'success',
                    'message': 'Thank you for your feedback! It has been submitted successfully.',
                    'close_modal': True
                })
            else:
                return redirect('main:feedback_submit')
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = FeedbackForm()
    
    return render(request, 'main/feedback_submit.html', {'form': form})


# Site Onboarding Views - Admin Only
@role_required(allowed_roles=['admin'])
@login_required
def site_onboarding_view(request):
    """Site Onboarding main page for managing asset_list, device_list, and device_mapping"""
    return render(request, 'main/site_onboarding.html')

@login_required
def api_site_onboarding_debug(request):
    """Debug endpoint for site onboarding issues"""
    try:
        debug_info = {
            'user_authenticated': request.user.is_authenticated,
            'user_username': request.user.username if request.user.is_authenticated else 'Anonymous',
            'user_is_admin': request.user.is_staff if request.user.is_authenticated else False,
            'user_groups': [group.name for group in request.user.groups.all()] if request.user.is_authenticated else [],
            'request_method': request.method,
            'request_path': request.path,
            'request_params': dict(request.GET),
        }
        
        # Test database connection
        try:
            from .models import AssetList
            asset_count = AssetList.objects.count()
            debug_info['database_connection'] = 'OK'
            debug_info['asset_list_count'] = asset_count
        except Exception as db_error:
            debug_info['database_connection'] = 'ERROR'
            debug_info['database_error'] = str(db_error)
        
    
    except Exception as e:
        return JsonResponse({
            'status': 'debug_error',
            'error': str(e),
            'timestamp': timezone.now().isoformat()
        }, status=500)

@login_required
def api_budget_values_debug(request):
    """Debug endpoint specifically for budget_values upload issues"""
    try:
        debug_info = {
            'timestamp': timezone.now().isoformat(),
            'user': request.user.username if request.user.is_authenticated else 'Anonymous',
        }
        
        # Test database connection and table structure
        try:
            from .models import budget_values
            count = budget_values.objects.count()
            debug_info['database_status'] = 'OK'
            debug_info['budget_values_count'] = count
            
            # Get table structure
            model_fields = [field.name for field in budget_values._meta.fields]
            debug_info['model_fields'] = model_fields
            
            if count > 0:
                sample = budget_values.objects.first()
                debug_info['sample_record'] = {
                    'asset_code': sample.asset_code,
                    'month_str': sample.month_str,
                    'bd_production': float(sample.bd_production) if sample.bd_production else None
                }
            
        except Exception as db_error:
            debug_info['database_status'] = 'ERROR'
            debug_info['database_error'] = str(db_error)
            import traceback
            debug_info['database_traceback'] = traceback.format_exc()
        
        # Test validation functions
        try:
            import pandas as pd
            test_data = {
                'asset_code': ['TEST001'],
                'month_str': ['JAN'],
                'bd_production': [100.0]
            }
            test_df = pd.DataFrame(test_data)
            
            from .views import validate_budget_values_data, validate_csv_structure
            budget_validation = validate_budget_values_data(test_df)
            csv_validation = validate_csv_structure(test_df, 'budget_values')
            
            debug_info['validation_functions'] = {
                'budget_validation': budget_validation,
                'csv_validation': {
                    'valid': csv_validation[0],
                    'error': csv_validation[1],
                    'missing_fields': csv_validation[2],
                    'extra_fields': csv_validation[3]
                }
            }
            
        except Exception as validation_error:
            debug_info['validation_functions'] = 'ERROR'
            debug_info['validation_error'] = str(validation_error)
            import traceback
            debug_info['validation_traceback'] = traceback.format_exc()
        
        return JsonResponse({
            'status': 'budget_debug_info',
            'debug': debug_info
        })
        
    except Exception as e:
        return JsonResponse({
            'status': 'budget_debug_error',
            'error': str(e),
            'timestamp': timezone.now().isoformat()
        }, status=500)


@role_required(allowed_roles=['admin'])
@login_required
def api_asset_list_data(request):
    """API endpoint to get asset list data with pagination"""
    try:
        # Debug logging for production troubleshooting
        import logging
        logger = logging.getLogger(__name__)
        logger.info(f"Asset list API called by user: {request.user.username if request.user.is_authenticated else 'Anonymous'}")
        
        page = int(request.GET.get('page', 1))
        page_size = int(request.GET.get('page_size', 25))
        search = request.GET.get('search', '')
        
        logger.info(f"Asset list query params: page={page}, page_size={page_size}, search='{search}'")
        
        try:
            assets = AssetList.objects.all()
            logger.info(f"AssetList query successful, found {assets.count()} total assets")
        except Exception as db_error:
            logger.error(f"Database error in AssetList query: {str(db_error)}")
            return JsonResponse({
                'error': 'Database connection error',
                'details': str(db_error),
                'user': request.user.username if request.user.is_authenticated else 'Anonymous'
            }, status=500)
        
        if search:
            assets = assets.filter(
                models.Q(asset_code__icontains=search) |
                models.Q(asset_name__icontains=search) |
                models.Q(country__icontains=search) |
                models.Q(portfolio__icontains=search)
            )
        
        total_count = assets.count()
        
        # Pagination
        start = (page - 1) * page_size
        end = start + page_size
        assets_page = assets[start:end]
        
        data = []
        for asset in assets_page:
            try:
                asset_data = {
                    'asset_code': asset.asset_code,
                    'asset_name': asset.asset_name,
                    'capacity': float(asset.capacity) if asset.capacity else 0,
                    'address': asset.address,
                    'country': asset.country,
                    'latitude': float(asset.latitude) if asset.latitude else 0,
                    'longitude': float(asset.longitude) if asset.longitude else 0,
                    'contact_person': asset.contact_person,
                    'contact_method': asset.contact_method,
                    'grid_connection_date': asset.grid_connection_date.isoformat() if asset.grid_connection_date else '',
                    'asset_number': asset.asset_number,
                    'portfolio': getattr(asset, 'portfolio', ''),
                    'timezone': asset.timezone,
                    'asset_name_oem': getattr(asset, 'asset_name_oem', ''),
                    'cod': asset.cod.isoformat() if getattr(asset, 'cod', None) else '',
                    'operational_cod': asset.operational_cod.isoformat() if getattr(asset, 'operational_cod', None) else '',
                    'y1_degradation': float(asset.y1_degradation) if getattr(asset, 'y1_degradation', None) else None,
                    'anual_degradation': float(asset.anual_degradation) if getattr(asset, 'anual_degradation', None) else None,
                    'api_name': getattr(asset, 'api_name', '') or '',
                    'api_key': getattr(asset, 'api_key', '') or '',
                }
                data.append(asset_data)
            except Exception as asset_error:
                logger.error(f"Error processing asset {asset.asset_code}: {str(asset_error)}")
                # Add minimal asset data to prevent complete failure
                data.append({
                    'asset_code': asset.asset_code,
                    'asset_name': asset.asset_name,
                    'capacity': 0,
                    'address': getattr(asset, 'address', ''),
                    'country': getattr(asset, 'country', ''),
                    'latitude': 0,
                    'longitude': 0,
                    'contact_person': getattr(asset, 'contact_person', ''),
                    'contact_method': getattr(asset, 'contact_method', ''),
                    'grid_connection_date': '',
                    'asset_number': getattr(asset, 'asset_number', ''),
                    'portfolio': '',
                    'timezone': getattr(asset, 'timezone', ''),
                    'asset_name_oem': '',
                    'cod': '',
                    'operational_cod': '',
                    'y1_degradation': None,
                    'anual_degradation': None,
                    'api_name': '',
                    'api_key': '',
                })
        
        logger.info(f"Asset list API returning {len(data)} assets for page {page}")
        
        return JsonResponse({
            'data': data,
            'total': total_count,
            'page': page,
            'page_size': page_size,
            'total_pages': math.ceil(total_count / page_size)
        })
        
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Error in api_asset_list_data: {str(e)}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        
        return JsonResponse({
            'error': 'Internal server error',
            'details': str(e),
            'user': request.user.username if request.user.is_authenticated else 'Anonymous',
            'endpoint': 'api_asset_list_data'
        }, status=500)


@role_required(allowed_roles=['admin'])
@login_required
def api_device_list_data(request):
    """API endpoint to get device list data with pagination"""
    try:
        page = int(request.GET.get('page', 1))
        page_size = int(request.GET.get('page_size', 25))
        search = request.GET.get('search', '')
        
        devices = device_list.objects.all()
        
        if search:
            devices = devices.filter(
                models.Q(device_id__icontains=search) |
                models.Q(device_name__icontains=search) |
                models.Q(device_code__icontains=search) |
                models.Q(device_type__icontains=search) |
                models.Q(country__icontains=search)
            )
        
        total_count = devices.count()
        
        # Pagination
        start = (page - 1) * page_size
        end = start + page_size
        devices_page = devices[start:end]
        
        data = []
        for device in devices_page:
            data.append({
                'device_id': device.device_id,
                'device_name': device.device_name,
                'device_code': device.device_code,
                'device_type_id': device.device_type_id,
                'device_serial': device.device_serial,
                'device_model': device.device_model,
                'device_make': device.device_make,
                'latitude': float(device.latitude) if device.latitude else 0,
                'longitude': float(device.longitude) if device.longitude else 0,
                'optimizer_no': device.optimizer_no,
                'parent_code': device.parent_code,
                'device_type': device.device_type,
                'software_version': device.software_version,
                'country': device.country,
                'string_no': device.string_no,
                'connected_strings': device.connected_strings,
                'device_sub_group': device.device_sub_group,
                'device_source': device.device_source,
            })
        
        return JsonResponse({
            'data': data,
            'total': total_count,
            'page': page,
            'page_size': page_size,
            'total_pages': math.ceil(total_count / page_size)
        })
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@role_required(allowed_roles=['admin'])
@login_required
def api_device_mapping_data(request):
    """API endpoint to get device mapping data with pagination"""
    try:
        page = int(request.GET.get('page', 1))
        page_size = int(request.GET.get('page_size', 25))
        search = request.GET.get('search', '')
        
        # Check if device_mapping table exists
        try:
            mappings = device_mapping.objects.all()
        except Exception as db_error:
            print(f"Database error accessing device_mapping: {str(db_error)}")
            # Return empty result if table doesn't exist
            return JsonResponse({
                'data': [],
                'total': 0,
                'page': page,
                'page_size': page_size,
                'total_pages': 0,
                'warning': 'Device mapping table not found. Please ensure the table exists in the database.'
            })
        
        if search:
            mappings = mappings.filter(
                models.Q(asset_code__icontains=search) |
                models.Q(device_type__icontains=search) |
                models.Q(oem_tag__icontains=search) |
                models.Q(discription__icontains=search) |
                models.Q(metric__icontains=search)
            )
        
        total_count = mappings.count()
        
        # Pagination
        start = (page - 1) * page_size
        end = start + page_size
        mappings_page = mappings[start:end]
        
        data = []
        for mapping in mappings_page:
            data.append({
                'id': mapping.id,
                'asset_code': mapping.asset_code,
                'device_type': mapping.device_type,
                'oem_tag': mapping.oem_tag,
                'description': mapping.description,  # Use the property for proper spelling
                'data_type': mapping.data_type,
                'units': mapping.units,
                'metric': mapping.metric,
                'fault_code': mapping.fault_code or '',
                'module_no': mapping.module_no or '',
                'default_value': mapping.default_value or '',
            })
        
        return JsonResponse({
            'data': data,
            'total': total_count,
            'page': page,
            'page_size': page_size,
            'total_pages': math.ceil(total_count / page_size)
        })
        
    except Exception as e:
        print(f"Error in api_device_mapping_data: {str(e)}")
        import traceback
        traceback.print_exc()
        return JsonResponse({'error': str(e)}, status=500)


@role_required(allowed_roles=['admin'])
@login_required
def api_budget_values_data(request):
    """API endpoint to get budget values data with pagination"""
    try:
        page = int(request.GET.get('page', 1))
        page_size = int(request.GET.get('page_size', 25))
        search = request.GET.get('search', '')
        
        print(f"Budget values API called - page: {page}, page_size: {page_size}, search: '{search}'")
        
        budgets = budget_values.objects.all().order_by('asset_code', 'month_str')
        print(f"Total budget records found: {budgets.count()}")
        
        if search:
            budgets = budgets.filter(
                models.Q(asset_code__icontains=search) |
                models.Q(asset_number__icontains=search) |
                models.Q(month_str__icontains=search)
            )
        
        total_count = budgets.count()
        
        # Pagination
        start = (page - 1) * page_size
        end = start + page_size
        budgets_page = budgets[start:end]
        
        data = []
        for budget in budgets_page:
            data.append({
                'id': budget.id,
                'asset_number': budget.asset_number,
                'asset_code': budget.asset_code,
                'month_str': budget.month_str,
                'month_date': budget.month_date.isoformat() if budget.month_date else '',
                'bd_production': float(budget.bd_production) if budget.bd_production else 0,
                'bd_ghi': float(budget.bd_ghi) if budget.bd_ghi else 0,
                'bd_gti': float(budget.bd_gti) if budget.bd_gti else 0,
            })
        
        print(f"Returning {len(data)} budget records")
        print(f"Sample data: {data[:2] if data else 'No data'}")
        
        return JsonResponse({
            'data': data,
            'total': total_count,
            'page': page,
            'page_size': page_size,
            'total_pages': math.ceil(total_count / page_size)
        })
        
    except Exception as e:
        print(f"Error in api_budget_values_data: {str(e)}")
        import traceback
        traceback.print_exc()
        return JsonResponse({'error': str(e)}, status=500)


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

@role_required(allowed_roles=['admin'])
@login_required
def api_test_unicode(request):
    """Test Unicode handling for debugging Japanese character issues"""
    import logging
    logger = logging.getLogger(__name__)
    try:
        # Test data with Japanese characters
        test_data = {
            'japanese_text': 'サンプルテキスト',  # Sample text
            'address': '東京都港区芝公園1丁目2-3',  # Tokyo address
            'name': '山田太郎',  # Yamada Taro
            'company': 'ソーラーテック株式会社'  # SolarTech Co., Ltd.
        }
        
        results = {}
        
        # Test encoding/decoding
        for key, value in test_data.items():
            processed = ensure_unicode_string(value)
            results[key] = {
                'original': value,
                'processed': processed,
                'repr': repr(processed),
                'bytes_utf8': processed.encode('utf-8').hex(),
                'length': len(processed)
            }
        
        # Test database round trip
        from django.db import connection
        with connection.cursor() as cursor:
            # Test a simple insert/select with Japanese text
            test_table_query = """
                SELECT 'テスト' as test_text, 
                       '東京' as city,
                       'サンプル' as sample
            """
            cursor.execute(test_table_query)
            db_result = cursor.fetchone()
            
            results['database_test'] = {
                'test_text': db_result[0],
                'city': db_result[1], 
                'sample': db_result[2]
            }
        
        return JsonResponse({
            'success': True,
            'results': results,
            'message': 'Unicode test completed'
        })
        
    except Exception as e:
        logger.error(f"Error in Unicode test: {str(e)}")
        return JsonResponse({'error': str(e)}, status=500)

@role_required(allowed_roles=['admin'])
@login_required
def api_find_corrupted_data(request):
    """Find records with corrupted characters (question marks) in the database"""
    import logging
    logger = logging.getLogger(__name__)
    try:
        corrupted_records = {
            'asset_list': [],
            'device_list': [],
            'device_mapping': []
        }
        
        # Check AssetList for corrupted data
        for asset in AssetList.objects.all():
            corrupted_fields = []
            if '?' in str(asset.asset_name):
                corrupted_fields.append('asset_name')
            if '?' in str(asset.address):
                corrupted_fields.append('address')
            if '?' in str(asset.contact_person):
                corrupted_fields.append('contact_person')
            if '?' in str(asset.contact_method):
                corrupted_fields.append('contact_method')
            if '?' in str(asset.portfolio):
                corrupted_fields.append('portfolio')
            
            if corrupted_fields:
                corrupted_records['asset_list'].append({
                    'asset_code': asset.asset_code,
                    'corrupted_fields': corrupted_fields,
                    'asset_name': asset.asset_name
                })
        
        # Check device_list for corrupted data
        for device in device_list.objects.all():
            corrupted_fields = []
            if '?' in str(device.device_name):
                corrupted_fields.append('device_name')
            if '?' in str(device.device_make):
                corrupted_fields.append('device_make')
            if '?' in str(device.device_model):
                corrupted_fields.append('device_model')
            if '?' in str(device.device_type):
                corrupted_fields.append('device_type')
            if '?' in str(device.country):
                corrupted_fields.append('country')
            
            if corrupted_fields:
                corrupted_records['device_list'].append({
                    'device_id': device.device_id,
                    'corrupted_fields': corrupted_fields,
                    'device_name': device.device_name
                })
        
        # Check device_mapping for corrupted data
        for mapping in device_mapping.objects.all():
            corrupted_fields = []
            if '?' in str(mapping.device_type):
                corrupted_fields.append('device_type')
            if '?' in str(mapping.oem_tag):
                corrupted_fields.append('oem_tag')
            if '?' in str(mapping.discription):
                corrupted_fields.append('discription')
            if '?' in str(mapping.data_type):
                corrupted_fields.append('data_type')
            if '?' in str(mapping.units):
                corrupted_fields.append('units')
            if '?' in str(mapping.metric):
                corrupted_fields.append('metric')
            
            if corrupted_fields:
                corrupted_records['device_mapping'].append({
                    'id': mapping.id,
                    'corrupted_fields': corrupted_fields,
                    'device_type': mapping.device_type,
                    'oem_tag': mapping.oem_tag
                })
        
        # Count totals
        total_corrupted = (
            len(corrupted_records['asset_list']) + 
            len(corrupted_records['device_list']) + 
            len(corrupted_records['device_mapping'])
        )
        
        return JsonResponse({
            'success': True,
            'total_corrupted_records': total_corrupted,
            'corrupted_data': corrupted_records,
            'message': f'Found {total_corrupted} records with corrupted characters'
        })
        
    except Exception as e:
        logger.error(f"Error finding corrupted data: {str(e)}")
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
                'grid_connection_date', 'asset_number', 'timezone', 'asset_name_oem',
                'cod', 'operational_cod', 'portfolio', 'y1_degradation', 'anual_degradation',
                'api_name', 'api_key'
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
                'timezone': '+09:00',
                'asset_name_oem': 'OEM Solar Farm 001',
                'cod': '2023-01-15 10:30:00',
                'operational_cod': '2023-02-01 00:00:00',
                'portfolio': 'ポートフォリオA',  # Portfolio A in Japanese
                'y1_degradation': '2.5',
                'anual_degradation': '0.5',
                'api_name': 'sample_api',
                'api_key': 'sample_api_key_123'
            }]
        elif table_name == 'device_list':
            filename = 'device_list_template.csv'
            headers = [
                'device_id', 'device_name', 'device_code', 'device_type_id',
                'device_serial', 'device_model', 'device_make', 'latitude',
                'longitude', 'optimizer_no', 'parent_code', 'device_type',
                'software_version', 'country', 'string_no', 'connected_strings',
                'device_sub_group', 'device_source'
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
                'device_source': '手動'  # Manual in Japanese
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

def download_site_onboarding_data(request, table_name):
    """Download CSV data for asset_list, device_list, or device_mapping"""
    try:
        if table_name == 'asset_list':
            queryset = AssetList.objects.all()
            filename = 'asset_list_export.csv'
            headers = [
                'asset_code', 'asset_name', 'capacity', 'address', 'country',
                'latitude', 'longitude', 'contact_person', 'contact_method',
                'grid_connection_date', 'asset_number', 'timezone', 'asset_name_oem',
                'cod', 'operational_cod', 'portfolio', 'y1_degradation', 'anual_degradation',
                'api_name', 'api_key'
            ]
        elif table_name == 'device_list':
            queryset = device_list.objects.all()
            filename = 'device_list_export.csv'
            headers = [
                'device_id', 'device_name', 'device_code', 'device_type_id',
                'device_serial', 'device_model', 'device_make', 'latitude',
                'longitude', 'optimizer_no', 'parent_code', 'device_type',
                'software_version', 'country', 'string_no', 'connected_strings',
                'device_sub_group', 'device_source'
            ]
        elif table_name == 'device_mapping':
            queryset = device_mapping.objects.all()
            filename = 'device_mapping_export.csv'
            headers = [
                'id', 'asset_code', 'device_type', 'oem_tag', 'discription',
                'data_type', 'units', 'metric', 'fault_code', 'module_no',
                'default_value'
            ]
        elif table_name == 'budget_values':
            queryset = budget_values.objects.all().order_by('asset_code', 'month_str')
            filename = 'budget_values_export.csv'
            headers = [
                'id', 'asset_number', 'asset_code', 'month_str', 'month_date',
                'bd_production', 'bd_ghi', 'bd_gti'
            ]
        elif table_name == 'ic_budget':
            queryset = ic_budget.objects.all().order_by('asset_code', 'month_str')
            filename = 'ic_budget_export.csv'
            headers = [
                'id', 'asset_code', 'asset_number', 'month_str', 'month_date', 'ic_bd_production'
            ]
        else:
            return JsonResponse({'error': 'Invalid table name'}, status=400)
        
        response = HttpResponse(content_type='text/csv; charset=utf-8')
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        
        # Add UTF-8 BOM for better Excel compatibility
        response.write('\ufeff')
        
        writer = csv.writer(response)
        writer.writerow(headers)
        
        for obj in queryset:
            row = []
            for header in headers:
                value = getattr(obj, header, '')
                if value is None:
                    value = ''
                row.append(str(value))
            writer.writerow(row)
        
        return response
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@csrf_exempt
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
        
        if not table_name or table_name not in ['asset_list', 'device_list', 'device_mapping', 'budget_values', 'ic_budget']:
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
                            with connection.cursor() as cursor:
                                cursor.execute("""
                                    INSERT INTO asset_list (
                                        asset_code, asset_name, capacity, address, country,
                                        latitude, longitude, contact_person, contact_method,
                                        grid_connection_date, asset_number, timezone, asset_name_oem,
                                        cod, operational_cod, portfolio, y1_degradation, anual_degradation,
                                        api_name, api_key
                                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                                    ON CONFLICT (asset_code) DO UPDATE SET
                                        asset_name = EXCLUDED.asset_name,
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
                                        cod = EXCLUDED.cod,
                                        operational_cod = EXCLUDED.operational_cod,
                                        portfolio = EXCLUDED.portfolio,
                                        y1_degradation = EXCLUDED.y1_degradation,
                                        anual_degradation = EXCLUDED.anual_degradation,
                                        api_name = EXCLUDED.api_name,
                                        api_key = EXCLUDED.api_key
                                """, [
                                    ensure_unicode_string(row.get('asset_code', '')),
                                    ensure_unicode_string(row.get('asset_name', '')),
                                    float(row.get('capacity', 0)) if pd.notna(row.get('capacity')) else None,
                                    ensure_unicode_string(row.get('address', '')),
                                    ensure_unicode_string(row.get('country', '')),
                                    float(row.get('latitude', 0)) if pd.notna(row.get('latitude')) else None,
                                    float(row.get('longitude', 0)) if pd.notna(row.get('longitude')) else None,
                                    ensure_unicode_string(row.get('contact_person', '')),
                                    ensure_unicode_string(row.get('contact_method', '')),
                                    pd.to_datetime(row.get('grid_connection_date')) if pd.notna(row.get('grid_connection_date')) else None,
                                    ensure_unicode_string(row.get('asset_number', '')),
                                    ensure_unicode_string(row.get('timezone', '')),
                                    ensure_unicode_string(row.get('asset_name_oem', '')),
                                    pd.to_datetime(row.get('cod')) if pd.notna(row.get('cod')) else None,
                                    pd.to_datetime(row.get('operational_cod')) if pd.notna(row.get('operational_cod')) else None,
                                    ensure_unicode_string(row.get('portfolio', '')),
                                    float(row.get('y1_degradation')) if pd.notna(row.get('y1_degradation')) else None,
                                    float(row.get('anual_degradation')) if pd.notna(row.get('anual_degradation')) else None,
                                    ensure_unicode_string(row.get('api_name', '')),
                                    ensure_unicode_string(row.get('api_key', ''))
                                ])
                            success_count += 1
                        elif table_name == 'device_list':
                            # Use raw SQL to insert device data
                            from django.db import connection
                            with connection.cursor() as cursor:
                                cursor.execute("""
                                    INSERT INTO device_list (
                                        device_id, device_name, device_code, device_type_id,
                                        device_serial, device_model, device_make, latitude,
                                        longitude, optimizer_no, parent_code, device_type,
                                        software_version, country, string_no, connected_strings,
                                    device_sub_group, device_source
                                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
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
                                    device_source = EXCLUDED.device_source
                            """, [
                                ensure_unicode_string(row.get('device_id', '')),
                                ensure_unicode_string(row.get('device_name', '')),
                                ensure_unicode_string(row.get('device_code', '')),
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
                                ensure_unicode_string(row.get('device_source', ''))
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
                                    optional_fields = {
                                        'discription': row.get('discription', row.get('description', '')),
                                        'data_type': row.get('data_type', ''),
                                        'units': row.get('units', ''),
                                        'fault_code': row.get('fault_code', ''),
                                        'module_no': row.get('module_no', ''),
                                        'default_value': row.get('default_value', '')
                                    }
                                    
                                    for field_name, field_value in optional_fields.items():
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
                                    optional_fields = {
                                        'discription': row.get('discription', row.get('description', '')),
                                        'data_type': row.get('data_type', ''),
                                        'units': row.get('units', ''),
                                        'fault_code': row.get('fault_code', ''),
                                        'module_no': row.get('module_no', ''),
                                        'default_value': row.get('default_value', '')
                                    }
                                    
                                    for field_name, field_value in optional_fields.items():
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
                                
                                print(f"    IC Budget processing: {asset_code} - {month_str} - Production: {ic_bd_production}")
                                print(f"    Raw data: asset_number='{asset_number}', month_date='{month_date}', ic_bd_production_raw='{ic_bd_production_raw}'")
                                
                                cursor.execute("""
                                    SELECT id FROM ic_budget 
                                    WHERE asset_code = %s AND month_str = %s
                                """, [asset_code, month_str])
                                
                                existing_record = cursor.fetchone()
                                
                                if existing_record:
                                    # Update existing record
                                    ic_budget_id = existing_record[0]
                                    print(f"    Updating existing IC budget record ID: {ic_budget_id}")
                                    cursor.execute("""
                                        UPDATE ic_budget SET
                                            asset_number = %s,
                                            month_date = %s,
                                            ic_bd_production = %s
                                        WHERE id = %s
                                    """, [
                                        asset_number,
                                        month_date,
                                        ic_bd_production,
                                        ic_budget_id
                                    ])
                                    print(f"    Updated IC budget record with production: {ic_bd_production}")
                                else:
                                    # Insert new record
                                    print(f"    Inserting new IC budget record")
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
                                
                                # Verify the data was saved correctly
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


# CRUD API endpoints for Site Onboarding

@role_required(allowed_roles=['admin'])
@login_required
@csrf_exempt
def api_update_asset_list(request):
    """API endpoint to update asset list record"""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            asset_code = data.get('asset_code')
            
            if not asset_code:
                return JsonResponse({'error': 'Asset code is required'}, status=400)
            
            # Use raw SQL to update unmanaged table
            from django.db import connection
            
            with connection.cursor() as cursor:
                # Handle datetime formatting
                def parse_datetime(date_str):
                    if date_str:
                        try:
                            from datetime import datetime
                            return datetime.fromisoformat(date_str.replace('Z', '+00:00'))
                        except:
                            return None
                    return None
                
                grid_connection_date = parse_datetime(data.get('grid_connection_date'))
                cod_date = parse_datetime(data.get('cod'))
                operational_cod_date = parse_datetime(data.get('operational_cod'))
                
                # Build dynamic update query based on provided fields
                update_fields = []
                values = []
                
                field_mappings = {
                    'asset_name': data.get('asset_name'),
                    'capacity': float(data.get('capacity', 0)) if data.get('capacity') else None,
                    'address': data.get('address', ''),
                    'country': data.get('country'),
                    'latitude': float(data.get('latitude', 0)) if data.get('latitude') else None,
                    'longitude': float(data.get('longitude', 0)) if data.get('longitude') else None,
                    'contact_person': data.get('contact_person', ''),
                    'contact_method': data.get('contact_method', ''),
                    'grid_connection_date': grid_connection_date,
                    'asset_number': data.get('asset_number', ''),
                    'timezone': data.get('timezone', ''),
                    'asset_name_oem': data.get('asset_name_oem', ''),
                    'cod': cod_date,
                    'operational_cod': operational_cod_date,
                    'portfolio': data.get('portfolio'),
                    'y1_degradation': float(data.get('y1_degradation')) if data.get('y1_degradation') else None,
                    'anual_degradation': float(data.get('anual_degradation')) if data.get('anual_degradation') else None,
                    'api_name': data.get('api_name', ''),
                    'api_key': data.get('api_key', '')
                }
                
                for field, value in field_mappings.items():
                    if field in data:  # Only update fields that were provided
                        update_fields.append(f"{field} = %s")
                        values.append(value)
                
                if update_fields:
                    values.append(asset_code)  # For WHERE clause
                    cursor.execute(f"""
                        UPDATE asset_list 
                        SET {', '.join(update_fields)}
                        WHERE asset_code = %s
                    """, values)
            
            return JsonResponse({
                'success': True,
                'message': 'Asset updated successfully!'
            })
            
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)
    
    return JsonResponse({'error': 'Only POST method allowed'}, status=405)


@role_required(allowed_roles=['admin'])
@login_required
@csrf_exempt
def api_create_asset_list(request):
    """API endpoint to create new asset list record"""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            
            # Validate required fields
            required_fields = ['asset_code', 'asset_name', 'country', 'portfolio']
            for field in required_fields:
                if not data.get(field):
                    return JsonResponse({'error': f'{field} is required'}, status=400)
            
            # Use raw SQL to insert into unmanaged table
            from django.db import connection
            
            with connection.cursor() as cursor:
                # Handle datetime formatting
                def parse_datetime(date_str):
                    if date_str:
                        try:
                            from datetime import datetime
                            return datetime.fromisoformat(date_str.replace('Z', '+00:00'))
                        except:
                            return None
                    return None
                
                grid_connection_date = parse_datetime(data.get('grid_connection_date'))
                cod_date = parse_datetime(data.get('cod'))
                operational_cod_date = parse_datetime(data.get('operational_cod'))
                
                # Insert into asset_list table
                cursor.execute("""
                    INSERT INTO asset_list (
                        asset_code, asset_name, capacity, address, country,
                        latitude, longitude, contact_person, contact_method,
                        grid_connection_date, asset_number, timezone, asset_name_oem,
                        cod, operational_cod, portfolio, y1_degradation, anual_degradation,
                        api_name, api_key
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """, [
                    data.get('asset_code'),
                    data.get('asset_name'),
                    float(data.get('capacity', 0)) if data.get('capacity') else None,
                    data.get('address', ''),
                    data.get('country'),
                    float(data.get('latitude', 0)) if data.get('latitude') else None,
                    float(data.get('longitude', 0)) if data.get('longitude') else None,
                    data.get('contact_person', ''),
                    data.get('contact_method', ''),
                    grid_connection_date,
                    data.get('asset_number', ''),
                    data.get('timezone', ''),
                    data.get('asset_name_oem', ''),
                    cod_date,
                    operational_cod_date,
                    data.get('portfolio'),
                    float(data.get('y1_degradation')) if data.get('y1_degradation') else None,
                    float(data.get('anual_degradation')) if data.get('anual_degradation') else None,
                    data.get('api_name', ''),
                    data.get('api_key', '')
                ])
            
            return JsonResponse({
                'success': True,
                'message': 'Asset created successfully!'
            })
            
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)
    
    return JsonResponse({'error': 'Only POST method allowed'}, status=405)


@role_required(allowed_roles=['admin'])
@login_required
def api_get_unique_api_names(request):
    """API endpoint to get unique API names for suggestions"""
    try:
        # Get unique API names that are not null or empty
        unique_names = AssetList.objects.exclude(
            api_name__isnull=True
        ).exclude(
            api_name__exact=''
        ).values_list('api_name', flat=True).distinct().order_by('api_name')
        
        return JsonResponse({
            'success': True,
            'api_names': list(unique_names)
        })
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@role_required(allowed_roles=['admin'])
@login_required
@csrf_exempt
def api_delete_asset_list(request, asset_code):
    """API endpoint to delete asset list record"""
    if request.method == 'DELETE':
        try:
            # Check if user is superuser
            if not request.user.is_superuser:
                # Log unauthorized delete attempt for security
                import logging
                logger = logging.getLogger(__name__)
                logger.warning(f"Unauthorized delete attempt by user {request.user.username} (ID: {request.user.id}) for asset {asset_code}")
                return JsonResponse({'error': 'Only superusers can delete records'}, status=403)
            
            # Use raw SQL to delete from unmanaged table
            from django.db import connection
            
            with connection.cursor() as cursor:
                cursor.execute("DELETE FROM asset_list WHERE asset_code = %s", [asset_code])
                
            # Log successful delete for audit trail
            import logging
            logger = logging.getLogger(__name__)
            logger.info(f"Asset {asset_code} deleted by superuser {request.user.username} (ID: {request.user.id})")
                
            return JsonResponse({
                'success': True,
                'message': 'Asset deleted successfully!'
            })
            
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)
    
    return JsonResponse({'error': 'Only DELETE method allowed'}, status=405)


@role_required(allowed_roles=['admin'])
@login_required
@csrf_exempt
def api_update_device_list(request):
    """API endpoint to update device list record"""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            device_id = data.get('device_id')
            
            if not device_id:
                return JsonResponse({'error': 'Device ID is required'}, status=400)
            
            # Use raw SQL to update unmanaged table
            from django.db import connection
            
            with connection.cursor() as cursor:
                # Build dynamic update query based on provided fields
                update_fields = []
                values = []
                
                field_mappings = {
                    'device_name': data.get('device_name'),
                    'device_code': data.get('device_code', ''),
                    'device_type_id': data.get('device_type_id', ''),
                    'device_serial': data.get('device_serial', ''),
                    'device_model': data.get('device_model', ''),
                    'device_make': data.get('device_make', ''),
                    'latitude': float(data.get('latitude', 0)) if data.get('latitude') else 0,
                    'longitude': float(data.get('longitude', 0)) if data.get('longitude') else 0,
                    'optimizer_no': int(data.get('optimizer_no', 0)) if data.get('optimizer_no') else 0,
                    'parent_code': data.get('parent_code', ''),
                    'device_type': data.get('device_type'),
                    'software_version': data.get('software_version', ''),
                    'country': data.get('country'),
                    'string_no': data.get('string_no', ''),
                    'connected_strings': data.get('connected_strings', ''),
                    'device_sub_group': data.get('device_sub_group', ''),
                    'device_source': data.get('device_source', '')
                }
                
                for field, value in field_mappings.items():
                    if field in data:  # Only update fields that were provided
                        update_fields.append(f"{field} = %s")
                        values.append(value)
                
                if update_fields:
                    values.append(device_id)  # For WHERE clause
                    cursor.execute(f"""
                        UPDATE device_list 
                        SET {', '.join(update_fields)}
                        WHERE device_id = %s
                    """, values)
            
            return JsonResponse({
                'success': True,
                'message': 'Device updated successfully!'
            })
            
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)
    
    return JsonResponse({'error': 'Only POST method allowed'}, status=405)


@role_required(allowed_roles=['admin'])
@login_required
@csrf_exempt
def api_create_device_list(request):
    """API endpoint to create new device list record"""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            
            # Validate required fields
            required_fields = ['device_id', 'device_name', 'device_type', 'country']
            for field in required_fields:
                if not data.get(field):
                    return JsonResponse({'error': f'{field} is required'}, status=400)
            
            # Use raw SQL to insert into unmanaged table
            from django.db import connection
            
            with connection.cursor() as cursor:
                cursor.execute("""
                    INSERT INTO device_list (
                        device_id, device_name, device_code, device_type_id,
                        device_serial, device_model, device_make, latitude,
                        longitude, optimizer_no, parent_code, device_type,
                        software_version, country, string_no, connected_strings,
                        device_sub_group, device_source
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """, [
                    data.get('device_id'),
                    data.get('device_name'),
                    data.get('device_code', ''),
                    data.get('device_type_id', ''),
                    data.get('device_serial', ''),
                    data.get('device_model', ''),
                    data.get('device_make', ''),
                    float(data.get('latitude', 0)) if data.get('latitude') else 0,
                    float(data.get('longitude', 0)) if data.get('longitude') else 0,
                    int(data.get('optimizer_no', 0)) if data.get('optimizer_no') else 0,
                    data.get('parent_code', ''),
                    data.get('device_type'),
                    data.get('software_version', ''),
                    data.get('country'),
                    data.get('string_no', ''),
                    data.get('connected_strings', ''),
                    data.get('device_sub_group', ''),
                    data.get('device_source', '')
                ])
            
            return JsonResponse({
                'success': True,
                'message': 'Device created successfully!'
            })
            
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)
    
    return JsonResponse({'error': 'Only POST method allowed'}, status=405)


@role_required(allowed_roles=['admin'])
@login_required
@csrf_exempt
def api_delete_device_list(request, device_id):
    """API endpoint to delete device list record"""
    if request.method == 'DELETE':
        try:
            # Check if user is superuser
            if not request.user.is_superuser:
                # Log unauthorized delete attempt for security
                import logging
                logger = logging.getLogger(__name__)
                logger.warning(f"Unauthorized delete attempt by user {request.user.username} (ID: {request.user.id}) for device {device_id}")
                return JsonResponse({'error': 'Only superusers can delete records'}, status=403)
            
            # Use raw SQL to delete from unmanaged table
            from django.db import connection
            
            with connection.cursor() as cursor:
                cursor.execute("DELETE FROM device_list WHERE device_id = %s", [device_id])
                
            # Log successful delete for audit trail
            import logging
            logger = logging.getLogger(__name__)
            logger.info(f"Device {device_id} deleted by superuser {request.user.username} (ID: {request.user.id})")
                
            return JsonResponse({
                'success': True,
                'message': 'Device deleted successfully!'
            })
            
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)
    
    return JsonResponse({'error': 'Only DELETE method allowed'}, status=405)


@role_required(allowed_roles=['admin'])
@login_required
@csrf_exempt
def api_update_device_mapping(request):
    """API endpoint to update device mapping record"""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            mapping_id = data.get('id')
            
            if not mapping_id:
                return JsonResponse({'error': 'Mapping ID is required'}, status=400)
            
            # Use raw SQL to update unmanaged table
            from django.db import connection
            
            with connection.cursor() as cursor:
                # Build dynamic update query based on provided fields
                update_fields = []
                values = []
                
                field_mappings = {
                    'asset_code': ensure_unicode_string(data.get('asset_code')),
                    'device_type': ensure_unicode_string(data.get('device_type')),
                    'oem_tag': ensure_unicode_string(data.get('oem_tag')),
                    'discription': ensure_unicode_string(data.get('description', '')),  # Use 'description' from frontend but save as 'discription'
                    'data_type': ensure_unicode_string(data.get('data_type')),
                    'units': ensure_unicode_string(data.get('units')),
                    'metric': ensure_unicode_string(data.get('metric')),
                    'fault_code': ensure_unicode_string(data.get('fault_code', '')),
                    'module_no': ensure_unicode_string(data.get('module_no', '')),
                    'default_value': ensure_unicode_string(data.get('default_value', ''))
                }
                
                for field, value in field_mappings.items():
                    if field.replace('discription', 'description') in data:  # Check if field was provided (handle discription mapping)
                        update_fields.append(f"{field} = %s")
                        values.append(value)
                
                if update_fields:
                    values.append(mapping_id)  # For WHERE clause
                    cursor.execute(f"""
                        UPDATE device_mapping 
                        SET {', '.join(update_fields)}
                        WHERE id = %s
                    """, values)
            
            return JsonResponse({
                'success': True,
                'message': 'Device mapping updated successfully!'
            })
            
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)
    
    return JsonResponse({'error': 'Only POST method allowed'}, status=405)


@role_required(allowed_roles=['admin'])
@login_required
@csrf_exempt
def api_create_device_mapping(request):
    """API endpoint to create new device mapping record"""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            
            # Validate required fields
            required_fields = ['asset_code', 'device_type', 'oem_tag', 'data_type', 'units', 'metric']
            for field in required_fields:
                if not data.get(field):
                    return JsonResponse({'error': f'{field} is required'}, status=400)
            
            # Use raw SQL to insert into unmanaged table
            from django.db import connection
            
            with connection.cursor() as cursor:
                # Check if record with same asset_code, metric, device_type already exists
                cursor.execute("""
                    SELECT id FROM device_mapping 
                    WHERE asset_code = %s AND metric = %s AND device_type = %s
                """, [data.get('asset_code'), data.get('metric'), data.get('device_type')])
                
                existing_record = cursor.fetchone()
                if existing_record:
                    return JsonResponse({
                        'error': f'Record already exists with asset_code={data.get("asset_code")}, metric={data.get("metric")}, device_type={data.get("device_type")}'
                    }, status=400)
                
                # Get the next available ID
                cursor.execute("SELECT COALESCE(MAX(id), 0) + 1 FROM device_mapping")
                next_id = cursor.fetchone()[0]
                
                # Insert into device_mapping table
                cursor.execute("""
                    INSERT INTO device_mapping (
                        id, asset_code, device_type, oem_tag, discription,
                        data_type, units, metric, fault_code, module_no, default_value
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """, [
                    next_id,
                    ensure_unicode_string(data.get('asset_code')),
                    ensure_unicode_string(data.get('device_type')),
                    ensure_unicode_string(data.get('oem_tag')),
                    ensure_unicode_string(data.get('description', '')),  # Use 'description' from frontend but save as 'discription'
                    ensure_unicode_string(data.get('data_type')),
                    ensure_unicode_string(data.get('units')),
                    ensure_unicode_string(data.get('metric')),
                    ensure_unicode_string(data.get('fault_code', '')),
                    ensure_unicode_string(data.get('module_no', '')),
                    ensure_unicode_string(data.get('default_value', ''))
                ])
            
            return JsonResponse({
                'success': True,
                'message': 'Device mapping created successfully!',
                'id': next_id
            })
            
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)
    
    return JsonResponse({'error': 'Only POST method allowed'}, status=405)


@role_required(allowed_roles=['admin'])
@login_required
@csrf_exempt
def api_delete_device_mapping(request, mapping_id):
    """API endpoint to delete device mapping record"""
    if request.method == 'DELETE':
        try:
            # Check if user is superuser
            if not request.user.is_superuser:
                # Log unauthorized delete attempt for security
                import logging
                logger = logging.getLogger(__name__)
                logger.warning(f"Unauthorized delete attempt by user {request.user.username} (ID: {request.user.id}) for device mapping {mapping_id}")
                return JsonResponse({'error': 'Only superusers can delete records'}, status=403)
            
            # Use raw SQL to delete from unmanaged table
            from django.db import connection
            
            with connection.cursor() as cursor:
                cursor.execute("DELETE FROM device_mapping WHERE id = %s", [mapping_id])
                
            # Log successful delete for audit trail
            import logging
            logger = logging.getLogger(__name__)
            logger.info(f"Device mapping {mapping_id} deleted by superuser {request.user.username} (ID: {request.user.id})")
            
            return JsonResponse({
                'success': True,
                'message': 'Device mapping deleted successfully!'
            })
            
        except device_mapping.DoesNotExist:
            return JsonResponse({'error': 'Device mapping not found'}, status=404)
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)
    
    return JsonResponse({'error': 'Only DELETE method allowed'}, status=405)


@login_required
@feature_required('user_management')  # Only admins can access
def feedback_list_view(request):
    """
    View for admins to see all feedback with filtering and search.
    Only accessible to admin users.
    """
    from django.db.models import Q
    
    # Start with base queryset
    feedback_list = Feedback.objects.all().select_related('user')
    
    # Get filter parameters
    status_filter = request.GET.get('status', '')
    search_query = request.GET.get('search', '').strip()
    
    # Apply status filter
    if status_filter:
        feedback_list = feedback_list.filter(attended_status=status_filter)
    
    # Apply search filter
    if search_query:
        feedback_list = feedback_list.filter(
            Q(subject__icontains=search_query) |
            Q(message__icontains=search_query) |
            Q(user__username__icontains=search_query) |
            Q(user__first_name__icontains=search_query) |
            Q(user__last_name__icontains=search_query) |
            Q(user_email__icontains=search_query)
        )
    
    # Order by creation date (newest first)
    feedback_list = feedback_list.order_by('-created_at')
    
    # Add pagination
    paginator = Paginator(feedback_list, 10)  # Show 10 feedback per page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Prepare context with filter values for template
    context = {
        'page_obj': page_obj,
        'feedback_list': page_obj,
        'current_status': status_filter,
        'current_search': search_query,
        'total_count': paginator.count,
        'filtered_count': len(page_obj) if page_obj else 0,
    }
    
    return render(request, 'main/feedback_list.html', context)

# Add a new AJAX endpoint for loading images
@login_required
@feature_required('user_management')
def feedback_images_ajax(request, feedback_id):
    """
    AJAX endpoint to load images for a specific feedback entry
    """
    feedback = get_object_or_404(Feedback, id=feedback_id)
    images = feedback.images.all()
    
    images_data = []
    for image in images:
        images_data.append({
            'id': image.id,
            'url': image.image.url,
            'name': image.image.name
        })
    
    return JsonResponse({
        'success': True,
        'images': images_data,
        'count': images.count()
    })

@login_required
@feature_required('user_management')  # Only admins can access
def feedback_image_download(request, feedback_id):
    """
    View for admins to download feedback images.
    Only accessible to admin users.
    """
    feedback = get_object_or_404(Feedback, id=feedback_id)
    
    if not feedback.image:
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'error': 'No image attached to this feedback.'}, status=404)
        messages.error(request, 'No image attached to this feedback.')
        return redirect('main:feedback_list')
    
    try:
        # Check if file exists
        if not feedback.image.storage.exists(feedback.image.name):
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({'error': 'Image file not found on server.'}, status=404)
            messages.error(request, 'Image file not found on server.')
            return redirect('main:feedback_list')
        
        # For iframe context, provide a direct link to the media file
        if 'iframe' in request.GET or 'embed' in request.GET:
            # Redirect to direct media URL
            media_url = f"{settings.MEDIA_URL}{feedback.image.name}"
            return redirect(media_url)
        
        # Open the file and read its content
        with feedback.image.open('rb') as f:
            file_content = f.read()
        
        # Determine content type based on file extension
        import mimetypes
        content_type, _ = mimetypes.guess_type(feedback.image.name)
        if not content_type:
            content_type = 'application/octet-stream'
        
        response = HttpResponse(file_content, content_type=content_type)
        response['Content-Disposition'] = f'attachment; filename="{os.path.basename(feedback.image.name)}"'
        
        # Remove blocking headers for downloads
        response['X-Frame-Options'] = 'SAMEORIGIN'
        response['X-Content-Type-Options'] = 'nosniff'
        
        # Allow downloads from same origin
        response['Access-Control-Allow-Origin'] = request.META.get('HTTP_ORIGIN', '*')
        response['Access-Control-Allow-Methods'] = 'GET'
        response['Access-Control-Allow-Headers'] = 'Content-Type'
        
        return response
        
    except Exception as e:
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'error': f'Error downloading image: {str(e)}'}, status=500)
        messages.error(request, f'Error downloading image: {str(e)}')
        return redirect('main:feedback_list')


@login_required
@feature_required('user_management')  # Only admins can access
def feedback_image_direct(request, feedback_id):
    """
    Direct image serving view for downloads without security headers.
    Only accessible to admin users.
    """
    feedback = get_object_or_404(Feedback, id=feedback_id)
    
    if not feedback.image:
        return HttpResponse('No image found', status=404)
    
    try:
        # Check if file exists
        if not feedback.image.storage.exists(feedback.image.name):
            return HttpResponse('Image file not found', status=404)
        
        # Open the file and read its content
        with feedback.image.open('rb') as f:
            file_content = f.read()
        
        # Determine content type based on file extension
        import mimetypes
        content_type, _ = mimetypes.guess_type(feedback.image.name)
        if not content_type:
            content_type = 'image/jpeg'  # Default to image
        
        # Create a simple response with minimal headers
        response = HttpResponse(file_content, content_type=content_type)
        response['Content-Disposition'] = f'attachment; filename="{os.path.basename(feedback.image.name)}"'
        response['Content-Length'] = len(file_content)
        
        # Only essential headers - no security restrictions
        response['Cache-Control'] = 'no-cache'
        
        return response
        
    except Exception as e:
        return HttpResponse(f'Error: {str(e)}', status=500)


@login_required
@feature_required('user_management')  # Only admins can access
def debug_media_files(request):
    """
    Debug view to check media files and settings.
    Only accessible to admin users.
    """
    import os
    from django.conf import settings
    
    debug_info = {
        'media_root': settings.MEDIA_ROOT,
        'media_url': settings.MEDIA_URL,
        'debug_mode': settings.DEBUG,
        'media_root_exists': os.path.exists(settings.MEDIA_ROOT),
        'feedback_images_dir': os.path.join(settings.MEDIA_ROOT, 'feedback_images'),
        'feedback_images_exists': os.path.exists(os.path.join(settings.MEDIA_ROOT, 'feedback_images')),
        'feedback_count': Feedback.objects.count(),
        'feedback_with_images': Feedback.objects.exclude(image='').count(),
    }
    
    # List actual files in feedback_images directory
    feedback_images_path = os.path.join(settings.MEDIA_ROOT, 'feedback_images')
    if os.path.exists(feedback_images_path):
        debug_info['actual_files'] = os.listdir(feedback_images_path)
    else:
        debug_info['actual_files'] = []
    
    # List feedback records with images
    feedback_with_images = Feedback.objects.exclude(image='').values('id', 'subject', 'image', 'created_at')
    debug_info['feedback_records'] = list(feedback_with_images)
    
    return JsonResponse(debug_info, indent=2)



# Download Views for Data Export

@feature_required('data_upload')
@login_required
def download_data_view(request, data_type):
    """Generic download view for all data types - Admin only"""
    try:
        # Check if user is admin
        try:
            user_profile = UserProfile.objects.get(user=request.user)
            if user_profile.role != 'admin':
                return JsonResponse({'error': 'Access denied. Admin privileges required.'}, status=403)
        except UserProfile.DoesNotExist:
            return JsonResponse({'error': 'Access denied. User profile not found.'}, status=403)
        # Define the model mapping for download
        model_mapping = {
            'yield': YieldData,
            'bess': BESSData,
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
            return JsonResponse({'error': 'Invalid data type'}, status=400)

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
        return JsonResponse({'error': str(e)}, status=500)

def export_to_csv(queryset, friendly_name, data_type):
    """Export queryset to CSV format"""
    import csv
    from datetime import datetime

    # Create the HTTP response with CSV content type
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    filename = f"{friendly_name}_{timestamp}.csv"
    
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="{filename}"'

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
        return export_to_csv(queryset, friendly_name, data_type)
    except Exception as e:
        return JsonResponse({'error': f'Excel export failed: {str(e)}'}, status=500)


# Budget Values CRUD Operations
@role_required(allowed_roles=['admin'])
@login_required
def api_create_budget_values(request):
    """API endpoint to create a new budget values record"""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            
            # Use raw SQL for unmanaged table
            from django.db import connection
            
            asset_code = ensure_unicode_string(data.get('asset_code', ''))
            month_str = ensure_unicode_string(data.get('month_str', ''))
            
            # Check if record already exists
            with connection.cursor() as cursor:
                cursor.execute("""
                    SELECT id FROM budget_values 
                    WHERE asset_code = %s AND month_str = %s
                """, [asset_code, month_str])
                
                existing_record = cursor.fetchone()
                
                if existing_record:
                    return JsonResponse({'error': f'Budget values already exist for {asset_code} - {month_str}'}, status=400)
                
                # Insert new record
                cursor.execute("""
                    INSERT INTO budget_values (
                        asset_number, asset_code, month_str, month_date,
                        bd_production, bd_ghi, bd_gti
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s)
                """, [
                    ensure_unicode_string(data.get('asset_number', '')),
                    asset_code,
                    month_str,
                    data.get('month_date') if data.get('month_date') else None,
                    float(data.get('bd_production', 0)) if data.get('bd_production') else 0,
                    float(data.get('bd_ghi', 0)) if data.get('bd_ghi') else 0,
                    float(data.get('bd_gti', 0)) if data.get('bd_gti') else 0
                ])
            
            return JsonResponse({
                'success': True,
                'message': 'Budget values created successfully!'
            })
            
        except ValueError as e:
            return JsonResponse({'error': f'Invalid data format: {str(e)}'}, status=400)
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)
    
    return JsonResponse({'error': 'Only POST method allowed'}, status=405)

@role_required(allowed_roles=['admin'])
@login_required  
def api_update_budget_values(request):
    """API endpoint to update budget values record"""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            budget_id = data.get('id')
            
            if not budget_id:
                return JsonResponse({'error': 'Budget ID is required'}, status=400)
            
            # Use raw SQL for unmanaged table
            from django.db import connection
            
            with connection.cursor() as cursor:
                cursor.execute("""
                    UPDATE budget_values SET
                        asset_number = %s,
                        asset_code = %s,
                        month_str = %s,
                        month_date = %s,
                        bd_production = %s,
                        bd_ghi = %s,
                        bd_gti = %s
                    WHERE id = %s
                """, [
                    ensure_unicode_string(data.get('asset_number', '')),
                    ensure_unicode_string(data.get('asset_code', '')),
                    ensure_unicode_string(data.get('month_str', '')),
                    data.get('month_date') if data.get('month_date') else None,
                    float(data.get('bd_production', 0)) if data.get('bd_production') else 0,
                    float(data.get('bd_ghi', 0)) if data.get('bd_ghi') else 0,
                    float(data.get('bd_gti', 0)) if data.get('bd_gti') else 0,
                    budget_id
                ])
            
            return JsonResponse({
                'success': True,
                'message': 'Budget values updated successfully!'
            })
            
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)
    
    return JsonResponse({'error': 'Only POST method allowed'}, status=405)

@superuser_required
@role_required(allowed_roles=['admin'])
@login_required
def api_delete_budget_values(request, budget_id):
    """API endpoint to delete budget values record"""
    if request.method == 'DELETE':
        try:
            # Check if user is superuser
            if not request.user.is_superuser:
                # Log unauthorized delete attempt for security
                import logging
                logger = logging.getLogger(__name__)
                logger.warning(f"Unauthorized delete attempt by user {request.user.username} (ID: {request.user.id}) for budget values {budget_id}")
                return JsonResponse({'error': 'Only superusers can delete records'}, status=403)
            
            # Use raw SQL to delete from unmanaged table
            from django.db import connection
            
            with connection.cursor() as cursor:
                cursor.execute("DELETE FROM budget_values WHERE id = %s", [budget_id])
                
            # Log successful delete for audit trail
            import logging
            logger = logging.getLogger(__name__)
            logger.info(f"Budget values {budget_id} deleted by superuser {request.user.username} (ID: {request.user.id})")
            
            return JsonResponse({
                'success': True,
                'message': 'Budget values deleted successfully!'
            })
            
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)
    
    return JsonResponse({'error': 'Only DELETE method allowed'}, status=405)


# IC Budget API endpoints
@role_required(allowed_roles=['admin'])
@login_required
def api_ic_budget_data(request):
    """API endpoint to fetch paginated IC budget data"""
    if request.method == 'GET':
        try:
            page = int(request.GET.get('page', 1))
            page_size = int(request.GET.get('page_size', 25))
            search = request.GET.get('search', '')
            
            # Use raw SQL to query unmanaged table
            from django.db import connection
            
            with connection.cursor() as cursor:
                # Build search condition
                search_condition = ""
                search_params = []
                if search:
                    search_condition = "WHERE (asset_code ILIKE %s OR asset_number ILIKE %s OR month_str ILIKE %s)"
                    search_params = [f'%{search}%', f'%{search}%', f'%{search}%']
                
                # Get total count
                count_query = f"SELECT COUNT(*) FROM ic_budget {search_condition}"
                cursor.execute(count_query, search_params)
                total_count = cursor.fetchone()[0]
                
                # Calculate pagination
                offset = (page - 1) * page_size
                total_pages = (total_count + page_size - 1) // page_size
                
                # Get paginated data
                data_query = f"""
                    SELECT id, asset_code, asset_number, month_str, month_date, ic_bd_production
                    FROM ic_budget 
                    {search_condition}
                    ORDER BY asset_code, month_str
                    LIMIT %s OFFSET %s
                """
                cursor.execute(data_query, search_params + [page_size, offset])
                
                columns = [col[0] for col in cursor.description]
                ic_budgets = [dict(zip(columns, row)) for row in cursor.fetchall()]
                
                # Convert dates to strings for JSON serialization
                for ic_budget in ic_budgets:
                    if ic_budget['month_date']:
                        ic_budget['month_date'] = ic_budget['month_date'].strftime('%Y-%m-%d')
            
            return JsonResponse({
                'ic_budgets': ic_budgets,
                'pagination': {
                    'current_page': page,
                    'total_pages': total_pages,
                    'total_count': total_count,
                    'page_size': page_size
                }
            })
            
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)
    
    return JsonResponse({'error': 'Only GET method allowed'}, status=405)


@role_required(allowed_roles=['admin'])
@login_required
@csrf_exempt
def api_create_ic_budget(request):
    """API endpoint to create new IC budget record"""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            
            # Validate required fields
            required_fields = ['asset_code', 'asset_number', 'month_str', 'month_date', 'ic_bd_production']
            for field in required_fields:
                if not data.get(field):
                    return JsonResponse({'error': f'{field} is required'}, status=400)
            
            # Use raw SQL to insert into unmanaged table
            from django.db import connection
            
            with connection.cursor() as cursor:
                # Handle date formatting
                month_date = data.get('month_date')
                if month_date:
                    try:
                        from datetime import datetime
                        month_date = datetime.strptime(month_date, '%Y-%m-%d').date()
                    except:
                        return JsonResponse({'error': 'Invalid month_date format. Use YYYY-MM-DD'}, status=400)
                
                # Check for existing record
                cursor.execute("""
                    SELECT id FROM ic_budget 
                    WHERE asset_code = %s AND month_str = %s
                """, [data.get('asset_code'), data.get('month_str')])
                
                if cursor.fetchone():
                    return JsonResponse({'error': 'IC Budget record already exists for this asset and month'}, status=400)
                
                # Insert into ic_budget table
                cursor.execute("""
                    INSERT INTO ic_budget (
                        asset_code, asset_number, month_str, month_date, ic_bd_production
                    ) VALUES (%s, %s, %s, %s, %s)
                """, [
                    data.get('asset_code'),
                    data.get('asset_number'),
                    data.get('month_str'),
                    month_date,
                    float(data.get('ic_bd_production'))
                ])
            
            return JsonResponse({
                'success': True,
                'message': 'IC Budget created successfully!'
            })
            
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)
    
    return JsonResponse({'error': 'Only POST method allowed'}, status=405)


@role_required(allowed_roles=['admin'])
@login_required
@csrf_exempt
def api_update_ic_budget(request):
    """API endpoint to update IC budget record"""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            ic_budget_id = data.get('id')
            
            if not ic_budget_id:
                return JsonResponse({'error': 'IC Budget ID is required'}, status=400)
            
            # Use raw SQL to update unmanaged table
            from django.db import connection
            
            with connection.cursor() as cursor:
                # Handle date formatting
                month_date = data.get('month_date')
                if month_date:
                    try:
                        from datetime import datetime
                        month_date = datetime.strptime(month_date, '%Y-%m-%d').date()
                    except:
                        return JsonResponse({'error': 'Invalid month_date format. Use YYYY-MM-DD'}, status=400)
                
                # Update ic_budget table
                cursor.execute("""
                    UPDATE ic_budget 
                    SET asset_code = %s, asset_number = %s, month_str = %s, 
                        month_date = %s, ic_bd_production = %s
                    WHERE id = %s
                """, [
                    data.get('asset_code'),
                    data.get('asset_number'),
                    data.get('month_str'),
                    month_date,
                    float(data.get('ic_bd_production')),
                    ic_budget_id
                ])
            
            return JsonResponse({
                'success': True,
                'message': 'IC Budget updated successfully!'
            })
            
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)
    
    return JsonResponse({'error': 'Only POST method allowed'}, status=405)


@role_required(allowed_roles=['admin'])
@login_required
def api_delete_ic_budget(request, ic_budget_id):
    """API endpoint to delete IC budget record"""
    if request.method == 'DELETE':
        try:
            # Check if user is superuser
            if not request.user.is_superuser:
                # Log unauthorized delete attempt for security
                import logging
                logger = logging.getLogger(__name__)
                logger.warning(f"Unauthorized delete attempt by user {request.user.username} (ID: {request.user.id}) for IC budget {ic_budget_id}")
                return JsonResponse({'error': 'Only superusers can delete records'}, status=403)
            
            # Use raw SQL to delete from unmanaged table
            from django.db import connection
            
            with connection.cursor() as cursor:
                cursor.execute("DELETE FROM ic_budget WHERE id = %s", [ic_budget_id])
                
            # Log successful delete for audit trail
            import logging
            logger = logging.getLogger(__name__)
            logger.info(f"IC Budget {ic_budget_id} deleted by superuser {request.user.username} (ID: {request.user.id})")
            
            return JsonResponse({
                'success': True,
                'message': 'IC Budget deleted successfully!'
            })
            
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)
    
    return JsonResponse({'error': 'Only DELETE method allowed'}, status=405)


@login_required
@feature_required('user_management')  # Only admins can access
def mark_feedback_attended(request, feedback_id):
    """
    Mark feedback as attended and send thank you email to the user.
    Only accessible to admin users.
    """
    if request.method != 'POST':
        return JsonResponse({'error': 'Only POST method allowed'}, status=405)
    
    try:
        feedback = get_object_or_404(Feedback, id=feedback_id)
        
        # Check if already attended
        if feedback.attended_status == 'attended':
            return JsonResponse({
                'success': False,
                'message': 'This feedback has already been marked as attended.'
            })
        
        # Get admin response text from request body
        import json
        admin_response = ''
        try:
            data = json.loads(request.body)
            admin_response = data.get('admin_response', '').strip()
        except (json.JSONDecodeError, AttributeError):
            # If no JSON data, admin_response remains empty
            pass
        
        # Update feedback status
        from django.utils import timezone
        feedback.attended_status = 'attended'
        feedback.attended_at = timezone.now()
        feedback.save()
        
        # Send thank you email
        try:
            from django.template.loader import render_to_string
            from django.core.mail import EmailMultiAlternatives
            
            # Prepare email context
            context = {
                'user_name': feedback.user.get_full_name() or feedback.user.username,
                'feedback_subject': feedback.subject,
                'feedback_date': feedback.created_at.strftime('%B %d, %Y at %I:%M %p'),
                'admin_response': admin_response,
                'has_admin_response': bool(admin_response),
            }
            
            # Render email templates
            html_content = render_to_string('main/feedback_thank_you_email.html', context)
            text_content = render_to_string('main/feedback_thank_you_email.txt', context)
            
            # Create email
            subject = f'Thank You for Your Feedback - {feedback.subject}'
            from_email = settings.DEFAULT_FROM_EMAIL
            to_email = [feedback.user_email]
            
            # Create email message
            msg = EmailMultiAlternatives(subject, text_content, from_email, to_email)
            msg.attach_alternative(html_content, "text/html")
            
            # Send email
            msg.send()
            
            email_sent = True
            email_message = "Thank you email sent successfully."
            
        except Exception as e:
            # Log email error but don't fail the entire operation
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Failed to send thank you email for feedback {feedback_id}: {str(e)}")
            email_sent = False
            email_message = f"Feedback marked as attended, but email sending failed: {str(e)}"
        
        return JsonResponse({
            'success': True,
            'message': f'Feedback marked as attended successfully! {email_message}',
            'email_sent': email_sent,
            'attended_at': feedback.attended_at.strftime('%B %d, %Y at %I:%M %p'),
            'subject': feedback.subject
        })
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)
    

# Add this new view after the mark_feedback_attended view
@login_required
@superuser_required  # Only superusers can delete feedback
def delete_feedback(request, feedback_id):
    """
    Delete feedback entry. Only superusers can delete attended feedback.
    """
    if request.method != 'POST':
        return JsonResponse({'success': False, 'message': 'Invalid request method.'}, status=405)
    
    try:
        feedback = get_object_or_404(Feedback, id=feedback_id)
        
        # Only allow deletion of attended feedback
        if feedback.attended_status != 'attended':
            return JsonResponse({
                'success': False,
                'message': 'Only attended feedback can be deleted.'
            }, status=400)
        
        # Store feedback info for logging
        user_info = f"{feedback.user.username} ({feedback.user_email})"
        subject = feedback.subject
        created_date = feedback.created_at.strftime('%Y-%m-%d %H:%M')
        
        # Delete associated images first (they will be deleted automatically due to CASCADE)
        # but we can log the count for audit purposes
        image_count = feedback.images.count()
        
        # Delete the feedback
        feedback.delete()
        
        # Log the deletion
        logger = logging.getLogger(__name__)
        logger.info(f"Feedback deleted by superuser {request.user.username}: "
                   f"ID={feedback_id}, User={user_info}, Subject='{subject}', "
                   f"Created={created_date}, Images deleted={image_count}")
        
        return JsonResponse({
            'success': True,
            'message': f'Feedback "{subject}" has been successfully deleted.'
        })
        
    except Exception as e:
        logger = logging.getLogger(__name__)
        logger.error(f"Error deleting feedback {feedback_id}: {str(e)}")
        
        return JsonResponse({
            'success': False,
            'message': 'An error occurred while deleting the feedback.'
        }, status=500)


# External Service Proxy Views for Iframe Integration
import requests

@csrf_exempt
@require_http_methods(["GET", "POST", "PUT", "DELETE", "OPTIONS"])
def proxy_external_service(request, service_path=''):
    """
    Proxy view to handle external service requests and bypass iframe restrictions
    """
    # Allowed external services (whitelist for security)
    allowed_services = {
        '10.80.100.103:5555': {
            'base_url': 'http://10.80.100.103:5555',
            'allowed_paths': ['/', '/dashboard/', '/api/', '/reports/'],
            'headers_to_forward': ['Authorization', 'Content-Type', 'Accept'],
            'timeout': 30
        }
    }
    
    # Extract service from request
    service_host = request.GET.get('service', '10.80.100.103:5555')
    
    if service_host not in allowed_services:
        logger = logging.getLogger(__name__)
        logger.warning(f"Unauthorized service access attempt: {service_host}")
        return HttpResponse("Service not allowed", status=403)
    
    service_config = allowed_services[service_host]
    base_url = service_config['base_url']
    
    # Construct the full URL
    if service_path.startswith('/'):
        full_url = f"{base_url}{service_path}"
    else:
        full_url = f"{base_url}/{service_path}"
    
    # Check if path is allowed
    if not any(full_url.startswith(base_url + path) for path in service_config['allowed_paths']):
        logger = logging.getLogger(__name__)
        logger.warning(f"Unauthorized path access: {service_path}")
        return HttpResponse("Path not allowed", status=403)
    
    try:
        # Prepare headers
        headers = {}
        for header_name in service_config['headers_to_forward']:
            if header_name in request.META:
                headers[header_name] = request.META[header_name]
        
        # Add user agent
        headers['User-Agent'] = request.META.get('HTTP_USER_AGENT', 'Django-Proxy')
        
        # Prepare data for POST/PUT requests
        data = None
        if request.method in ['POST', 'PUT']:
            data = request.body
        
        # Make the request to external service
        response = requests.request(
            method=request.method,
            url=full_url,
            headers=headers,
            data=data,
            params=request.GET,
            timeout=service_config['timeout'],
            allow_redirects=False
        )
        
        # Create Django response
        django_response = HttpResponse(
            content=response.content,
            status=response.status_code,
            content_type=response.headers.get('Content-Type', 'text/html')
        )
        
        # Forward important headers (excluding frame options)
        headers_to_forward = [
            'Content-Type', 'Cache-Control', 'ETag', 'Last-Modified',
            'Content-Encoding', 'Content-Length'
        ]
        
        for header in headers_to_forward:
            if header in response.headers:
                django_response[header] = response.headers[header]
        
        # Override frame options to allow embedding
        django_response['X-Frame-Options'] = 'SAMEORIGIN'
        
        return django_response
        
    except requests.exceptions.RequestException as e:
        logger = logging.getLogger(__name__)
        logger.error(f"Proxy request failed: {str(e)}")
        return HttpResponse("Service temporarily unavailable", status=503)
    except Exception as e:
        logger = logging.getLogger(__name__)
        logger.error(f"Unexpected proxy error: {str(e)}")
        return HttpResponse("Internal server error", status=500)

def iframe_proxy_view(request):
    """
    Simple iframe proxy for external services
    """
    service_url = request.GET.get('url', '')
    
    if not service_url:
        return HttpResponse("No URL provided", status=400)
    
    # Validate URL is from allowed service
    if not service_url.startswith('http://10.80.100.103:5555'):
        return HttpResponse("Service not allowed", status=403)
    
    try:
        response = requests.get(service_url, timeout=30)
        
        # Create response with frame options that allow embedding
        django_response = HttpResponse(
            content=response.content,
            status=response.status_code,
            content_type=response.headers.get('Content-Type', 'text/html')
        )
        
        # Allow iframe embedding
        django_response['X-Frame-Options'] = 'SAMEORIGIN'
        
        return django_response
        
    except Exception as e:
        logger = logging.getLogger(__name__)
        logger.error(f"Iframe proxy error: {str(e)}")
        return HttpResponse("Service unavailable", status=503)

# Security Management API Endpoints for Superusers
@login_required
def get_blocked_ips(request):
    """Get list of blocked IPs - Superuser only"""
    if not request.user.is_superuser:
        return JsonResponse({'error': 'Permission denied'}, status=403)
    
    try:
        from main.middleware.realtime_ip_blocker import realtime_blocker
        stats = realtime_blocker.get_blocking_stats()
        return JsonResponse({
            'success': True,
            'blocked_ips': stats['blocked_ips'],
            'total_blocked_ips': stats['total_blocked_ips']
        })
    except Exception as e:
        return JsonResponse({'error': f'Import error: {str(e)}'}, status=500)

@login_required
def test_security_endpoint(request):
    """Test endpoint to verify URLs are working"""
    return JsonResponse({'message': 'Security endpoints are working!', 'status': 'ok'})

@login_required
def get_blocked_users(request):
    """Get list of blocked users - Superuser only"""
    if not request.user.is_superuser:
        return JsonResponse({'error': 'Permission denied'}, status=403)
    
    try:
        from main.middleware.realtime_ip_blocker import realtime_blocker
        stats = realtime_blocker.get_blocking_stats()
        return JsonResponse({
            'success': True,
            'blocked_users': stats['blocked_users'],
            'total_blocked_users': stats['total_blocked_users']
        })
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

@login_required
def block_ip_manual(request):
    """Manually block an IP address - Superuser only"""
    if not request.user.is_superuser:
        return JsonResponse({'error': 'Permission denied'}, status=403)
    
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            ip_address = data.get('ip_address', '').strip()
            reason = data.get('reason', 'Manually blocked by admin')
            
            if not ip_address:
                return JsonResponse({'error': 'IP address is required'}, status=400)
            
            from main.middleware.realtime_ip_blocker import realtime_blocker
            realtime_blocker.block_ip_immediately(ip_address, reason, False)
            
            return JsonResponse({
                'success': True,
                'message': f'IP {ip_address} blocked successfully'
            })
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)
    
    return JsonResponse({'error': 'Method not allowed'}, status=405)

@login_required
def unblock_ip_manual(request):
    """Manually unblock an IP address - Superuser only"""
    if not request.user.is_superuser:
        return JsonResponse({'error': 'Permission denied'}, status=403)
    
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            ip_address = data.get('ip_address', '').strip()
            reason = data.get('reason', 'Manual unblock by admin')
            
            if not ip_address:
                return JsonResponse({'error': 'IP address is required'}, status=400)
            
            from main.models import BlockedIP, IPBlockingLog
            from main.middleware.realtime_ip_blocker import realtime_blocker
            from django.utils import timezone
            
            # Check if IP is blocked
            try:
                blocked_ip = BlockedIP.objects.get(ip_address=ip_address, status='active')
            except BlockedIP.DoesNotExist:
                return JsonResponse({
                    'error': f'IP {ip_address} is not currently blocked'
                }, status=404)
            
            # Update BlockedIP record
            blocked_ip.status = 'inactive'
            blocked_ip.updated_at = timezone.now()
            blocked_ip.save()
            
            # Create IPBlockingLog entry for unblocking
            IPBlockingLog.objects.create(
                ip_address=ip_address,
                block_type='manual',
                block_reason='other',
                reason_details=f"Unblocked: {reason}",
                blocked_by=blocked_ip.blocked_by,
                status='unblocked',
                unblocked_by=request.user,
                unblocked_at=timezone.now(),
                unblock_reason=reason,
                metadata={
                    'manual_unblock': True,
                    'original_reason': blocked_ip.reason
                }
            )
            
            # Update realtime blocker cache
            realtime_blocker.blocked_ips.discard(ip_address)
            
            return JsonResponse({
                'success': True,
                'message': f'IP {ip_address} unblocked successfully',
                'original_reason': blocked_ip.reason
            })
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)
    
    return JsonResponse({'error': 'Method not allowed'}, status=405)

@login_required
def block_user_manual(request):
    """Manually block a user - Superuser only"""
    if not request.user.is_superuser:
        return JsonResponse({'error': 'Permission denied'}, status=403)
    
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            username = data.get('username', '').strip()
            reason = data.get('reason', 'Manually blocked by admin')
            
            if not username:
                return JsonResponse({'error': 'Username is required'}, status=400)
            
            # Check if user exists
            try:
                user = User.objects.get(username=username)
            except User.DoesNotExist:
                return JsonResponse({'error': 'User not found'}, status=404)
            
            from main.middleware.realtime_ip_blocker import realtime_blocker
            realtime_blocker.block_user_immediately(username, reason)
            
            return JsonResponse({
                'success': True,
                'message': f'User {username} blocked successfully'
            })
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)
    
    return JsonResponse({'error': 'Method not allowed'}, status=405)

@login_required
def unblock_user_manual(request):
    """Manually unblock a user - Superuser only"""
    if not request.user.is_superuser:
        return JsonResponse({'error': 'Permission denied'}, status=403)
    
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            username = data.get('username', '').strip()
            reason = data.get('reason', 'Manual unblock by admin')
            
            if not username:
                return JsonResponse({'error': 'Username is required'}, status=400)
            
            from main.models import BlockedUser, UserBlockingLog
            from main.middleware.realtime_ip_blocker import realtime_blocker
            from django.utils import timezone
            
            # Check if user exists and is blocked
            try:
                user = User.objects.get(username=username)
                blocked_user = BlockedUser.objects.get(user=user, status='active')
            except User.DoesNotExist:
                return JsonResponse({'error': f'User {username} not found'}, status=404)
            except BlockedUser.DoesNotExist:
                return JsonResponse({
                    'error': f'User {username} is not currently blocked'
                }, status=404)
            
            # Update BlockedUser record
            blocked_user.status = 'inactive'
            blocked_user.updated_at = timezone.now()
            blocked_user.save()
            
            # Create UserBlockingLog entry for unblocking
            UserBlockingLog.objects.create(
                user=user,
                block_type='manual',
                block_reason='other',
                reason_details=f"Unblocked: {reason}",
                ip_address=request.META.get('REMOTE_ADDR', '127.0.0.1'),
                blocked_by=blocked_user.blocked_by,
                status='unblocked',
                unblocked_by=request.user,
                unblocked_at=timezone.now(),
                unblock_reason=reason,
                metadata={
                    'manual_unblock': True,
                    'original_reason': blocked_user.reason
                }
            )
            
            # Re-enable user account
            user.is_active = True
            user.save()
            
            # Update realtime blocker cache
            realtime_blocker.blocked_users.discard(username)
            
            return JsonResponse({
                'success': True,
                'message': f'User {username} unblocked successfully',
                'original_reason': blocked_user.reason
            })
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)
    
    return JsonResponse({'error': 'Method not allowed'}, status=405)

@csrf_exempt
def delete_user_permanent(request):
    """Permanently delete a user - Superuser only"""
    if not request.user.is_superuser:
        return JsonResponse({'error': 'Permission denied'}, status=403)
    
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            username = data.get('username', '').strip()
            
            if not username:
                return JsonResponse({'error': 'Username is required'}, status=400)
            
            # Prevent self-deletion
            if username == request.user.username:
                return JsonResponse({'error': 'You cannot delete your own account'}, status=400)
            
            # Check if user exists
            try:
                user = User.objects.get(username=username)
            except User.DoesNotExist:
                return JsonResponse({'error': 'User not found'}, status=404)
            
            # Delete user (this will cascade to related objects)
            user.delete()
            
            return JsonResponse({
                'success': True,
                'message': f'User {username} deleted permanently'
            })
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)
    
    return JsonResponse({'error': 'Method not allowed'}, status=405)

# Example view removed to prevent iframe conflicts