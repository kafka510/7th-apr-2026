"""
Secure Static and Media File Serving
------------------------------------
Serves static and media files with authentication requirements.
Login page assets are whitelisted for public access.

Works in both development and production environments:
- Development: Uses STATICFILES_DIRS to find files
- Production: Uses STATIC_ROOT (collected static files)
- Handles WhiteNoise manifest files for hashed filenames
"""

import os
import json
import mimetypes
import hashlib
from pathlib import Path
from django.conf import settings
from django.http import HttpResponse, HttpResponseForbidden, HttpResponseNotFound, FileResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.cache import cache_control
from django.utils.http import http_date
from django.contrib.auth.decorators import login_required
from django.core.exceptions import SuspiciousFileOperation
from django.contrib.staticfiles.storage import staticfiles_storage
import logging

logger = logging.getLogger(__name__)

# Whitelist of static files that can be accessed without authentication
# These are only the files needed for the login page
LOGIN_PAGE_ASSETS_WHITELIST = {
    'PEAK_LOGO.jpg',
    'PEAK_LOGO.55e2671ed43f.jpg',  # Versioned filename
    'solar-bg.jpg',
}

# Additional whitelist patterns for login page assets (if needed)
LOGIN_PAGE_ASSETS_PATTERNS = [
    r'^PEAK_LOGO.*\.jpg$',  # Any versioned logo
    r'^solar-bg\.jpg$',
]


def is_login_page_asset(filename):
    """
    Check if a file is in the login page assets whitelist.
    """
    # Check exact match
    if filename in LOGIN_PAGE_ASSETS_WHITELIST:
        return True
    
    # Check pattern match
    import re
    for pattern in LOGIN_PAGE_ASSETS_PATTERNS:
        if re.match(pattern, filename):
            return True
    
    return False


def serve_static_file(request, file_path):
    """
    Serve static files with authentication.
    Login page assets are publicly accessible.
    All other files require authentication.
    """
    # Normalize the path - remove leading slashes
    file_path = file_path.lstrip('/')
    
    # Security: Prevent directory traversal and absolute paths
    if '..' in file_path or os.path.isabs(file_path):
        logger.warning(f"Directory traversal attempt: {file_path} from IP {request.META.get('REMOTE_ADDR')}")
        return HttpResponseForbidden("Invalid file path")
    
    # Security: Prevent accessing hidden files or system files
    if file_path.startswith('.') or '/.' in file_path:
        logger.warning(f"Attempt to access hidden file: {file_path} from IP {request.META.get('REMOTE_ADDR')}")
        return HttpResponseForbidden("Access denied")
    
    # Get the filename for whitelist checking
    filename = os.path.basename(file_path)
    
    # Check if it's a login page asset
    is_login_asset = is_login_page_asset(filename)
    
    # If not a login asset, require authentication
    if not is_login_asset:
        if not request.user.is_authenticated:
            # Log unauthorized access attempts for security monitoring
            logger.warning(f"Unauthenticated access attempt to static file: {file_path} from IP {request.META.get('REMOTE_ADDR')}")
            return HttpResponseForbidden("Authentication required to access this file")
    
    # Log successful access (debug level in development, info in production for security monitoring)
    if settings.DEBUG:
        logger.debug(f"Static file access: {file_path}, is_login_asset: {is_login_asset}, user: {request.user.username if request.user.is_authenticated else 'Anonymous'}")
    else:
        # Production: log all static file access for security monitoring
        logger.info(f"Static file access: {file_path}, is_login_asset: {is_login_asset}, user: {request.user.username if request.user.is_authenticated else 'Anonymous'}, IP: {request.META.get('REMOTE_ADDR')}")
    
    # Build full file path
    # Use Django's staticfiles storage to handle both dev and prod environments
    # This also handles WhiteNoise manifest files for hashed filenames
    full_path = None
    
    try:
        # Try using Django's staticfiles storage (handles WhiteNoise manifest)
        # This works in both dev and prod, and handles hashed filenames
        if hasattr(staticfiles_storage, 'url') and hasattr(staticfiles_storage, 'path'):
            try:
                # Check if file exists in storage
                if staticfiles_storage.exists(file_path):
                    full_path = staticfiles_storage.path(file_path)
            except (ValueError, OSError) as e:
                # Storage might not support path() in all cases
                logger.debug(f"Storage path() not available: {e}")
        
        # Fallback: Direct file system lookup
        if not full_path or not os.path.exists(full_path):
            # Check STATIC_ROOT first (production - collected files)
            if hasattr(settings, 'STATIC_ROOT') and settings.STATIC_ROOT and os.path.exists(settings.STATIC_ROOT):
                static_root_path = os.path.join(settings.STATIC_ROOT, file_path)
                if os.path.exists(static_root_path) and os.path.isfile(static_root_path):
                    full_path = static_root_path
            
            # Check STATICFILES_DIRS (development)
            if (not full_path or not os.path.exists(full_path)) and hasattr(settings, 'STATICFILES_DIRS'):
                for static_dir in settings.STATICFILES_DIRS:
                    static_dir_path = os.path.join(static_dir, file_path)
                    if os.path.exists(static_dir_path) and os.path.isfile(static_dir_path):
                        full_path = static_dir_path
                        break
            
            # If still not found, try the static directory directly (fallback)
            if not full_path or not os.path.exists(full_path):
                base_dir = Path(settings.BASE_DIR)
                static_path = base_dir / 'static' / file_path
                if static_path.exists() and static_path.is_file():
                    full_path = str(static_path)
            
            # Handle WhiteNoise manifest for hashed filenames (production)
            if (not full_path or not os.path.exists(full_path)) and hasattr(settings, 'STATIC_ROOT') and settings.STATIC_ROOT:
                manifest_path = os.path.join(settings.STATIC_ROOT, 'staticfiles.json')
                if os.path.exists(manifest_path):
                    try:
                        with open(manifest_path, 'r') as f:
                            manifest = json.load(f)
                            # Look for the file in manifest (handles hashed filenames)
                            if file_path in manifest.get('paths', {}):
                                hashed_path = manifest['paths'][file_path]
                                full_hashed_path = os.path.join(settings.STATIC_ROOT, hashed_path)
                                if os.path.exists(full_hashed_path):
                                    full_path = full_hashed_path
                    except (json.JSONDecodeError, KeyError, IOError) as e:
                        logger.debug(f"Could not read WhiteNoise manifest: {e}")
    
    except Exception as e:
        logger.error(f"Error locating static file {file_path}: {e}")
    
    if not full_path or not os.path.exists(full_path):
        logger.warning(f"Static file not found: {file_path} (DEBUG={settings.DEBUG}, STATIC_ROOT={getattr(settings, 'STATIC_ROOT', 'Not set')})")
        return HttpResponseNotFound("File not found")
    
    # Security: Ensure the resolved path is within allowed directories
    try:
        full_path_abs = os.path.abspath(full_path)
        # Verify it's within STATIC_ROOT or STATICFILES_DIRS
        allowed = False
        
        # Check STATIC_ROOT (production)
        if hasattr(settings, 'STATIC_ROOT') and settings.STATIC_ROOT:
            static_root_abs = os.path.abspath(settings.STATIC_ROOT)
            if full_path_abs.startswith(static_root_abs):
                allowed = True
        
        # Check STATICFILES_DIRS (development)
        if not allowed and hasattr(settings, 'STATICFILES_DIRS'):
            for static_dir in settings.STATICFILES_DIRS:
                static_dir_abs = os.path.abspath(static_dir)
                if full_path_abs.startswith(static_dir_abs):
                    allowed = True
                    break
        
        # Fallback: Check base static directory
        if not allowed:
            base_static = os.path.abspath(os.path.join(settings.BASE_DIR, 'static'))
            if full_path_abs.startswith(base_static):
                allowed = True
        
        if not allowed:
            logger.error(f"Security violation: Attempted access outside static directories: {full_path_abs}")
            logger.error(f"STATIC_ROOT: {getattr(settings, 'STATIC_ROOT', 'Not set')}")
            logger.error(f"STATICFILES_DIRS: {getattr(settings, 'STATICFILES_DIRS', 'Not set')}")
            return HttpResponseForbidden("Access denied")
    except Exception as e:
        logger.error(f"Error validating static file path: {e}")
        return HttpResponseForbidden("Invalid file path")
    
    # Determine content type
    content_type, encoding = mimetypes.guess_type(full_path)
    if not content_type:
        content_type = 'application/octet-stream'
    
    # Serve the file
    try:
        # Use context manager to ensure file is closed properly
        file_handle = open(full_path, 'rb')
        response = FileResponse(file_handle, content_type=content_type)
        
        # Set appropriate headers
        file_size = os.path.getsize(full_path)
        response['Content-Length'] = file_size
        
        # Cache control - environment-specific caching
        # In production, use longer cache times since files are hashed/versioned
        if settings.DEBUG:
            # Development: shorter cache to see changes immediately
            if is_login_asset:
                response['Cache-Control'] = 'public, max-age=300'  # 5 minutes
            else:
                response['Cache-Control'] = 'private, max-age=60'  # 1 minute
            # Add no-cache for development to ensure fresh files during development
            response['Pragma'] = 'no-cache'
        else:
            # Production: longer cache since files are versioned/hashed
            if is_login_asset:
                response['Cache-Control'] = 'public, max-age=86400'  # 24 hours
            else:
                response['Cache-Control'] = 'private, max-age=3600'  # 1 hour
        
        # Set last modified for cache validation
        stat = os.stat(full_path)
        response['Last-Modified'] = http_date(stat.st_mtime)
        
        # Add ETag for better caching (optional but recommended)
        etag = hashlib.md5(f"{full_path}{stat.st_mtime}".encode()).hexdigest()
        response['ETag'] = f'"{etag}"'
        
        # Log successful access (only in DEBUG mode to avoid log spam)
        if settings.DEBUG:
            logger.debug(f"Serving static file: {file_path} ({file_size} bytes) - Login asset: {is_login_asset}")
        
        return response
        
    except IOError as e:
        logger.error(f"Error reading static file {file_path}: {e}")
        return HttpResponseNotFound("Error reading file")
    except PermissionError as e:
        logger.error(f"Permission denied accessing static file {file_path}: {e}")
        return HttpResponseForbidden("Permission denied")
    except Exception as e:
        logger.error(f"Unexpected error serving static file {file_path}: {e}", exc_info=True)
        return HttpResponseNotFound("Error serving file")


@require_http_methods(["GET", "HEAD"])
def serve_media_file(request, file_path):
    """
    Serve media files - ALWAYS requires authentication.
    Media files are user-uploaded content and should never be public.
    """
    # Require authentication for all media files
    if not request.user.is_authenticated:
        logger.warning(f"Unauthenticated access attempt to media file: {file_path} from IP {request.META.get('REMOTE_ADDR')}")
        return HttpResponseForbidden("Authentication required to access media files")
    
    # Normalize the path
    file_path = file_path.lstrip('/')
    
    # Security: Prevent directory traversal
    if '..' in file_path or file_path.startswith('/'):
        logger.warning(f"Directory traversal attempt in media: {file_path} from IP {request.META.get('REMOTE_ADDR')}")
        return HttpResponseForbidden("Invalid file path")
    
    # Build full file path
    if not hasattr(settings, 'MEDIA_ROOT') or not settings.MEDIA_ROOT:
        return HttpResponseNotFound("Media root not configured")
    
    full_path = os.path.join(settings.MEDIA_ROOT, file_path)
    full_path = os.path.normpath(full_path)
    
    # Security: Ensure the resolved path is within MEDIA_ROOT
    media_root = os.path.abspath(settings.MEDIA_ROOT)
    full_path_abs = os.path.abspath(full_path)
    
    if not full_path_abs.startswith(media_root):
        logger.error(f"Security violation: Attempted access outside media root: {full_path_abs}")
        return HttpResponseForbidden("Access denied")
    
    if not os.path.exists(full_path) or not os.path.isfile(full_path):
        logger.warning(f"Media file not found: {file_path}")
        return HttpResponseNotFound("File not found")
    
    # Determine content type
    content_type, encoding = mimetypes.guess_type(full_path)
    if not content_type:
        content_type = 'application/octet-stream'
    
    # Serve the file
    try:
        # Use context manager to ensure file is closed properly
        file_handle = open(full_path, 'rb')
        response = FileResponse(file_handle, content_type=content_type)
        
        # Set appropriate headers
        file_size = os.path.getsize(full_path)
        response['Content-Length'] = file_size
        
        # Media files should not be cached publicly - always require revalidation
        if settings.DEBUG:
            response['Cache-Control'] = 'private, no-cache, must-revalidate'
        else:
            response['Cache-Control'] = 'private, max-age=300'  # 5 minutes
        
        # Set last modified for cache validation
        stat = os.stat(full_path)
        response['Last-Modified'] = http_date(stat.st_mtime)
        
        # Add ETag for better caching
        etag = hashlib.md5(f"{full_path}{stat.st_mtime}".encode()).hexdigest()
        response['ETag'] = f'"{etag}"'
        
        # Log successful access (only in DEBUG mode)
        if settings.DEBUG:
            logger.debug(f"Serving media file: {file_path} ({file_size} bytes) for user: {request.user.username}")
        
        return response
        
    except IOError as e:
        logger.error(f"Error reading media file {file_path}: {e}")
        return HttpResponseNotFound("Error reading file")
    except PermissionError as e:
        logger.error(f"Permission denied accessing media file {file_path}: {e}")
        return HttpResponseForbidden("Permission denied")
    except Exception as e:
        logger.error(f"Unexpected error serving media file {file_path}: {e}", exc_info=True)
        return HttpResponseNotFound("Error serving file")
