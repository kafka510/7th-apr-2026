"""
URL Encryption Security Module
Provides URL obfuscation and encryption capabilities
"""

from .encryption import URLEncryption, encrypt_url, decrypt_url, is_encrypted_url

# Lazy import of middleware to avoid circular imports during Django startup
def get_URLEncryptionMiddleware():
    from .middleware import URLEncryptionMiddleware
    return URLEncryptionMiddleware

__all__ = [
    'URLEncryption',
    'encrypt_url', 
    'decrypt_url',
    'is_encrypted_url',
    'get_URLEncryptionMiddleware'
]
