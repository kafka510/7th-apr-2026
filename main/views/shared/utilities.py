"""
Shared utility functions for views
"""
import pandas as pd
import chardet
import pytz
from datetime import datetime, timezone, timedelta
from django.db.models import Q
from ...models import UserProfile, AssetList
from main.permissions import user_has_capability


def dt_to_utc(ts, tz):   
    """Convert timestamp to UTC with timezone offset"""
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
        
        # Users with global site access capability get all sites
        if user_has_capability(request.user, 'ticketing.view_all_sites'):
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


def filter_data_by_user_sites(queryset, asset_field_name, request):
    """
    Filter queryset based on user's accessible sites.
    asset_field_name: The field name in the model that contains the asset code
    """
    accessible_sites = get_user_accessible_sites(request)
    
    if accessible_sites and accessible_sites.exists():
        # Match using both asset_number and asset_code to handle mixed datasets.
        asset_numbers = list(accessible_sites.values_list('asset_number', flat=True))
        asset_codes = list(accessible_sites.values_list('asset_code', flat=True))
        asset_numbers = [a for a in asset_numbers if a]
        asset_codes = [a for a in asset_codes if a]

        if not asset_numbers and not asset_codes:
            return queryset.none()

        # Filter by either identifier type.
        filtered_queryset = queryset.filter(
            Q(**{f"{asset_field_name}__in": asset_numbers}) |
            Q(**{f"{asset_field_name}__in": asset_codes})
        )
        return filtered_queryset
    else:
        # User has no accessible sites, return empty queryset
        return queryset.none()


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
        
        if result['encoding']:
            detected_encoding = result['encoding'].lower()
            confidence = result.get('confidence', 0)
            
            # Handle common encoding aliases and improve detection
            encoding_mapping = {
                'ascii': 'utf-8',  # ASCII is subset of UTF-8
                'windows-1252': 'cp1252',
                'iso-8859-1': 'latin1',
                'shift_jis': 'shift_jis',
                'cp932': 'cp932',
                'euc-jp': 'euc-jp'
            }
            
            # Map to preferred encoding if available
            final_encoding = encoding_mapping.get(detected_encoding, detected_encoding)
            
            print(f"File encoding detected: {detected_encoding} (confidence: {confidence:.2f}) -> using: {final_encoding}")
            return final_encoding
        else:
            print("Could not detect file encoding, defaulting to utf-8")
            return 'utf-8'
            
    except Exception as e:
        print(f"Error detecting file encoding: {str(e)}")
        return 'utf-8'
