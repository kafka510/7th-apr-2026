"""
Serializers for Site Onboarding API v2
"""
from rest_framework import serializers
from shared_app.serializers.base_serializers import PaginatedResponseSerializer


class AssetListSerializer(serializers.Serializer):
    asset_code = serializers.CharField()
    asset_name = serializers.CharField()
    capacity = serializers.FloatField(required=False, allow_null=True)
    address = serializers.CharField(required=False, allow_null=True)
    country = serializers.CharField(required=False, allow_null=True)
    latitude = serializers.FloatField(required=False, allow_null=True)
    longitude = serializers.FloatField(required=False, allow_null=True)
    contact_person = serializers.CharField(required=False, allow_null=True)
    contact_method = serializers.CharField(required=False, allow_null=True)
    grid_connection_date = serializers.DateField(required=False, allow_null=True)
    asset_number = serializers.CharField(required=False, allow_null=True)
    portfolio = serializers.CharField(required=False, allow_null=True)
    timezone = serializers.CharField(required=False, allow_null=True)
    asset_name_oem = serializers.CharField(required=False, allow_null=True)
    cod = serializers.CharField(required=False, allow_null=True)
    operational_cod = serializers.CharField(required=False, allow_null=True)
    y1_degradation = serializers.FloatField(required=False, allow_null=True)
    anual_degradation = serializers.FloatField(required=False, allow_null=True)
    api_name = serializers.CharField(required=False, allow_null=True)
    api_key = serializers.CharField(required=False, allow_null=True)
    tilt_configs = serializers.JSONField(required=False, allow_null=True)
    altitude_m = serializers.FloatField(required=False, allow_null=True)
    albedo = serializers.FloatField(required=False, allow_null=True)
    pv_syst_pr = serializers.FloatField(required=False, allow_null=True)


class AssetListResponseSerializer(PaginatedResponseSerializer):
    results = AssetListSerializer(many=True)


class DeviceListSerializer(serializers.Serializer):
    device_id = serializers.CharField()
    device_name = serializers.CharField(required=False, allow_null=True)
    device_code = serializers.CharField(required=False, allow_null=True)
    device_type_id = serializers.CharField(required=False, allow_null=True)
    device_serial = serializers.CharField(required=False, allow_null=True)
    device_model = serializers.CharField(required=False, allow_null=True)
    device_make = serializers.CharField(required=False, allow_null=True)
    latitude = serializers.FloatField(required=False, allow_null=True)
    longitude = serializers.FloatField(required=False, allow_null=True)
    optimizer_no = serializers.IntegerField(required=False, allow_null=True)
    parent_code = serializers.CharField(required=False, allow_null=True)
    device_type = serializers.CharField(required=False, allow_null=True)
    software_version = serializers.CharField(required=False, allow_null=True)
    country = serializers.CharField(required=False, allow_null=True)
    string_no = serializers.CharField(required=False, allow_null=True)
    connected_strings = serializers.CharField(required=False, allow_null=True)
    device_sub_group = serializers.CharField(required=False, allow_null=True)
    dc_cap = serializers.FloatField(required=False, allow_null=True)
    device_source = serializers.CharField(required=False, allow_null=True)
    ac_capacity = serializers.FloatField(required=False, allow_null=True)
    equipment_warranty_start_date = serializers.DateField(required=False, allow_null=True)
    equipment_warranty_expire_date = serializers.DateField(required=False, allow_null=True)
    epc_warranty_start_date = serializers.DateField(required=False, allow_null=True)
    epc_warranty_expire_date = serializers.DateField(required=False, allow_null=True)
    calibration_frequency = serializers.CharField(required=False, allow_null=True)
    pm_frequency = serializers.CharField(required=False, allow_null=True)
    visual_inspection_frequency = serializers.CharField(required=False, allow_null=True)
    bess_capacity = serializers.FloatField(required=False, allow_null=True)
    yom = serializers.CharField(required=False, allow_null=True)
    nomenclature = serializers.CharField(required=False, allow_null=True)
    location = serializers.CharField(required=False, allow_null=True)


class DeviceListResponseSerializer(PaginatedResponseSerializer):
    results = DeviceListSerializer(many=True)


class DeviceMappingSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    asset_code = serializers.CharField()
    device_type = serializers.CharField(required=False, allow_null=True)
    oem_tag = serializers.CharField(required=False, allow_null=True)
    description = serializers.CharField(required=False, allow_null=True)
    data_type = serializers.CharField(required=False, allow_null=True)
    units = serializers.CharField(required=False, allow_null=True)
    metric = serializers.CharField(required=False, allow_null=True)
    fault_code = serializers.CharField(required=False, allow_null=True)
    module_no = serializers.CharField(required=False, allow_null=True)
    default_value = serializers.CharField(required=False, allow_null=True)


class DeviceMappingResponseSerializer(PaginatedResponseSerializer):
    results = DeviceMappingSerializer(many=True)


class BudgetValuesSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    asset_number = serializers.CharField(required=False, allow_null=True)
    asset_code = serializers.CharField()
    month_str = serializers.CharField(required=False, allow_null=True)
    month_date = serializers.DateField(required=False, allow_null=True)
    bd_production = serializers.FloatField(required=False, allow_null=True)
    bd_ghi = serializers.FloatField(required=False, allow_null=True)
    bd_gti = serializers.FloatField(required=False, allow_null=True)


class BudgetValuesResponseSerializer(PaginatedResponseSerializer):
    results = BudgetValuesSerializer(many=True)


class ICBudgetSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    asset_code = serializers.CharField()
    asset_number = serializers.CharField(required=False, allow_null=True)
    month_str = serializers.CharField(required=False, allow_null=True)
    month_date = serializers.DateField(required=False, allow_null=True)
    ic_bd_production = serializers.FloatField(required=False, allow_null=True)


class ICBudgetResponseSerializer(PaginatedResponseSerializer):
    results = ICBudgetSerializer(many=True)


class ApiResponseSerializer(serializers.Serializer):
    success = serializers.BooleanField()
    message = serializers.CharField()
    error = serializers.CharField(required=False, allow_null=True)


class UniqueApiNamesResponseSerializer(serializers.Serializer):
    success = serializers.BooleanField()
    api_names = serializers.ListField(child=serializers.CharField())

