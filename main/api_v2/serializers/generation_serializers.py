"""
Serializers for Generation Report endpoints (React app).
"""

from rest_framework import serializers
from shared_app.serializers.base_serializers import PaginatedResponseSerializer


class GenerationDailyDataSerializer(serializers.Serializer):
    """Serializer for daily data in wide format (date rows, asset columns)"""
    Date = serializers.CharField()
    # Dynamic asset columns will be included as-is in the dict


class YieldDataRowSerializer(serializers.Serializer):
    """Serializer for yield data row"""
    assetno = serializers.CharField(required=False, allow_blank=True)
    dc_capacity_mw = serializers.FloatField(required=False, allow_null=True)
    month = serializers.CharField(required=False, allow_blank=True)
    country = serializers.CharField(required=False, allow_blank=True)
    portfolio = serializers.CharField(required=False, allow_blank=True)
    ic_approved_budget_dollar = serializers.FloatField(required=False, allow_null=True)
    expected_budget_dollar = serializers.FloatField(required=False, allow_null=True)
    actual_generation_dollar = serializers.FloatField(required=False, allow_null=True)
    operational_budget_dollar = serializers.FloatField(required=False, allow_null=True)
    revenue_loss_op = serializers.FloatField(required=False, allow_null=True)
    ppa_rate = serializers.FloatField(required=False, allow_null=True)


class MapDataRowSerializer(serializers.Serializer):
    """Serializer for map data row"""
    asset_no = serializers.CharField(required=False, allow_blank=True)
    dc_capacity_mwp = serializers.FloatField(required=False, allow_null=True)
    country = serializers.CharField(required=False, allow_blank=True)
    portfolio = serializers.CharField(required=False, allow_blank=True)


class DateRangeSerializer(serializers.Serializer):
    """Serializer for date range"""
    min = serializers.CharField()
    max = serializers.CharField()


class GenerationReportDataSerializer(serializers.Serializer):
    """Serializer for complete generation report data"""
    icApprovedBudgetDaily = serializers.ListField(
        child=serializers.DictField(),
        required=False,
        allow_empty=True
    )
    expectedBudgetDaily = serializers.ListField(
        child=serializers.DictField(),
        required=False,
        allow_empty=True
    )
    actualGenerationDaily = serializers.ListField(
        child=serializers.DictField(),
        required=False,
        allow_empty=True
    )
    budgetGIIDaily = serializers.ListField(
        child=serializers.DictField(),
        required=False,
        allow_empty=True
    )
    actualGIIDaily = serializers.ListField(
        child=serializers.DictField(),
        required=False,
        allow_empty=True
    )
    yieldData = YieldDataRowSerializer(many=True, required=False, allow_empty=True)
    mapData = MapDataRowSerializer(many=True, required=False, allow_empty=True)
    latestReportDate = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    dateRange = DateRangeSerializer(required=False, allow_null=True)

