"""
Serializers for Sales Dashboard endpoints (React app).
"""

from rest_framework import serializers


class SalesYieldDataSerializer(serializers.Serializer):
    """Serializer for yield data in sales dashboard"""
    month = serializers.CharField(required=False, allow_blank=True)
    country = serializers.CharField(required=False, allow_blank=True)
    portfolio = serializers.CharField(required=False, allow_blank=True)
    assetno = serializers.CharField(required=False, allow_blank=True)
    dc_capacity_mw = serializers.FloatField(required=False, allow_null=True)
    ic_approved_budget = serializers.FloatField(required=False, allow_null=True)
    expected_budget = serializers.FloatField(required=False, allow_null=True)
    weather_loss_or_gain = serializers.FloatField(required=False, allow_null=True)
    grid_curtailment = serializers.FloatField(required=False, allow_null=True)
    grid_outage = serializers.FloatField(required=False, allow_null=True)
    operation_budget = serializers.FloatField(required=False, allow_null=True)
    breakdown_loss = serializers.FloatField(required=False, allow_null=True)
    unclassified_loss = serializers.FloatField(required=False, allow_null=True)
    actual_generation = serializers.FloatField(required=False, allow_null=True)
    string_failure = serializers.FloatField(required=False, allow_null=True)
    inverter_failure = serializers.FloatField(required=False, allow_null=True)
    mv_failure = serializers.FloatField(required=False, allow_null=True)
    hv_failure = serializers.FloatField(required=False, allow_null=True)
    expected_pr = serializers.FloatField(required=False, allow_null=True)
    actual_pr = serializers.FloatField(required=False, allow_null=True)
    pr_gap = serializers.FloatField(required=False, allow_null=True)
    pr_gap_observation = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    pr_gap_action_need_to_taken = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    revenue_loss = serializers.FloatField(required=False, allow_null=True)
    revenue_loss_observation = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    revenue_loss_action_need_to_taken = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    actual_irradiation = serializers.FloatField(required=False, allow_null=True)
    ac_capacity_mw = serializers.FloatField(required=False, allow_null=True)
    bess_capacity_mwh = serializers.FloatField(required=False, allow_null=True)
    bess_generation_mwh = serializers.FloatField(required=False, allow_null=True)
    ppa_rate = serializers.FloatField(required=False, allow_null=True)
    ic_approved_budget_dollar = serializers.FloatField(required=False, allow_null=True)
    expected_budget_dollar = serializers.FloatField(required=False, allow_null=True)
    actual_generation_dollar = serializers.FloatField(required=False, allow_null=True)
    operational_budget_dollar = serializers.FloatField(required=False, allow_null=True)
    revenue_loss_op = serializers.FloatField(required=False, allow_null=True)
    created_at = serializers.DateTimeField(required=False, allow_null=True)
    updated_at = serializers.DateTimeField(required=False, allow_null=True)


class SalesMapDataSerializer(serializers.Serializer):
    """Serializer for map data in sales dashboard"""
    asset_no = serializers.CharField(required=False, allow_blank=True)
    country = serializers.CharField(required=False, allow_blank=True)
    portfolio = serializers.CharField(required=False, allow_blank=True)
    site_name = serializers.CharField(required=False, allow_blank=True)
    dc_capacity_mwp = serializers.FloatField(required=False, allow_null=True)
    battery_capacity_mw = serializers.FloatField(required=False, allow_null=True)
    plant_type = serializers.CharField(required=False, allow_blank=True)
    installation_type = serializers.CharField(required=False, allow_blank=True)
    latitude = serializers.FloatField(required=False, allow_null=True)
    longitude = serializers.FloatField(required=False, allow_null=True)


class SalesDataSerializer(serializers.Serializer):
    """Serializer for complete sales dashboard data"""
    yieldData = SalesYieldDataSerializer(many=True, required=False, allow_empty=True)
    mapData = SalesMapDataSerializer(many=True, required=False, allow_empty=True)

