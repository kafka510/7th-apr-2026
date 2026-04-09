"""
Serializers for Data Upload API v2
"""
from rest_framework import serializers


class DataCountsSerializer(serializers.Serializer):
    yield_count = serializers.IntegerField()
    bess_count = serializers.IntegerField()
    bess_v1_count = serializers.IntegerField()
    aoc_count = serializers.IntegerField()
    ice_count = serializers.IntegerField()
    icvsexvscur_count = serializers.IntegerField()
    map_count = serializers.IntegerField()
    minamata_count = serializers.IntegerField()
    actual_generation_daily_count = serializers.IntegerField()
    expected_budget_daily_count = serializers.IntegerField()
    budget_gii_daily_count = serializers.IntegerField()
    actual_gii_daily_count = serializers.IntegerField()
    ic_approved_budget_daily_count = serializers.IntegerField()


class UploadHistoryItemSerializer(serializers.Serializer):
    file_name = serializers.CharField()
    data_type = serializers.CharField()
    upload_mode = serializers.CharField()
    import_date = serializers.DateTimeField(required=False, allow_null=True)
    records_imported = serializers.IntegerField()
    records_skipped = serializers.IntegerField()
    status = serializers.CharField()
    imported_by = serializers.CharField()
    file_size_mb = serializers.FloatField(required=False, allow_null=True)
    processing_time = serializers.FloatField(required=False, allow_null=True)
    success_rate = serializers.FloatField(required=False, allow_null=True)


class UploadHistoryResponseSerializer(serializers.Serializer):
    uploads = UploadHistoryItemSerializer(many=True)
    message = serializers.CharField(required=False, allow_null=True)


class DataPreviewResponseSerializer(serializers.Serializer):
    data = serializers.ListField(child=serializers.DictField())


class DeleteDataRequestSerializer(serializers.Serializer):
    data_type = serializers.CharField(required=True)
    delete_option = serializers.CharField(required=True)
    start_date = serializers.DateField(required=False, allow_null=True)
    end_date = serializers.DateField(required=False, allow_null=True)


class DeleteDataResponseSerializer(serializers.Serializer):
    success = serializers.BooleanField()
    message = serializers.CharField()
    deleted_count = serializers.IntegerField(required=False, allow_null=True)

