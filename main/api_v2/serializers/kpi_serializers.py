"""
Serializers for KPI endpoints (React app).
"""

from rest_framework import serializers


class KPIMetricSerializer(serializers.Serializer):
    """Serializer for individual KPI realtime metric"""
    asset_code = serializers.CharField()
    asset_number = serializers.CharField(required=False, allow_blank=True)
    asset_name = serializers.CharField(required=False, allow_blank=True)
    country = serializers.CharField(required=False, allow_blank=True)
    portfolio = serializers.CharField(required=False, allow_blank=True)
    date = serializers.CharField()
    daily_kwh = serializers.FloatField()
    daily_irr = serializers.FloatField()
    daily_generation_mwh = serializers.FloatField()
    daily_irradiation_mwh = serializers.FloatField()
    daily_ic_mwh = serializers.FloatField()
    daily_expected_mwh = serializers.FloatField()
    daily_budget_irradiation_mwh = serializers.FloatField()
    expect_pr = serializers.FloatField()
    actual_pr = serializers.FloatField()
    dc_capacity_mw = serializers.FloatField()
    last_updated = serializers.CharField(required=False, allow_null=True)
    is_frozen = serializers.BooleanField()
    capacity = serializers.FloatField()
    timezone = serializers.CharField()
    site_state = serializers.CharField(required=False, allow_null=True)


class KPIMetricsResponseSerializer(serializers.Serializer):
    """Serializer for KPI metrics list response"""
    count = serializers.IntegerField()
    results = KPIMetricSerializer(many=True)


class KPISummarySerializer(serializers.Serializer):
    """Serializer for KPI summary response"""
    total_assets = serializers.IntegerField()
    total_daily_kwh = serializers.FloatField()
    avg_daily_irr = serializers.FloatField()
    last_updated = serializers.CharField(required=False, allow_null=True)

