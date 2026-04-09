from rest_framework import serializers


class BasicOptionSerializer(serializers.Serializer):
    value = serializers.CharField()
    label = serializers.CharField()


class DescribedOptionSerializer(BasicOptionSerializer):
    description = serializers.CharField(required=False, allow_blank=True, allow_null=True)


class SiteOptionSerializer(BasicOptionSerializer):
    assetCode = serializers.CharField(allow_null=True, required=False)
    assetNumber = serializers.CharField(allow_null=True, required=False)
    country = serializers.CharField(allow_null=True, required=False)
    portfolio = serializers.CharField(allow_null=True, required=False)


class TicketDashboardFiltersSerializer(serializers.Serializer):
    statusOptions = BasicOptionSerializer(many=True)
    priorityOptions = BasicOptionSerializer(many=True)
    categoryOptions = DescribedOptionSerializer(many=True)
    lossCategoryOptions = DescribedOptionSerializer(many=True)
    siteOptions = SiteOptionSerializer(many=True)


class TicketDashboardMetaSerializer(serializers.Serializer):
    appliedFilters = serializers.DictField(child=serializers.JSONField(), required=False)
    generatedAt = serializers.CharField()


class ChartDatasetSerializer(serializers.Serializer):
    labels = serializers.ListField(child=serializers.CharField(), allow_empty=True)
    values = serializers.ListField(child=serializers.FloatField(), allow_empty=True)


class TicketDashboardChartsSerializer(serializers.Serializer):
    status = ChartDatasetSerializer()
    priority = ChartDatasetSerializer()
    category = ChartDatasetSerializer()


class TicketDashboardKpiSerializer(serializers.Serializer):
    total_tickets = serializers.IntegerField()
    open_tickets = serializers.IntegerField()
    unassigned_tickets = serializers.IntegerField()
    overdue_tickets = serializers.IntegerField()


class RecentTicketSerializer(serializers.Serializer):
    id = serializers.CharField()
    ticket_number = serializers.CharField()
    title = serializers.CharField()
    status = serializers.CharField()
    status_display = serializers.CharField()
    priority = serializers.CharField()
    priority_display = serializers.CharField()
    site_name = serializers.CharField()
    created_at = serializers.CharField()


class DeviceTicketSerializer(serializers.Serializer):
    device_name = serializers.CharField()
    device_serial = serializers.CharField()
    count = serializers.IntegerField()


class LossByCategorySerializer(serializers.Serializer):
    category_name = serializers.CharField()
    total_loss = serializers.FloatField()
    count = serializers.IntegerField()


class LossByDeviceSerializer(serializers.Serializer):
    device_name = serializers.CharField()
    device_make = serializers.CharField()
    device_model = serializers.CharField()
    total_loss = serializers.FloatField()
    count = serializers.IntegerField()


class AvgTimeSerializer(serializers.Serializer):
    days = serializers.IntegerField()
    hours = serializers.IntegerField()
    minutes = serializers.IntegerField()
    total_seconds = serializers.FloatField()


class TicketDashboardLossesSerializer(serializers.Serializer):
    total = serializers.FloatField()
    byCategory = LossByCategorySerializer(many=True)
    byDevice = LossByDeviceSerializer(many=True)


class TicketDashboardSummarySerializer(serializers.Serializer):
    meta = TicketDashboardMetaSerializer()
    filters = TicketDashboardFiltersSerializer()
    kpis = TicketDashboardKpiSerializer()
    charts = TicketDashboardChartsSerializer()
    recentTickets = RecentTicketSerializer(many=True)
    ticketsByDevice = DeviceTicketSerializer(many=True)
    ticketsByStatus = serializers.DictField(child=serializers.IntegerField())
    avgTimeToClose = AvgTimeSerializer(allow_null=True, required=False)
    losses = TicketDashboardLossesSerializer()


class AnalyticsItemSerializer(serializers.Serializer):
    label = serializers.CharField()
    subLabel = serializers.CharField(allow_blank=True, allow_null=True, required=False)
    value = serializers.FloatField()
    secondary = serializers.FloatField()
    trend = serializers.ListField(child=serializers.IntegerField(), allow_empty=True)
    entityType = serializers.CharField()
    entityKey = serializers.JSONField()


class AnalyticsPaginationSerializer(serializers.Serializer):
    page = serializers.IntegerField()
    perPage = serializers.IntegerField()
    totalItems = serializers.IntegerField()
    totalPages = serializers.IntegerField()


class AnalyticsResponseSerializer(serializers.Serializer):
    labels = serializers.ListField(child=serializers.CharField(), allow_empty=True)
    values = serializers.ListField(child=serializers.FloatField(), allow_empty=True)
    items = AnalyticsItemSerializer(many=True)
    pagination = AnalyticsPaginationSerializer()


class RecentTicketsResponseSerializer(serializers.Serializer):
    count = serializers.IntegerField()
    results = RecentTicketSerializer(many=True)


class TicketListItemSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    ticket_number = serializers.CharField()
    title = serializers.CharField()
    status = serializers.CharField()
    status_display = serializers.CharField()
    priority = serializers.CharField()
    priority_display = serializers.CharField()
    category = serializers.CharField(allow_null=True)
    sub_category = serializers.CharField(allow_null=True, required=False)
    asset_code = serializers.CharField(allow_null=True)
    asset_name = serializers.CharField(allow_null=True)
    asset_number = serializers.CharField(allow_null=True)
    assigned_to_id = serializers.IntegerField(allow_null=True)
    assigned_to = serializers.CharField(allow_null=True)
    created_at = serializers.DateTimeField()
    updated_at = serializers.DateTimeField(allow_null=True)


class SubCategoryOptionSerializer(BasicOptionSerializer):
    category = serializers.CharField()


class TicketUserSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    username = serializers.CharField()
    name = serializers.CharField()


class TicketListFiltersSerializer(serializers.Serializer):
    statusOptions = BasicOptionSerializer(many=True)
    priorityOptions = BasicOptionSerializer(many=True)
    categoryOptions = BasicOptionSerializer(many=True)
    subCategoryOptions = SubCategoryOptionSerializer(many=True)
    siteOptions = SiteOptionSerializer(many=True)
    assigneeOptions = BasicOptionSerializer(many=True)
    assetNumberOptions = BasicOptionSerializer(many=True)


class TicketSubCategorySerializer(serializers.Serializer):
    id = serializers.IntegerField()
    name = serializers.CharField()
    category_id = serializers.IntegerField()


class TicketMaterialSerializer(serializers.Serializer):
    id = serializers.CharField()
    material_name = serializers.CharField()
    quantity = serializers.CharField()
    unit_price = serializers.CharField()
    created_at = serializers.CharField()
    updated_at = serializers.CharField()


class TicketMaterialCreateSerializer(serializers.Serializer):
    material_name = serializers.CharField(max_length=200)
    quantity = serializers.DecimalField(max_digits=10, decimal_places=2)
    unit_price = serializers.DecimalField(max_digits=10, decimal_places=2)


class TicketManpowerSerializer(serializers.Serializer):
    id = serializers.CharField()
    person_name = serializers.CharField()
    hours_worked = serializers.CharField()
    hourly_rate = serializers.CharField()
    created_at = serializers.CharField()
    updated_at = serializers.CharField()


class TicketManpowerCreateSerializer(serializers.Serializer):
    person_name = serializers.CharField(max_length=200)
    hours_worked = serializers.DecimalField(max_digits=10, decimal_places=2)
    hourly_rate = serializers.DecimalField(max_digits=10, decimal_places=2)


class TicketDetailSerializer(serializers.Serializer):
    id = serializers.CharField()
    ticket_number = serializers.CharField()
    title = serializers.CharField()
    description = serializers.CharField(allow_blank=True, required=False)
    status = serializers.CharField()
    status_display = serializers.CharField()
    priority = serializers.CharField()
    priority_display = serializers.CharField()
    category = serializers.CharField(allow_null=True)
    sub_category = TicketSubCategorySerializer(allow_null=True)
    loss_category = serializers.CharField(allow_null=True)
    asset_code = serializers.CharField(allow_null=True)
    asset_name = serializers.CharField(allow_null=True)
    assigned_to = TicketUserSerializer(allow_null=True)
    created_by = TicketUserSerializer(allow_null=True)
    updated_by = TicketUserSerializer(allow_null=True)
    watchers = TicketUserSerializer(many=True)
    created_at = serializers.CharField()
    updated_at = serializers.CharField(allow_null=True)
    closed_at = serializers.CharField(allow_null=True)
    metadata = serializers.DictField()
    permissions = serializers.DictField()
    materials = TicketMaterialSerializer(many=True)
    manpower = TicketManpowerSerializer(many=True)


class TicketTimelineSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    user = TicketUserSerializer(allow_null=True)
    action = serializers.CharField()
    field = serializers.CharField(allow_null=True)
    old_value = serializers.CharField(allow_null=True)
    new_value = serializers.CharField(allow_null=True)
    notes = serializers.CharField(allow_blank=True)
    created_at = serializers.CharField()


class TicketCommentSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    user = TicketUserSerializer(allow_null=True)
    comment = serializers.CharField()
    created_at = serializers.CharField()
    is_internal = serializers.BooleanField()


class TicketAttachmentSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    file_name = serializers.CharField()
    file_url = serializers.CharField()
    file_size = serializers.IntegerField(required=False, allow_null=True)
    file_type = serializers.CharField(required=False, allow_null=True)
    uploaded_by = TicketUserSerializer(allow_null=True)
    created_at = serializers.CharField()


class TicketFormOptionsSerializer(serializers.Serializer):
    sites = BasicOptionSerializer(many=True)
    categories = BasicOptionSerializer(many=True)
    subCategories = SubCategoryOptionSerializer(many=True)
    lossCategories = BasicOptionSerializer(many=True)
    priorities = BasicOptionSerializer(many=True)
    users = BasicOptionSerializer(many=True)


class DeviceOptionSerializer(serializers.Serializer):
    value = serializers.CharField()
    label = serializers.CharField()
    device_type = serializers.CharField(allow_null=True, required=False)
    device_sub_group = serializers.CharField(allow_null=True, required=False)
    warranty_expire_date = serializers.DateTimeField(allow_null=True, required=False)


class TicketCreateUpdateSerializer(serializers.Serializer):
    title = serializers.CharField(max_length=255)
    description = serializers.CharField()
    asset_code = serializers.CharField()
    location = serializers.CharField(allow_null=True, required=False, allow_blank=True)
    device_type = serializers.CharField(allow_null=True, required=False, allow_blank=True)
    device_id = serializers.CharField(allow_null=True, required=False, allow_blank=True)
    sub_device_id = serializers.CharField(allow_null=True, required=False, allow_blank=True)
    category = serializers.CharField()
    sub_category = serializers.CharField(allow_null=True, required=False, allow_blank=True)
    loss_category = serializers.CharField(allow_null=True, required=False, allow_blank=True)
    loss_value = serializers.DecimalField(max_digits=12, decimal_places=2, allow_null=True, required=False)
    priority = serializers.ChoiceField(choices=[('low', 'Low'), ('medium', 'Medium'), ('high', 'High'), ('critical', 'Critical')])
    assigned_to = serializers.CharField(allow_null=True, required=False, allow_blank=True)
    watchers = serializers.ListField(child=serializers.CharField(), required=False, allow_empty=True)

