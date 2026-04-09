"""
Custom exceptions for the application.
"""


class APIException(Exception):
    """Base API exception"""
    def __init__(self, message, status_code=400):
        self.message = message
        self.status_code = status_code
        super().__init__(self.message)


class AssetNotFoundError(APIException):
    """Raised when asset is not found"""
    def __init__(self, asset_code):
        super().__init__(f"Asset '{asset_code}' not found", status_code=404)


class PermissionDeniedError(APIException):
    """Raised when permission is denied"""
    def __init__(self, message="Permission denied"):
        super().__init__(message, status_code=403)


class ValidationError(APIException):
    """Raised when validation fails"""
    def __init__(self, message, status_code=400):
        super().__init__(message, status_code=status_code)

