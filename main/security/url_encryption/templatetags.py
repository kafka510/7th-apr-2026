"""
Template tags for URL encryption
Allows templates to generate encrypted URLs
"""
from django import template
from django.urls import reverse
from django.utils.safestring import mark_safe
from .encryption import url_encryption

register = template.Library()

@register.simple_tag
def encrypted_url(view_name, *args, **kwargs):
    """
    Generate an encrypted URL for a view
    
    Usage:
        {% encrypted_url 'dashboard' %}
        {% encrypted_url 'user_management' %}
        {% encrypted_url 'edit_user_access' user_id=123 %}
    """
    try:
        # Generate the original URL
        original_url = reverse(view_name, args=args, kwargs=kwargs)
        
        # Encrypt the URL
        encrypted_token = url_encryption.encrypt_url(original_url)
        
        return encrypted_token
    
    except Exception as e:
        # Fallback to original URL if encryption fails
        try:
            return reverse(view_name, args=args, kwargs=kwargs)
        except:
            return '#'

@register.simple_tag
def encrypted_path(path):
    """
    Encrypt an arbitrary path
    
    Usage:
        {% encrypted_path '/dashboard/' %}
        {% encrypted_path '/api/yield-data/' %}
    """
    try:
        return url_encryption.encrypt_url(path)
    except:
        return path

@register.simple_tag
def encrypted_link(text, view_name, *args, **kwargs):
    """
    Generate a complete encrypted link HTML
    
    Usage:
        {% encrypted_link "Dashboard" 'dashboard' %}
        {% encrypted_link "User Management" 'user_management' %}
    """
    try:
        encrypted_url = encrypted_url(view_name, *args, **kwargs)
        return mark_safe(f'<a href="/{encrypted_url}">{text}</a>')
    except:
        return text

@register.filter
def encrypt_url_path(path):
    """
    Filter to encrypt a URL path
    
    Usage:
        {{ "/dashboard/"|encrypt_url_path }}
        {{ some_url|encrypt_url_path }}
    """
    try:
        return url_encryption.encrypt_url(path)
    except:
        return path
