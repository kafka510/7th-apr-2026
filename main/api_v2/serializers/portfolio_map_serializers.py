"""
Serializers for Portfolio Map endpoints (React app).
"""

import math
from rest_framework import serializers


class SafeFloatField(serializers.FloatField):
    """FloatField that safely handles string values like '-' during serialization"""
    def to_representation(self, value):
        """Handle serialization - convert value to float or None"""
        if value is None:
            return None
        if isinstance(value, str):
            value = value.strip()
            if not value or value == '-' or value == '':
                return None
            try:
                return float(value)
            except (ValueError, TypeError):
                return None
        if isinstance(value, float) and math.isnan(value):
            return None
        try:
            return float(value)
        except (ValueError, TypeError):
            return None


class MapDataEntrySerializer(serializers.Serializer):
    """Serializer for map data entry"""
    id = serializers.IntegerField(required=False, allow_null=True)
    asset_no = serializers.CharField(required=False, allow_blank=True)
    country = serializers.CharField(required=False, allow_blank=True)
    site_name = serializers.CharField(required=False, allow_blank=True)
    portfolio = serializers.CharField(required=False, allow_blank=True)
    installation_type = serializers.CharField(required=False, allow_blank=True)
    dc_capacity_mwp = serializers.FloatField(required=False, allow_null=True)
    pcs_capacity = serializers.FloatField(required=False, allow_null=True)
    battery_capacity_mw = serializers.FloatField(required=False, allow_null=True)
    plant_type = serializers.CharField(required=False, allow_blank=True)
    offtaker = serializers.CharField(required=False, allow_blank=True)
    cod = serializers.CharField(required=False, allow_blank=True)
    latitude = serializers.SerializerMethodField()
    longitude = serializers.SerializerMethodField()
    created_at = serializers.DateTimeField(required=False, allow_null=True)
    updated_at = serializers.DateTimeField(required=False, allow_null=True)
    
    def get_latitude(self, obj):
        """Safely convert latitude to float or None"""
        # obj is a dict when passed from ViewSet
        value = obj.get('latitude') if isinstance(obj, dict) else getattr(obj, 'latitude', None)
        return self._safe_float(value)
    
    def get_longitude(self, obj):
        """Safely convert longitude to float or None"""
        # obj is a dict when passed from ViewSet
        value = obj.get('longitude') if isinstance(obj, dict) else getattr(obj, 'longitude', None)
        return self._safe_float(value)
    
    def _safe_float(self, value):
        """Helper to safely convert value to float or None"""
        if value is None:
            return None
        if isinstance(value, str):
            value = value.strip()
            if not value or value == '-' or value == '':
                return None
            try:
                return float(value)
            except (ValueError, TypeError):
                return None
        if isinstance(value, float) and math.isnan(value):
            return None
        try:
            return float(value)
        except (ValueError, TypeError):
            return None
    
    def to_representation(self, instance):
        """Override to ensure latitude/longitude are properly handled"""
        ret = super().to_representation(instance)
        # Ensure latitude and longitude are None if they were invalid strings
        if 'latitude' in ret and ret['latitude'] is None:
            ret['latitude'] = None
        if 'longitude' in ret and ret['longitude'] is None:
            ret['longitude'] = None
        return ret


class PortfolioMapYieldDataSerializer(serializers.Serializer):
    """Serializer for yield data in portfolio map"""
    month = serializers.CharField(required=False, allow_blank=True)
    country = serializers.CharField(required=False, allow_blank=True)
    portfolio = serializers.CharField(required=False, allow_blank=True)
    assetno = serializers.CharField(required=False, allow_blank=True)
    dc_capacity_mw = serializers.FloatField(required=False, allow_null=True)
    ic_approved_budget = serializers.FloatField(required=False, allow_null=True)
    expected_budget = serializers.FloatField(required=False, allow_null=True)
    actual_generation = serializers.FloatField(required=False, allow_null=True)
    created_at = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    updated_at = serializers.CharField(required=False, allow_blank=True, allow_null=True)


class PortfolioMapDataSerializer(serializers.Serializer):
    """Serializer for complete portfolio map data"""
    mapData = MapDataEntrySerializer(many=True, required=False, allow_empty=True)
    yieldData = PortfolioMapYieldDataSerializer(many=True, required=False, allow_empty=True)

