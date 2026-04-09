"""
URL Encryption Middleware
Transparently handles encrypted URLs without disrupting existing functionality
"""
from django.http import HttpResponseRedirect
from django.urls import resolve, Resolver404
from django.utils.deprecation import MiddlewareMixin
from django.conf import settings
from .encryption import url_encryption, is_encrypted_url, decrypt_url
import logging

logger = logging.getLogger(__name__)

class URLEncryptionMiddleware(MiddlewareMixin):
    """
    Middleware to handle encrypted URLs
    
    This middleware:
    1. Intercepts requests with encrypted URLs
    2. Decrypts the URL to get the original path
    3. Redirects to the original path
    4. Keeps existing URLs working normally
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
        super().__init__(get_response)
    
    def process_request(self, request):
        """Process incoming requests to handle encrypted URLs"""
        
        # Get the current path
        path = request.path
        
        # Skip if path is too short to be encrypted
        if len(path) < 10:
            return None
        
        # Check if this is an encrypted URL
        if is_encrypted_url(path[1:]) and not path.startswith('/admin/'):
            try:
                # Decrypt the URL (remove leading slash for decryption)
                original_path, extra_data = decrypt_url(path[1:])
                
                if original_path:
                    # Log the decryption (optional - remove in production)
                    logger.info(f"Decrypted URL: {path} -> {original_path}")
                    
                    # Add extra data to request if present
                    if extra_data:
                        request.encrypted_data = extra_data
                    
                    # Redirect to original path
                    return HttpResponseRedirect(original_path)
                
            except Exception as e:
                logger.error(f"URL decryption failed for {path}: {str(e)}")
                # Continue with original request if decryption fails
        
        return None
    
    def process_response(self, request, response):
        """Process outgoing responses to add encryption helpers"""
        
        # Add encryption helper to request object for templates
        if hasattr(request, 'user') and request.user.is_authenticated:
            request.encrypt_url = lambda path: url_encryption.encrypt_url(path)
        
        return response
