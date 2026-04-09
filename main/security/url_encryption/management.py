"""
URL Encryption Management Utilities
Provides functions to generate and manage encrypted URLs
"""
from django.urls import get_resolver
from .encryption import url_encryption

def generate_encrypted_urls_for_app(app_name='main'):
    """
    Generate encrypted URLs for all views in an app
    
    Args:
        app_name (str): Name of the Django app
    
    Returns:
        dict: Dictionary mapping view names to encrypted URLs
    """
    resolver = get_resolver()
    encrypted_urls = {}
    
    # Get all URL patterns from the specified app
    for pattern in resolver.url_patterns:
        if hasattr(pattern, 'app_name') and pattern.app_name == app_name:
            for url_pattern in pattern.url_patterns:
                if hasattr(url_pattern, 'name') and url_pattern.name:
                    try:
                        from django.urls import reverse
                        original_url = reverse(f'{app_name}:{url_pattern.name}')
                        encrypted_url = url_encryption.encrypt_url(original_url)
                        encrypted_urls[url_pattern.name] = {
                            'original': original_url,
                            'encrypted': encrypted_url,
                            'view_name': url_pattern.name
                        }
                    except Exception as e:
                        encrypted_urls[url_pattern.name] = {
                            'error': str(e),
                            'view_name': url_pattern.name
                        }
    
    return encrypted_urls

def test_url_encryption(url_path):
    """
    Test URL encryption/decryption cycle
    
    Args:
        url_path (str): URL path to test
    
    Returns:
        dict: Test results
    """
    try:
        # Encrypt
        encrypted = url_encryption.encrypt_url(url_path)
        
        # Decrypt
        decrypted_path, extra_data = url_encryption.decrypt_url(encrypted)
        
        return {
            'success': True,
            'original': url_path,
            'encrypted': encrypted,
            'decrypted': decrypted_path,
            'extra_data': extra_data,
            'cycle_success': url_path == decrypted_path
        }
    
    except Exception as e:
        return {
            'success': False,
            'error': str(e),
            'original': url_path
        }

def get_encryption_stats():
    """
    Get encryption system statistics
    
    Returns:
        dict: Encryption statistics
    """
    try:
        # Test encryption with a sample URL
        test_url = '/test-encryption/'
        encrypted = url_encryption.encrypt_url(test_url)
        decrypted, _ = url_encryption.decrypt_url(encrypted)
        
        return {
            'encryption_working': True,
            'test_url': test_url,
            'encrypted_length': len(encrypted),
            'decryption_success': test_url == decrypted,
            'key_available': bool(url_encryption.key)
        }
    
    except Exception as e:
        return {
            'encryption_working': False,
            'error': str(e)
        }
