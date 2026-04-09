"""
Data upload and management views
"""
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

from ..models import (
    YieldData, BESSData, BESSV1Data, AOCData, ICEData, FeedbackImage, ICVSEXVSCURData, MapData, 
    MinamataStringLossData, DataImportLog, AssetList, device_list, device_mapping, budget_values, timeseries_data, UserProfile,
    ActualGenerationDailyData, ExpectedBudgetDailyData, BudgetGIIDailyData, ActualGIIDailyData,
    ICApprovedBudgetDailyData, LossCalculationData, RealTimeKPI, Feedback, ic_budget
)
from ..forms import FeedbackForm

import csv, json, os, pandas as pd, io, math, pytz, chardet
from datetime import datetime, timezone, timedelta
from django.http import HttpResponse
from django.core.paginator import Paginator

from .shared.utilities import (
	 detect_file_encoding
)
from .shared.validators import (
    try_read_csv_with_encoding, clean_file_content, analyze_file_encoding, try_decode_with_errors,
    validate_csv_requirements, validate_csv_data
)


@feature_required('data_upload')
@login_required
@ensure_csrf_cookie  # Ensures CSRF token is available for React app
def data_upload_view(request):
    print(f"Data upload view accessed - Method: {request.method}")
    
    # Check if React version is enabled via waffle flag
    from waffle import flag_is_active
    use_react = flag_is_active(request, 'react_data_upload')
    
    if request.method == 'GET':
        if use_react:
            return render(request, 'main/data_upload_react.html')
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
#@csrf_exempt
def data_upload_help_view(request):
    """Help page for data upload with templates and instructions"""
    # Check if React version is enabled via waffle flag
    from waffle import flag_is_active
    use_react = flag_is_active(request, 'react_data_upload_help')
    
    if use_react:
        return render(request, 'main/data_upload_help_react.html')
    
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
        successful_encoding = None
        error_details = []
        
        print(f"Trying to read CSV file: {csv_file.name if hasattr(csv_file, 'name') else 'Unknown'}")
        print(f"Detected encoding: {detected_encoding}")
        
        for encoding in encodings_to_try:
            if encoding is None:
                continue
                
            result = try_read_csv_with_encoding(csv_file, encoding)
            if result['success']:
                df = result['df']
                successful_encoding = encoding
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
                    successful_encoding = encoding
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
                            successful_encoding = encoding
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
        
        # Drop completely empty columns (common in Excel exports)
        # This helps with validation and processing efficiency
        initial_col_count = len(df.columns)
        df = df.dropna(axis=1, how='all')  # Drop columns where all values are NaN
        dropped_cols = initial_col_count - len(df.columns)
        if dropped_cols > 0:
            print(f"⚠️ Dropped {dropped_cols} completely empty columns (likely from Excel export)")
        
        # Check if daily CSV files have only one column - try different delimiters
        if data_type in ['actual_generation_daily', 'expected_budget_daily', 'budget_gii_daily', 'actual_gii_daily', 'ic_approved_budget_daily']:
            if len(df.columns) == 1:
                print(f"⚠️ Warning: CSV file has only 1 column. Trying different delimiters...")
                # Try different delimiters
                delimiters_to_try = [';', '\t', '|', ',']
                for delimiter in delimiters_to_try:
                    if delimiter == ',':
                        continue  # Already tried comma
                    try:
                        csv_file.seek(0)
                        test_df = pd.read_csv(csv_file, encoding=successful_encoding or 'utf-8', sep=delimiter)
                        if len(test_df.columns) > 1:
                            print(f"✅ Successfully read CSV with delimiter '{delimiter}' - found {len(test_df.columns)} columns")
                            df = test_df
                            break
                    except Exception as e:
                        print(f"❌ Failed with delimiter '{delimiter}': {e}")
                        continue
        
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
                
                # Special handling for percentage sign - replace % with _percent
                if normalized_col.endswith('_%'):
                    normalized_col = normalized_col.replace('_%', '_percent')
                elif '%' in normalized_col:
                    normalized_col = normalized_col.replace('%', '_percent')
                
                # Clean up any double underscores
                while '__' in normalized_col:
                    normalized_col = normalized_col.replace('__', '_')
                
                # Special handling for Yield data columns
                if data_type == 'yield':
                    # Handle special column name mappings for yield data
                    if normalized_col == 'string_failure' or normalized_col == 'stringfailure':
                        normalized_col = 'string_failure'
                    elif normalized_col == 'inverter_failure' or normalized_col == 'inverterfailure':
                        normalized_col = 'inverter_failure'
                    elif normalized_col in ('budgeted_grid_curtailment', 'budgetedgridcurtailment'):
                        normalized_col = 'budgeted_grid_curtailment'
                    # Handle duplicate grid_curtailment columns - skip if already added
                    if normalized_col == 'grid_curtailment' and normalized_col in normalized_columns:
                        # If we already have grid_curtailment, skip the duplicate
                        continue
                
                # Special handling for ICVSEXVSCUR percentage columns
                if data_type == 'icvsexvscur':
                    if 'expected_pr' in normalized_col and 'percent' not in normalized_col:
                        normalized_col = 'expected_pr_percent'
                    elif 'actual_pr' in normalized_col and 'percent' not in normalized_col:
                        normalized_col = 'actual_pr_percent'
                
                # Special handling for Loss Calculation columns
                if data_type == 'loss_calculation':
                    # Fix common column mapping issues
                    if normalized_col == 's_no':
                        normalized_col = 'l'  # Map S No to l (Loss ID)
                    elif normalized_col == 'start_dae':
                        normalized_col = 'start_date'  # Fix typo in "Start Dae"
                    elif normalized_col == 'subcatergory':
                        normalized_col = 'subcategory'  # Fix typo in "Subcatergory"
                    elif normalized_col == 'budget_pr_percent':
                        normalized_col = 'budget_pr_percent'  # Fix percentage column
                    elif normalized_col == 'ppa_rate_in_usd':
                        normalized_col = 'ppa_rate_usd'  # Fix PPA rate column
                    elif normalized_col == 'revenue_loss_in_usd':
                        normalized_col = 'revenue_loss_usd'  # Fix revenue loss column
                
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



# API endpoints for data management
#@csrf_exempt
@login_required
def api_data_counts(request):
    """Get data counts for all data types"""
    try:
        counts = {
            'yield_count': YieldData.objects.count(),
            'bess_count': BESSData.objects.count(),
            'bess_v1_count': BESSV1Data.objects.count(),
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
                        elif 'bessv1' in upload.file_name.lower() or 'bess_v1' in upload.file_name.lower():
                            data_type = 'bess_v1'
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
        }
        
        model = model_mapping.get(data_type)
        if not model:
            return JsonResponse({'error': 'Invalid data type'}, status=400)
        
        # Get first 10 records with ordering
        records = model.objects.order_by('-id')[:10]
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
        
        # Return with message if no data found
        if not data:
            return JsonResponse({
                'data': [],
                'message': f'No preview data found for {data_type}. The table may be empty or contain no records.'
            })
        
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
def api_download_data(request):
    """API endpoint to download data as CSV or Excel"""
    if request.method != 'GET':
        return JsonResponse({'error': 'Method not allowed'}, status=405)
    
    try:
        data_type = request.GET.get('data_type')
        format_type = request.GET.get('format', 'csv').lower()
        
        if not data_type:
            return JsonResponse({'error': 'Data type is required'}, status=400)
        
        # Validate format
        if format_type not in ['csv', 'excel']:
            return JsonResponse({'error': 'Invalid format. Must be "csv" or "excel"'}, status=400)
        
        # Check permissions - reuse the download_data_view which has permission checks
        from .download_views import download_data_view
        
        # Ensure format parameter is in request.GET for download_data_view
        # download_data_view reads format from request.GET.get('format')
        # The format is already in request.GET, so it will be passed through
        
        try:
            # The download_data_view returns HttpResponse directly, which we can return
            response = download_data_view(request, data_type)
            
            # Check if response is an error
            if response.status_code >= 400:
                # Check if it's a JSON error response (from export_to_excel error handling)
                content_type = response.get('Content-Type', '')
                if 'application/json' in content_type:
                    # It's already a JSON error response, return it as-is
                    return response
                # If it's an HTML error response, return JSON error instead
                elif hasattr(response, 'content') and isinstance(response.content, bytes) and b'<html' in response.content:
                    error_msg = 'Excel export failed. Please try CSV format or ensure pandas/openpyxl is installed.'
                    if format_type == 'excel':
                        return JsonResponse({
                            'error': error_msg,
                            'suggestion': 'Try downloading as CSV format instead'
                        }, status=500)
                    else:
                        return JsonResponse({'error': 'Download failed'}, status=response.status_code)
            
            return response
        except ImportError as e:
            # Pandas/openpyxl not available
            logger = logging.getLogger(__name__)
            logger.error(f"Import error in api_download_data: {str(e)}", exc_info=True)
            if format_type == 'excel':
                return JsonResponse({
                    'error': 'Excel export requires pandas and openpyxl packages. Please install them or use CSV format.',
                    'suggestion': 'Try downloading as CSV format instead'
                }, status=500)
            raise
        except Exception as e:
            logger = logging.getLogger(__name__)
            logger.error(f"Error in download_data_view for {data_type}: {str(e)}", exc_info=True)
            if format_type == 'excel':
                return JsonResponse({
                    'error': f'Excel export failed: {str(e)}. Please try CSV format.',
                    'suggestion': 'Try downloading as CSV format instead'
                }, status=500)
            raise
        
    except Exception as e:
        logger = logging.getLogger(__name__)
        logger.error(f"Error in api_download_data: {str(e)}", exc_info=True)
        return JsonResponse({'error': str(e)}, status=500)

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
            'ic_approved_budget_daily': ICApprovedBudgetDailyData
        }
        
        model = model_mapping.get(data_type)
        if not model:
            return {'success': False, 'error': 'Invalid data type'}
        
        # Delete based on date field
        if data_type in ['actual_generation_daily', 'expected_budget_daily', 'budget_gii_daily', 'actual_gii_daily', 'ic_approved_budget_daily']:
            deleted_count = model.objects.filter(
                date__gte=start_dt,
                date__lte=end_dt
            ).delete()[0]
        elif data_type == 'bess':
            deleted_count = model.objects.filter(
                date__gte=start_date,
                date__lte=end_date
            ).delete()[0]
        elif data_type == 'bess_v1':
            start_month = start_date[:7]
            end_month = end_date[:7]
            deleted_count = model.objects.filter(
                month__gte=start_month,
                month__lte=end_month
            ).delete()[0]
        elif data_type == 'icvsexvscur':
            # For IC vs Expected, month is stored as a proper date (first day of the month),
            # so we should filter using real date objects, not truncated YYYY-MM strings.
            deleted_count = model.objects.filter(
                month__gte=start_dt,
                month__lte=end_dt
            ).delete()[0]
        else:
            # For other models, delete by month if available.
            # The frontend sends full dates (YYYY-MM-DD) from <input type="date">,
            # but many of these models store only month-level strings (e.g. '2025-01').
            # Normalize the incoming dates to year-month so the comparison actually matches.
            start_month = start_date[:7]  # 'YYYY-MM'
            end_month = end_date[:7]      # 'YYYY-MM'
            deleted_count = model.objects.filter(
                month__gte=start_month,
                month__lte=end_month
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
        'bess_v1': 'BESSV1Data',
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
    from .. import models
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
        'bess_v1': ['month', 'country', 'portfolio', 'asset_no'],
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
    
    # If we already have a datetime / Timestamp / date-like object,
    # just normalize it to the first day of that month.
    try:
        # pandas.Timestamp, datetime, and date all have year/month attributes
        if hasattr(month_str, "year") and hasattr(month_str, "month"):
            return datetime(month_str.year, month_str.month, 1).date()
    except Exception as e:
        print(f"Error normalizing existing date '{month_str}': {e}")
    
    month_mapping = {
        'jan': 1, 'feb': 2, 'mar': 3, 'apr': 4, 'may': 5, 'jun': 6,
        'jul': 7, 'aug': 8, 'sep': 9, 'oct': 10, 'nov': 11, 'dec': 12
    }
    
    try:
        # First, support the historic "25-Apr" and "Jan-25" formats
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
                    year_part = None
                    month_part = None
                
                if year_part is not None and month_part is not None:
                    # Determine year (assuming 25 means 2025)
                    if year_part.isdigit():
                        year = 2000 + int(year_part) if int(year_part) < 100 else int(year_part)
                    else:
                        year = 2025  # Default fallback
                    
                    # Get month number
                    month_num = month_mapping.get(month_part, 1)
                    
                    # Return date object for 1st day of the month
                    return datetime(year, month_num, 1).date()
        
        # If the older dash formats didn't match, fall back to general date parsing
        # to support values like "1/1/2026", "2026-01-01", "01-01-2026", etc.
        if isinstance(month_str, str):
            import pandas as pd
            parsed = pd.to_datetime(month_str)
            return datetime(parsed.year, parsed.month, 1).date()
    except Exception as e:
        print(f"Error parsing month '{month_str}': {e}")
    
    # Fallback to current month start if parsing fails
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
        elif data_type == 'bess_v1':
            return model.objects.filter(
                month=instance.month,
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
        elif data_type == 'bess_v1':
            return model.objects.filter(
                month=instance.month,
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
                
                # Try different date formats (including formats like "01-Nov-25")
                date_obj = None
                for fmt in ['%d-%b-%y', '%d-%b-%Y', '%d/%b/%y', '%d/%b/%Y', 
                           '%m/%d/%Y', '%Y-%m-%d', '%d/%m/%Y', '%d-%m-%Y', '%Y/%m/%d']:
                    try:
                        date_obj = pd.to_datetime(date_str, format=fmt).date()
                        break
                    except:
                        continue
                
                if not date_obj:
                    try:
                        # Try pandas' flexible date parser as fallback (handles various formats)
                        date_obj = pd.to_datetime(date_str, dayfirst=True).date()
                    except:
                        print(f"Could not parse date: {date_str}")
                        continue
                
                # Process each asset column
                for asset_col in asset_cols:
                    asset_code = asset_col.strip()
                    value = row[asset_col]
                    
                    # Skip only empty or null values (allow 0 values to be processed)
                    if pd.isna(value) or value == '':
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