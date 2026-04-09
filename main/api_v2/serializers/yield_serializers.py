"""
Serializers for Yield Report endpoints (React app).
"""

from rest_framework import serializers
from shared_app.serializers.base_serializers import PaginatedResponseSerializer


class YieldDataEntrySerializer(serializers.Serializer):
    """Serializer for individual yield data entry"""
    month = serializers.CharField(required=False, allow_blank=True)
    country = serializers.CharField(required=False, allow_blank=True)
    portfolio = serializers.CharField(required=False, allow_blank=True)
    assetno = serializers.CharField(required=False, allow_blank=True)
    dc_capacity_mw = serializers.FloatField(required=False, allow_null=True)
    ic_approved_budget = serializers.FloatField(required=False, allow_null=True)
    expected_budget = serializers.FloatField(required=False, allow_null=True)
    weather_loss_or_gain = serializers.FloatField(required=False, allow_null=True)
    grid_curtailment = serializers.FloatField(required=False, allow_null=True)
    budgeted_grid_curtailment = serializers.FloatField(required=False, allow_null=True)
    grid_outage = serializers.FloatField(required=False, allow_null=True)
    operation_budget = serializers.FloatField(required=False, allow_null=True)
    breakdown_loss = serializers.FloatField(required=False, allow_null=True)
    scheduled_outage_loss = serializers.FloatField(required=False, allow_null=True)
    unclassified_loss = serializers.FloatField(required=False, allow_null=True)
    actual_generation = serializers.FloatField(required=False, allow_null=True)
    string_failure = serializers.FloatField(required=False, allow_null=True)
    inverter_failure = serializers.FloatField(required=False, allow_null=True)
    ac_failure = serializers.FloatField(required=False, allow_null=True)
    
    def to_representation(self, instance):
        """Add space versions of failure fields for frontend compatibility"""
        ret = super().to_representation(instance)
        # Add space versions (frontend expects 'string failure', 'inverter failure', 'ac failure')
        # Check original instance first (ViewSet may have added space versions)
        if isinstance(instance, dict):
            if 'string failure' in instance:
                ret['string failure'] = instance['string failure']
            elif 'string_failure' in ret:
                ret['string failure'] = ret['string_failure']
            
            if 'inverter failure' in instance:
                ret['inverter failure'] = instance['inverter failure']
            elif 'inverter_failure' in ret:
                ret['inverter failure'] = ret['inverter_failure']
            
            if 'ac failure' in instance:
                ret['ac failure'] = instance['ac failure']
            elif 'ac_failure' in ret:
                ret['ac failure'] = ret['ac_failure']
        else:
            # If instance is not a dict, derive from underscore versions
            if 'string_failure' in ret:
                ret['string failure'] = ret['string_failure']
            if 'inverter_failure' in ret:
                ret['inverter failure'] = ret['inverter_failure']
            if 'ac_failure' in ret:
                ret['ac failure'] = ret['ac_failure']
        return ret
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
    remarks = serializers.CharField(required=False, allow_blank=True, allow_null=True)


class YieldDataResponseSerializer(PaginatedResponseSerializer):
    """Serializer for yield data list response"""
    results = YieldDataEntrySerializer(many=True)


class YieldFilterOptionsSerializer(serializers.Serializer):
    """Serializer for filter options"""
    months = serializers.ListField(child=serializers.CharField())
    years = serializers.ListField(child=serializers.CharField())
    countries = serializers.ListField(child=serializers.CharField())
    portfolios = serializers.ListField(child=serializers.CharField())
    assets = serializers.ListField(child=serializers.CharField())


class YieldDataWithOptionsResponseSerializer(PaginatedResponseSerializer):
    """Serializer for yield data response with filter options"""
    results = YieldDataEntrySerializer(many=True)
    filter_options = YieldFilterOptionsSerializer(required=False, allow_null=True)

