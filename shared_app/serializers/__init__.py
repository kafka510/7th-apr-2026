"""
Shared serializers module.
"""

# Import serializers only if rest_framework is available
try:
    from .base_serializers import (
        TimestampedSerializer,
        PaginatedResponseSerializer,
        ErrorResponseSerializer,
    )
    __all__ = [
        'TimestampedSerializer',
        'PaginatedResponseSerializer',
        'ErrorResponseSerializer',
    ]
except ImportError:
    # rest_framework not available
    __all__ = []

