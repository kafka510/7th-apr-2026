"""
URL Encryption Core Module
Handles AES encryption/decryption for URL obfuscation
"""
import base64
import json
from cryptography.fernet import Fernet
from django.conf import settings
from django.core.cache import cache
import hashlib
import secrets

class URLEncryption:
    """Handles URL encryption and decryption using Fernet (AES 128)"""
    
    def __init__(self):
        # Use Django's SECRET_KEY as base for encryption key
        self.key = self._get_or_create_encryption_key()
        self.cipher = Fernet(self.key)
    
    def _get_or_create_encryption_key(self):
        """Get or create encryption key based on SECRET_KEY"""
        cache_key = 'url_encryption_key'
        
        # Try to get key from cache, but handle connection errors gracefully
        try:
            key = cache.get(cache_key)
        except Exception:
            # If cache is unavailable (e.g., Redis connection error), generate key directly
            key = None
        
        if not key:
            # Generate key from SECRET_KEY for consistency
            secret_hash = hashlib.sha256(settings.SECRET_KEY.encode()).digest()
            key = base64.urlsafe_b64encode(secret_hash[:32])
            
            # Try to cache the key, but don't fail if cache is unavailable
            try:
                cache.set(cache_key, key, timeout=86400)  # Cache for 24 hours
            except Exception:
                # Cache unavailable - continue without caching
                pass
        
        return key
    
    def encrypt_url(self, url_path, extra_data=None):
        """
        Encrypt a URL path with optional extra data
        
        Args:
            url_path (str): The URL path to encrypt (e.g., '/dashboard/')
            extra_data (dict): Optional extra data to include
        
        Returns:
            str: Encrypted URL token
        """
        try:
            # Prepare data to encrypt
            data = {
                'path': url_path,
                'timestamp': secrets.token_hex(8),  # Add randomness
                'extra': extra_data or {}
            }
            
            # Convert to JSON and encrypt
            json_data = json.dumps(data)
            encrypted_data = self.cipher.encrypt(json_data.encode())
            
            # Return base64 encoded token
            return base64.urlsafe_b64encode(encrypted_data).decode()
        
        except Exception as e:
            # Fallback: return original path if encryption fails
            return url_path
    
    def decrypt_url(self, encrypted_token):
        """
        Decrypt an encrypted URL token
        
        Args:
            encrypted_token (str): The encrypted token
        
        Returns:
            tuple: (url_path, extra_data) or (None, None) if decryption fails
        """
        try:
            # Decode base64
            encrypted_data = base64.urlsafe_b64decode(encrypted_token.encode())
            
            # Decrypt
            decrypted_data = self.cipher.decrypt(encrypted_data)
            data = json.loads(decrypted_data.decode())
            
            return data.get('path'), data.get('extra', {})
        
        except Exception:
            # Return None if decryption fails
            return None, None
    
    def is_encrypted_url(self, url_path):
        """Check if a URL path is encrypted"""
        try:
            # Try to decrypt - if it works, it's encrypted
            path, _ = self.decrypt_url(url_path)
            return path is not None
        except:
            return False

# Global instance
url_encryption = URLEncryption()

def encrypt_url(url_path, extra_data=None):
    """Convenience function to encrypt a URL"""
    return url_encryption.encrypt_url(url_path, extra_data)

def decrypt_url(encrypted_token):
    """Convenience function to decrypt a URL"""
    return url_encryption.decrypt_url(encrypted_token)

def is_encrypted_url(url_path):
    """Convenience function to check if URL is encrypted"""
    return url_encryption.is_encrypted_url(url_path)
