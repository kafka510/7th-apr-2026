"""
Template tags for cache busting static files
"""
import time
import hashlib
import os
from django import template
from django.conf import settings
from django.templatetags.static import static as django_static

register = template.Library()


@register.simple_tag
def static_version(path):
    """
    Returns a static file URL with cache busting version parameter
    Usage: {% static_version 'js/gauge-charts.js' %}
    """
    url = django_static(path)
    
    # Get version from settings
    version = getattr(settings, 'STATIC_VERSION', '1.0.0')
    
    # Add version as query parameter
    separator = '&' if '?' in url else '?'
    return f"{url}{separator}v={version}"


@register.simple_tag
def static_hash(path):
    """
    Returns a static file URL with hash-based cache busting
    Usage: {% static_hash 'js/gauge-charts.js' %}
    This generates a hash based on file modification time
    """
    url = django_static(path)
    
    try:
        full_path = None
        
        # First, try STATICFILES_DIRS (for development)
        if hasattr(settings, 'STATICFILES_DIRS') and settings.STATICFILES_DIRS:
            for static_dir in settings.STATICFILES_DIRS:
                test_path = os.path.join(static_dir, path)
                if os.path.exists(test_path):
                    full_path = test_path
                    break
        
        # If not found in STATICFILES_DIRS, try STATIC_ROOT (for production)
        if not full_path and hasattr(settings, 'STATIC_ROOT') and settings.STATIC_ROOT:
            test_path = os.path.join(settings.STATIC_ROOT, path)
            if os.path.exists(test_path):
                full_path = test_path
        
        # If found, create hash from modification time
        if full_path:
            # Get file modification time
            mtime = os.path.getmtime(full_path)
            # Create a short hash
            file_hash = hashlib.md5(str(mtime).encode()).hexdigest()[:8]
            
            # Add hash as query parameter
            separator = '&' if '?' in url else '?'
            return f"{url}{separator}v={file_hash}"
    except Exception as e:
        # Fallback to version-based cache busting
        pass
    
    # Fallback to version-based cache busting
    version = getattr(settings, 'STATIC_VERSION', '1.0.0')
    separator = '&' if '?' in url else '?'
    return f"{url}{separator}v={version}"


@register.simple_tag
def static_timestamp(path):
    """
    Returns a static file URL with timestamp-based cache busting
    Usage: {% static_timestamp 'js/gauge-charts.js' %}
    This always generates a new timestamp (useful for development)
    """
    url = django_static(path)
    
    # Use current timestamp
    timestamp = str(int(time.time()))
    
    # Add timestamp as query parameter
    separator = '&' if '?' in url else '?'
    return f"{url}{separator}v={timestamp}"


@register.simple_tag
def app_version():
    """
    Returns the current application version
    Usage: {% app_version %}
    """
    return getattr(settings, 'STATIC_VERSION', '1.0.0')

