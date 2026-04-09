"""
Serializers for IC Budget vs Expected endpoints (React app).
"""

from rest_framework import serializers
from shared_app.serializers.base_serializers import PaginatedResponseSerializer


class ICBudgetDataEntrySerializer(serializers.Serializer):
    """Serializer for IC Budget vs Expected data entry"""
    id = serializers.IntegerField(required=False, allow_null=True)
    country = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    portfolio = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    dc_capacity_mwp = serializers.FloatField(required=False, allow_null=True)
    month = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    month_sort = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    ic_approved_budget_mwh = serializers.FloatField(required=False, allow_null=True)
    expected_budget_mwh = serializers.FloatField(required=False, allow_null=True)
    actual_generation_mwh = serializers.FloatField(required=False, allow_null=True)
    grid_curtailment_budget_mwh = serializers.FloatField(required=False, allow_null=True)
    actual_curtailment_mwh = serializers.FloatField(required=False, allow_null=True)
    budget_irradiation_kwh_m2 = serializers.FloatField(required=False, allow_null=True)
    actual_irradiation_kwh_m2 = serializers.FloatField(required=False, allow_null=True)
    expected_pr_percent = serializers.FloatField(required=False, allow_null=True)
    actual_pr_percent = serializers.FloatField(required=False, allow_null=True)
    created_at = serializers.DateTimeField(required=False, allow_null=True)
    updated_at = serializers.DateTimeField(required=False, allow_null=True)


class ICBudgetDataResponseSerializer(serializers.Serializer):
    """Serializer for IC Budget data response"""
    success = serializers.BooleanField()
    data = ICBudgetDataEntrySerializer(many=True)
    count = serializers.IntegerField()
    error = serializers.CharField(required=False, allow_blank=True, allow_null=True)

