"""
File Upload Security Utilities
==============================
Security functions for validating file uploads to prevent security vulnerabilities.
"""

import os
import logging
from django.core.exceptions import ValidationError

logger = logging.getLogger(__name__)

# Maximum file size: 50 MB (adjust as needed)
MAX_FILE_SIZE = 50 * 1024 * 1024  # 50 MB in bytes

# Allowed file extensions for CSV uploads
ALLOWED_CSV_EXTENSIONS = {'.csv', '.txt'}

# Allowed MIME types for CSV files
ALLOWED_CSV_MIME_TYPES = {
    'text/csv',
    'text/plain',
    'application/csv',
    'text/x-csv',
    'application/vnd.ms-excel',  # Excel sometimes sends this for CSV
}

# Allowed file extensions for image uploads
ALLOWED_IMAGE_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp'}

# Allowed MIME types for images
ALLOWED_IMAGE_MIME_TYPES = {
    'image/jpeg',
    'image/jpg',
    'image/png',
    'image/gif',
    'image/bmp',
    'image/webp',
}


def validate_file_upload(file, allowed_extensions=None, allowed_mime_types=None, max_size=None):
    """
    Validate file upload for security.
    
    Args:
        file: Django UploadedFile object
        allowed_extensions: Set of allowed file extensions (e.g., {'.csv', '.txt'})
        allowed_mime_types: Set of allowed MIME types (e.g., {'text/csv'})
        max_size: Maximum file size in bytes (default: MAX_FILE_SIZE)
    
    Returns:
        tuple: (is_valid, error_message)
    
    Raises:
        ValidationError: If file validation fails
    """
    if not file:
        raise ValidationError("No file provided")
    
    # Check file size
    max_size = max_size or MAX_FILE_SIZE
    if file.size > max_size:
        raise ValidationError(
            f"File size ({file.size} bytes) exceeds maximum allowed size ({max_size} bytes / {max_size / 1024 / 1024:.1f} MB)"
        )
    
    # Get file extension
    file_name = file.name
    file_ext = os.path.splitext(file_name.lower())[1]
    
    # Get MIME type (if available)
    content_type = getattr(file, 'content_type', None)
    
    # Validate extension if whitelist provided
    if allowed_extensions:
        if file_ext not in allowed_extensions:
            raise ValidationError(
                f"File extension '{file_ext}' is not allowed. Allowed extensions: {', '.join(allowed_extensions)}"
            )
    
    # Validate MIME type if whitelist provided
    if allowed_mime_types and content_type:
        if content_type.lower() not in allowed_mime_types:
            # Log suspicious MIME type mismatch
            logger.warning(
                f"Suspicious file upload: filename={file_name}, "
                f"extension={file_ext}, content_type={content_type}"
            )
            raise ValidationError(
                f"File type '{content_type}' is not allowed. Allowed types: {', '.join(allowed_mime_types)}"
            )
    
    # Sanitize filename to prevent path traversal
    sanitized_name = sanitize_filename(file_name)
    if sanitized_name != file_name:
        logger.warning(f"Filename sanitized: '{file_name}' -> '{sanitized_name}'")
    
    return True


def validate_csv_upload(file, max_size=None):
    """
    Validate CSV file upload specifically.
    
    Args:
        file: Django UploadedFile object
        max_size: Maximum file size in bytes (default: MAX_FILE_SIZE)
    
    Returns:
        tuple: (is_valid, error_message)
    
    Raises:
        ValidationError: If file validation fails
    """
    return validate_file_upload(
        file,
        allowed_extensions=ALLOWED_CSV_EXTENSIONS,
        allowed_mime_types=ALLOWED_CSV_MIME_TYPES,
        max_size=max_size
    )


def validate_image_upload(file, max_size=None):
    """
    Validate image file upload specifically.
    
    Args:
        file: Django UploadedFile object
        max_size: Maximum file size in bytes (default: MAX_FILE_SIZE)
    
    Returns:
        tuple: (is_valid, error_message)
    
    Raises:
        ValidationError: If file validation fails
    """
    return validate_file_upload(
        file,
        allowed_extensions=ALLOWED_IMAGE_EXTENSIONS,
        allowed_mime_types=ALLOWED_IMAGE_MIME_TYPES,
        max_size=max_size
    )


def sanitize_filename(filename):
    """
    Sanitize filename to prevent path traversal and other security issues.
    
    Args:
        filename: Original filename
    
    Returns:
        str: Sanitized filename
    """
    # Remove path components
    filename = os.path.basename(filename)
    
    # Remove any null bytes
    filename = filename.replace('\x00', '')
    
    # Remove leading/trailing dots and spaces
    filename = filename.strip('. ')
    
    # Replace dangerous characters
    dangerous_chars = ['/', '\\', '..', '<', '>', ':', '"', '|', '?', '*']
    for char in dangerous_chars:
        filename = filename.replace(char, '_')
    
    # Limit filename length
    if len(filename) > 255:
        name, ext = os.path.splitext(filename)
        filename = name[:255 - len(ext)] + ext
    
    return filename


def get_file_size_mb(file):
    """Get file size in MB."""
    return file.size / (1024 * 1024)
