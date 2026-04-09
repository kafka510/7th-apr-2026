"""
Base serializer classes for DRF.
"""

from rest_framework import serializers


class TimestampedSerializer(serializers.Serializer):
    """Base serializer with timestamp fields"""
    created_at = serializers.DateTimeField(read_only=True)
    updated_at = serializers.DateTimeField(read_only=True)


class PaginatedResponseSerializer(serializers.Serializer):
    """Serializer for paginated responses"""
    count = serializers.IntegerField()
    next = serializers.URLField(allow_null=True)
    previous = serializers.URLField(allow_null=True)
    results = serializers.ListField()


class ErrorResponseSerializer(serializers.Serializer):
    """Serializer for error responses"""
    error = serializers.CharField()
    detail = serializers.CharField(required=False)
    status_code = serializers.IntegerField()

