from django.db import models
from django.http import HttpResponseForbidden
# Create your models here.

from django.core.validators import MinValueValidator, MaxValueValidator, RegexValidator
import uuid
from django.contrib.auth.models import User
from django.utils import timezone

from .permissions import (
    APP_ACCESS_LABELS,
    get_capabilities_for_role,
    get_role_choices,
    role_has_capability,
)


class AssetList(models.Model):
    """Parent table with basic asset information"""
    asset_code = models.CharField(max_length=255, primary_key=True, help_text="Asset code")
    asset_name = models.CharField(max_length=255, help_text="Asset name")
    capacity = models.DecimalField(
        max_digits=19, 
        decimal_places=15, 
        help_text="site capacity in kWh"
    )
    address = models.TextField()
    country = models.CharField(max_length=100, help_text="Asset country")
    latitude = models.DecimalField(
        max_digits=19, 
        decimal_places=15, 
        validators=[MinValueValidator(-90), MaxValueValidator(90)],
        help_text="Latitude coordinate"
    )
    longitude = models.DecimalField(
        max_digits=19, 
        decimal_places=15, 
        validators=[MinValueValidator(-180), MaxValueValidator(180)],
        help_text="Longitude coordinate"
    )
    contact_person = models.TextField()
    contact_method = models.TextField()
    grid_connection_date = models.DateTimeField()
    asset_number = models.CharField(max_length=255, help_text="Asset number")
    customer_name = models.CharField(max_length=255, blank=True, null=True)
    timezone = models.CharField(
        max_length=10, 
        validators=[
            RegexValidator(
                regex=r'^[+-](0[0-9]|1[0-2]):[0-5][0-9]$',
                message='Timezone must be in format "+05:30" or "-08:00"',
                code='invalid_timezone'
            )
        ],
        help_text="Timezone offset in format '+05:30' or '-08:00'"
    )
    asset_name_oem = models.CharField(max_length=255, help_text="Asset name from OEM", blank=True, null=True)
    cod = models.DateTimeField(help_text="Commercial Operation Date", blank=True, null=True)
    operational_cod = models.DateTimeField(help_text="Operational Commercial Operation Date", blank=True, null=True)
    portfolio = models.CharField(max_length=255, help_text="Portfolio")
    y1_degradation = models.DecimalField(
        max_digits=5, 
        decimal_places=2, 
        help_text="Year 1 degradation percentage", 
        blank=True, 
        null=True
    )
    anual_degradation = models.DecimalField(
        max_digits=5, 
        decimal_places=2, 
        help_text="Annual degradation percentage", 
        blank=True, 
        null=True
    )
    api_name = models.TextField(blank=True, null=True)
    api_key = models.TextField(blank=True, null=True)
    # GHI→GII transposition and site config (admin-managed)
    tilt_configs = models.JSONField(
        null=True,
        blank=True,
        help_text='Array of tilt/azimuth/panel configs: [{"tilt_deg": 25, "azimuth_deg": 0, "panel_count": 100}]'
    )
    altitude_m = models.FloatField(
        null=True,
        blank=True,
        help_text='Site altitude in meters (for solar position)'
    )
    albedo = models.FloatField(
        null=True,
        blank=True,
        validators=[MinValueValidator(0), MaxValueValidator(1)],
        help_text='Ground albedo (0-1, default ~0.2 for transposition)'
    )
    pv_syst_pr = models.FloatField(
        null=True,
        blank=True,
        validators=[MinValueValidator(0), MaxValueValidator(1)],
        help_text='PVsyst Performance Ratio (0-1) for PR-based expected power model'
    )
    satellite_irradiance_source_asset_code = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        help_text='If set, use satellite irradiance from this other asset\'s _sat device. If null, use own {asset_code}_sat.',
    )
    provider_asset_id = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        help_text='API plant/station ID from data provider (e.g. Fusion Solar station code). Used by data collection adapters.',
    )
    #created_at = models.DateTimeField(auto_now_add=True)
    #updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'asset_list'
        ordering = ['asset_name']
        managed = False

    def __str__(self):
        return f"{self.asset_name} ({self.country})"

    @property
    def device_count(self):
        """Return the number of devices associated with this asset"""
        return self.devices.count()


class kpis(models.Model):
    """KPIs table with basic asset information"""
    id = models.AutoField(primary_key=True) 
    device_id = models.CharField(max_length=120, help_text='device_id')
    asset_code = models.CharField(max_length=120, help_text='asset code')
    asset_number = models.CharField(max_length=120, help_text= 'asset number')
    device_name = models.CharField(max_length=120, help_text='device_name')
    asset_name = models.CharField(max_length=120, help_text='asset_name')
    daily_min_read_time = models.DateTimeField(help_text='timestamp with timezone')
    daily_min_read_kwh = models.FloatField(help_text='kwh')
    daily_max_read_time = models.DateTimeField(help_text='timestamp with timezone')
    daily_max_read_kwh = models.FloatField(help_text='kwh')
    daily_max_min = models.FloatField(help_text='kwh')
    daily_prod_rec = models.FloatField(help_text='kwh')
    daily_prod_rec_time = models.DateTimeField(help_text='timestamp with timezone')
    day_1_max_read_time = models.DateTimeField(help_text='timestamp with timezone')
    day_1_max_read_kwh = models.FloatField(help_text='kwh')
    day_date = models.DateField(help_text='date')
    generation_metric = models.CharField(max_length=40, blank=True, null=True, help_text='metric used for daily_prod_rec')
    has_anomaly = models.BooleanField(default=False, help_text='whether anomalies were found for this day')
    anomaly_flags = models.JSONField(blank=True, null=True, help_text='anomaly details for this day')
    anomaly_notes = models.TextField(blank=True, null=True, help_text='human-readable anomaly summary')
    oem_daily_product_kwh = models.FloatField(
        blank=True,
        null=True,
        help_text='OEM-reported daily energy (e.g. Fusion Solar getDevKpiDay product_power), kWh',
    )

    class Meta:
        db_table = 'kpis'
        #ordering = ['device_id']
        managed = False
        #unique_together = [['device_id','day_date']]
        constraints = [
            models.UniqueConstraint(fields=['device_id', 'day_date'], name='unique_device_id_day_date')
        ]

    def __str__(self):
        return f"{self.asset_name} ({self.asset_code})"

    #@property
    #def device_count(self):
    #    """Return the number of devices associated with this asset"""
    #    return self.devices.count()

class device_list(models.Model):
    """Device List table with basic asset information"""
    device_id = models.CharField(max_length=120, primary_key=True, help_text='device_id')
    device_name = models.CharField(max_length=40)
    device_code = models.CharField(max_length=40,help_text='device_code')
    device_type_id = models.CharField(max_length=40)
    device_serial = models.CharField(max_length=40)
    device_model = models.CharField(max_length=40)
    device_make = models.CharField(max_length=40)
    latitude = models.FloatField()
    longitude = models.FloatField()
    optimizer_no = models.BigIntegerField()
    parent_code = models.CharField(max_length=40)
    device_type = models.CharField(max_length=40)
    software_version = models.CharField(max_length=40)
    country = models.CharField(max_length=40)
    string_no = models.CharField(max_length=40)
    connected_strings = models.CharField(max_length=120)
    device_sub_group = models.CharField(max_length=40)
    dc_cap = models.FloatField(null=True, blank=True, help_text='DC Capacity')
    device_source = models.CharField(max_length=40)
    ac_capacity = models.FloatField(null=True, blank=True, help_text='AC Capacity')
    equipment_warranty_start_date = models.DateTimeField(null=True, blank=True, help_text='Equipment Warranty Start Date')
    equipment_warranty_expire_date = models.DateTimeField(null=True, blank=True, help_text='Equipment Warranty Expire Date')
    epc_warranty_start_date = models.DateTimeField(null=True, blank=True, help_text='EPC Warranty Start Date')
    epc_warranty_expire_date = models.DateTimeField(null=True, blank=True, help_text='EPC Warranty Expire Date')
    calibration_frequency = models.CharField(max_length=40, blank=True, null=True, help_text='Calibration Frequency')
    pm_frequency = models.CharField(max_length=40, blank=True, null=True, help_text='PM Frequency')
    visual_inspection_frequency = models.CharField(max_length=40, blank=True, null=True, help_text='Visual Inspection Frequency')
    bess_capacity = models.FloatField(null=True, blank=True, help_text='BESS Capacity')
    yom = models.CharField(max_length=40, blank=True, null=True, help_text='Year of Manufacture')
    nomenclature = models.CharField(max_length=120, blank=True, null=True, help_text='Nomenclature')
    location = models.CharField(max_length=255, blank=True, null=True, help_text='Location')
    
    # PV Module Configuration Fields (Added in Migration 0050)
    module_datasheet_id = models.IntegerField(null=True, blank=True, help_text='Foreign key to pv_module_datasheet')
    modules_in_series = models.IntegerField(null=True, blank=True, help_text='Number of modules in series per string')
    installation_date = models.DateField(null=True, blank=True, help_text='Installation date')
    tilt_angle = models.FloatField(null=True, blank=True, help_text='Tilt angle in degrees')
    azimuth_angle = models.FloatField(null=True, blank=True, help_text='Azimuth angle in degrees (0=N, 90=E, 180=S, 270=W)')
    mounting_type = models.CharField(max_length=50, null=True, blank=True, help_text='Mounting type (Fixed, Tracker, etc.)')
    expected_soiling_loss = models.FloatField(null=True, blank=True, help_text='Expected soiling loss percentage')
    shading_factor = models.FloatField(null=True, blank=True, help_text='Shading factor percentage')
    measured_degradation_rate = models.FloatField(null=True, blank=True, help_text='Measured degradation rate %/year')
    last_performance_test_date = models.DateField(null=True, blank=True, help_text='Last performance test date')
    operational_notes = models.TextField(null=True, blank=True, help_text='Operational notes')
    power_model_id = models.IntegerField(null=True, blank=True, help_text='Foreign key to power_model_registry')
    power_model_config = models.JSONField(null=True, blank=True, help_text='Power model specific configuration')
    model_fallback_enabled = models.BooleanField(null=True, blank=True, default=True, help_text='Enable model fallback')
    weather_device_config = models.JSONField(null=True, blank=True, help_text='Weather device configuration with fallback support. Format: {"irradiance_devices": ["device1", "device2"], "temperature_devices": ["device1", "device2"], "wind_devices": ["device1", "device2"]}')
    # Loss calculation: when True (or null for backward compatibility), include in daily loss and test page device list
    loss_calculation_enabled = models.BooleanField(null=True, blank=True, default=True, help_text='Enable loss calculation for this device. Default True when null (backward compatibility).')
    # String config: tilt/azimuth/panel count per orientation (for GII and reporting)
    tilt_configs = models.JSONField(
        null=True,
        blank=True,
        help_text='Array of tilt/azimuth/panel configs per string: [{"tilt_deg": 25, "azimuth_deg": 0, "panel_count": 24}]'
    )

    class Meta:
        db_table = 'device_list'
        #ordering = ['device_id']
        managed = False

    def __str__(self):
        return f"{self.device_name} ({self.country})"
    
    def get_module_datasheet(self):
        """Get the related PVModuleDatasheet object"""
        if self.module_datasheet_id:
            try:
                return PVModuleDatasheet.objects.get(id=self.module_datasheet_id)
            except PVModuleDatasheet.DoesNotExist:
                return None
        return None
    
    def get_power_model(self):
        """Get the related PowerModelRegistry object"""
        if self.power_model_id:
            try:
                return PowerModelRegistry.objects.get(id=self.power_model_id)
            except PowerModelRegistry.DoesNotExist:
                return None
        return None
    
    @property
    def string_rated_power(self):
        """Calculate string rated power from module and count"""
        module = self.get_module_datasheet()
        if module and self.modules_in_series:
            return module.pmax_stc * self.modules_in_series
        return None
    
    @property
    def string_voc(self):
        """Calculate string Voc from module and count"""
        module = self.get_module_datasheet()
        if module and self.modules_in_series:
            return module.voc_stc * self.modules_in_series
        return None
    
    @property
    def string_vmp(self):
        """Calculate string Vmp from module and count"""
        module = self.get_module_datasheet()
        if module and self.modules_in_series:
            return module.vmp_stc * self.modules_in_series
        return None
    
    @property
    def string_age_years(self):
        """Calculate string age in years from installation date"""
        if self.installation_date:
            from datetime import date
            today = date.today()
            return (today - self.installation_date).days / 365.25
        return None
    
    @property
    def current_degradation_factor(self):
        """Calculate current degradation factor based on age and degradation rate"""
        module = self.get_module_datasheet()
        if self.string_age_years and module:
            # Use measured degradation if available, otherwise use module estimate
            degradation_rate = self.measured_degradation_rate or module.estimated_annual_degradation
            if degradation_rate:
                return 1 - (degradation_rate * self.string_age_years / 100)
        return 1.0  # No degradation if data unavailable


def get_configured_loss_string_devices_for_asset(asset_code: str):
    """
    Shared helper for loss calculation to fetch string devices that are:
    - attached to the given asset (parent_code)
    - string-type devices
    - have PV configuration (module_datasheet_id and modules_in_series set)
    - enabled for loss calculation (loss_calculation_enabled is True or null for backward compatibility)

    Returns a QuerySet of device_list objects so callers can project the fields they need.
    """
    from django.db.models import Q

    base_qs = device_list.objects.filter(
        parent_code=asset_code,
        device_type__icontains="string",
        module_datasheet_id__isnull=False,
        modules_in_series__isnull=False,
    )
    # Treat NULL as enabled to preserve current behaviour until explicitly disabled
    return base_qs.filter(
        Q(loss_calculation_enabled__isnull=True) | Q(loss_calculation_enabled=True)
    )


class device_mapping(models.Model):
    """Device Mapping table for site onboarding"""
    asset_code = models.CharField(max_length=120, help_text='Asset code')
    device_type = models.CharField(max_length=80, help_text='Device type')
    oem_tag = models.CharField(max_length=150, help_text='OEM tag')
    discription = models.CharField(max_length=150, help_text='Description', db_column='discription')  # Note: typo in database
    data_type = models.CharField(max_length=80, help_text='Data type')
    units = models.CharField(max_length=50, help_text='Units')
    metric = models.CharField(max_length=80, help_text='Metric')
    id = models.BigIntegerField(primary_key=True, help_text='ID')
    fault_code = models.CharField(max_length=50, help_text='Fault code', blank=True, null=True)
    module_no = models.CharField(max_length=50, help_text='Module number', blank=True, null=True)
    default_value = models.CharField(max_length=50, help_text='Default value', blank=True, null=True)

    class Meta:
        db_table = 'device_mapping'
        managed = False  # Table exists in database - Django should not manage it

    def __str__(self):
        return f"{self.asset_code} - {self.device_type} - {self.oem_tag}"
    
    @property
    def description(self):
        """Alias for discription field to maintain proper spelling in code"""
        return self.discription


class budget_values(models.Model):
    """Budget Values table for site onboarding"""
    id = models.BigAutoField(primary_key=True, help_text='Auto-generated ID')
    asset_number = models.CharField(max_length=150, help_text='Asset number')
    asset_code = models.CharField(max_length=150, help_text='Asset code')
    month_str = models.CharField(max_length=80, help_text='Month string (JAN, FEB, etc.)')
    month_date = models.DateField(help_text='Month date')
    bd_production = models.FloatField(help_text='Budget production value')
    bd_ghi = models.FloatField(help_text='Budget GHI value')
    bd_gti = models.FloatField(help_text='Budget GTI value')

    class Meta:
        db_table = 'budget_values'
        managed = False  # Keep as unmanaged since table exists
        constraints = [
            models.UniqueConstraint(fields=['asset_code', 'month_str'], name='unique_asset_month_budget')
        ]

    def __str__(self):
        return f"{self.asset_code} - {self.month_str}"


class ic_budget(models.Model):
    """IC Budget table for site onboarding"""
    id = models.BigAutoField(primary_key=True, help_text='Auto-generated ID')
    asset_code = models.CharField(max_length=150, help_text='Asset code')
    asset_number = models.CharField(max_length=150, help_text='Asset number')
    month_str = models.CharField(max_length=80, help_text='Month string (JAN, FEB, etc.)')
    month_date = models.DateField(help_text='Month date')
    ic_bd_production = models.FloatField(help_text='IC Budget production value')

    class Meta:
        db_table = 'ic_budget'
        managed = False  # Keep as unmanaged since table exists
        constraints = [
            models.UniqueConstraint(fields=['asset_code', 'month_date'], name='unique_asset_month_ic_budget')
        ]

    def __str__(self):
        return f"{self.asset_code} - {self.month_str}"


class assets_contracts(models.Model):
    """
    Asset contract details for Energy Revenue Hub / Site Onboarding.
    """

    id = models.BigAutoField(primary_key=True)
    asset_number = models.CharField(max_length=255, unique=True)
    asset_code = models.CharField(max_length=255)
    asset_name = models.CharField(max_length=255, blank=True, default="")
    customer_asset_name = models.CharField(max_length=255, blank=True, default="")
    customer_tax_number = models.CharField(max_length=64, blank=True, default="")
    asset_address = models.TextField(blank=True, default="")
    asset_cod = models.DateField(null=True, blank=True)
    contractor_name = models.CharField(max_length=255, blank=True, default="")
    spv_name = models.CharField(max_length=255, blank=True, default="")
    contract_start_date = models.DateField(null=True, blank=True)
    contract_end_date = models.DateField(null=True, blank=True)
    contract_billing_cycle = models.CharField(max_length=32, blank=True, default="monthly")
    contract_billing_cycle_start_day = models.IntegerField(null=True, blank=True)
    contract_billing_cycle_end_day = models.IntegerField(null=True, blank=True)
    currency_code = models.CharField(max_length=8, blank=True, default="SGD")
    sp_account_no = models.CharField(max_length=64, blank=True, default="")
    escalation_condition = models.CharField(max_length=16, blank=True, default="")
    escalation_type = models.CharField(
        max_length=24,
        blank=True,
        default="",
        help_text="Escalation model for rooftop/MRE rate: multiplicative, additive, etc.",
    )
    escalation_grace_years = models.PositiveSmallIntegerField(null=True, blank=True)
    escalation_rate = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    escalation_period = models.IntegerField(null=True, blank=True)
    gst_rate = models.DecimalField(
        max_digits=9,
        decimal_places=6,
        null=True,
        blank=True,
        help_text="GST as decimal fraction e.g. 0.09 for 9%.",
    )
    bank_name = models.CharField(max_length=255, blank=True, default="")
    bank_account_no = models.CharField(max_length=64, blank=True, default="")
    bank_swift = models.CharField(max_length=32, blank=True, default="")
    bank_branch_code = models.CharField(max_length=64, blank=True, default="")
    spv_address = models.TextField(blank=True, default="")
    spv_gst_number = models.CharField(max_length=64, blank=True, default="")
    contractor_id = models.CharField(max_length=64, blank=True, default="")
    contract_type = models.CharField(
        max_length=32,
        blank=True,
        default="",
        help_text="Billing engine profile key (e.g. sg_ppa); drives contract_profiles plugin in ERH.",
    )
    due_days = models.IntegerField(null=True, blank=True, help_text="Invoice due days offset from invoice date.")
    requires_utility_invoice = models.BooleanField(
        default=False,
        help_text="If true, billing requires a parsed utility invoice for the billing period (sg_ppa / utility-led flows).",
    )
    contractor_address = models.TextField(blank=True, default="")
    contact_person_1 = models.CharField(max_length=255, blank=True, default="")
    contact_person_2 = models.CharField(max_length=255, blank=True, default="")
    contact_person_3 = models.CharField(max_length=255, blank=True, default="")
    contact_person_4 = models.CharField(max_length=255, blank=True, default="")
    contact_person_5 = models.CharField(max_length=255, blank=True, default="")
    contact_person_6 = models.CharField(max_length=255, blank=True, default="")
    contact_email_id_1 = models.CharField(max_length=255, blank=True, default="")
    contact_email_id_2 = models.CharField(max_length=255, blank=True, default="")
    contact_email_id_3 = models.CharField(max_length=255, blank=True, default="")
    contact_email_id_4 = models.CharField(max_length=255, blank=True, default="")
    contact_email_id_5 = models.CharField(max_length=255, blank=True, default="")
    contact_email_id_6 = models.CharField(max_length=255, blank=True, default="")
    contact_email_id_7 = models.CharField(max_length=255, blank=True, default="")
    contact_number_1 = models.CharField(max_length=64, blank=True, default="")
    contact_number_2 = models.CharField(max_length=64, blank=True, default="")
    contact_number_3 = models.CharField(max_length=64, blank=True, default="")
    grid_export_rate = models.DecimalField(max_digits=18, decimal_places=6, null=True, blank=True)
    grid_export_tax = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    grid_excess_export = models.DecimalField(max_digits=18, decimal_places=6, null=True, blank=True)
    grid_excess_export_tax = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    rooftop_self_consumption_rate = models.DecimalField(max_digits=18, decimal_places=6, null=True, blank=True)
    rooftop_self_consumption_tax = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    solar_lease_rate = models.DecimalField(max_digits=18, decimal_places=6, null=True, blank=True)
    solar_lease_rate_tax = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    bess_dispatch_rate = models.DecimalField(max_digits=18, decimal_places=6, null=True, blank=True)
    bess_dispatch_tax = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    hybrid_solar_bess_rate = models.DecimalField(max_digits=18, decimal_places=6, null=True, blank=True)
    hybrid_solar_bess_tax = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    generation_based_ppa_rate = models.DecimalField(max_digits=18, decimal_places=6, null=True, blank=True)
    generation_based_ppa_tax = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    capacity_payment_rate = models.DecimalField(max_digits=18, decimal_places=6, null=True, blank=True)
    capacity_payment_tax = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    curtailment_compensation = models.DecimalField(max_digits=18, decimal_places=6, null=True, blank=True)
    peak_tariff_rate = models.DecimalField(max_digits=18, decimal_places=6, null=True, blank=True)
    off_peak_rate = models.DecimalField(max_digits=18, decimal_places=6, null=True, blank=True)
    shoulder_tariff = models.CharField(max_length=64, blank=True, default="")
    shoulder_rate = models.DecimalField(max_digits=18, decimal_places=6, null=True, blank=True)
    super_off_break_tariff = models.CharField(max_length=64, blank=True, default="")
    super_off_break_rate = models.DecimalField(max_digits=18, decimal_places=6, null=True, blank=True)
    seasonal_tou_tariff = models.CharField(max_length=64, blank=True, default="")
    seasonal_tou_rate = models.DecimalField(max_digits=18, decimal_places=6, null=True, blank=True)
    real_time_tou_tariff = models.CharField(max_length=64, blank=True, default="")
    real_time_tou_rate = models.DecimalField(max_digits=18, decimal_places=6, null=True, blank=True)
    critical_peak_tariff = models.CharField(max_length=64, blank=True, default="")
    critical_peak_rate = models.DecimalField(max_digits=18, decimal_places=6, null=True, blank=True)
    merchant_market_rate = models.DecimalField(max_digits=18, decimal_places=6, null=True, blank=True)
    ancillary_services_charges = models.DecimalField(max_digits=18, decimal_places=6, null=True, blank=True)
    ancillary_services_tax = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    virtual_ppa_rate = models.DecimalField(max_digits=18, decimal_places=6, null=True, blank=True)
    virtual_ppa_tax = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    green_tariff_rate = models.DecimalField(max_digits=18, decimal_places=6, null=True, blank=True)
    green_tariff_tax = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    tariff_matrix_json = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "assets_contracts"
        ordering = ["asset_number"]

    def __str__(self):
        return f"{self.asset_number} ({self.asset_code})"
    
    
class timeseries_data(models.Model):
    """Data table with basic asset information"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    device_id = models.CharField(max_length=80, help_text='device_id')
    ts = models.DateTimeField(help_text='timestamp with timezone')
    oem_metric = models.CharField(max_length=80, help_text='asset code')
    metric = models.CharField(max_length=80, help_text='asset code')
    value = models.CharField(max_length=80, help_text='asset code')
    

    class Meta:
        db_table = 'timeseries_data'
        #ordering = ['device_id']
        managed = False
        

    def __str__(self):
        return f"{self.device_id} ({self.oem_metric})"

    #@property
    #def device_count(self):
    #    """Return the number of devices associated with this asset"""
    #    return self.devices.count()

    #@property
    #def device_count(self):
    #    """Return the number of devices associated with this asset"""
    #    return self.devices.count()
################################################################################################
#################################################################################################
###############################################################################################

# YieldData matches yield.csv
class YieldData(models.Model):
    id = models.BigAutoField(primary_key=True)
    month = models.CharField(max_length=20)
    country = models.CharField(max_length=50)
    portfolio = models.CharField(max_length=100)
    assetno = models.CharField(max_length=50)
    dc_capacity_mw = models.FloatField(null=True, blank=True)
    ic_approved_budget = models.FloatField(null=True, blank=True)
    expected_budget = models.FloatField(null=True, blank=True)
    weather_loss_or_gain = models.FloatField(null=True, blank=True)
    grid_curtailment = models.FloatField(null=True, blank=True)
    budgeted_grid_curtailment = models.FloatField(null=True, blank=True)
    grid_outage = models.FloatField(null=True, blank=True)
    operation_budget = models.FloatField(null=True, blank=True)
    breakdown_loss = models.FloatField(null=True, blank=True)
    unclassified_loss = models.FloatField(null=True, blank=True)
    actual_generation = models.FloatField(null=True, blank=True)
    string_failure = models.FloatField(null=True, blank=True)
    inverter_failure = models.FloatField(null=True, blank=True)
    mv_failure = models.FloatField(null=True, blank=True)
    hv_failure = models.FloatField(null=True, blank=True)
    ac_failure = models.FloatField(null=True, blank=True)   ####    
    budgeted_irradiation = models.FloatField(null=True, blank=True)   ####
    actual_irradiation = models.FloatField(null=True, blank=True)   ####
    ac_capacity_mw = models.FloatField(null=True, blank=True)    ####
    bess_capacity_mwh = models.FloatField(null=True, blank=True)    ####
    bess_generation_mwh = models.FloatField(null=True, blank=True)   ####
    expected_pr = models.FloatField(null=True, blank=True)
    actual_pr = models.FloatField(null=True, blank=True)
    pr_gap = models.FloatField(null=True, blank=True)
    pr_gap_observation = models.TextField(blank=True)
    pr_gap_action_need_to_taken = models.TextField(blank=True)
    revenue_loss = models.FloatField(null=True, blank=True)
    revenue_loss_observation = models.TextField(blank=True)
    revenue_loss_action_need_to_taken = models.TextField(blank=True)
    # New columns from updated yield.csv
    ppa_rate = models.FloatField(null=True, blank=True, help_text='Power Purchase Agreement rate')
    ic_approved_budget_dollar = models.FloatField(null=True, blank=True, help_text='IC approved budget in dollars')
    expected_budget_dollar = models.FloatField(null=True, blank=True, help_text='Expected budget in dollars')
    actual_generation_dollar = models.FloatField(null=True, blank=True, help_text='Actual generation in dollars')
    operational_budget_dollar = models.FloatField(null=True, blank=True, help_text='Operational budget in dollars')
    revenue_loss_op = models.FloatField(null=True, blank=True, help_text='Revenue loss operational')
    # New columns from yield_v1.csv
    weather_corrected_budget = models.FloatField(null=True, blank=True, help_text='Weather corrected budget')
    actual_curtailment = models.FloatField(null=True, blank=True, help_text='Actual curtailment')
    grid_loss = models.FloatField(null=True, blank=True, help_text='Grid loss')
    scheduled_outage_loss = models.FloatField(null=True, blank=True, help_text='Scheduled outage loss')
    unclassified_loss_percent = models.FloatField(null=True, blank=True, help_text='Unclassified loss percentage')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.assetno} - {self.month}"

# BESSData matches bess.csv
class BESSData(models.Model):
    id = models.BigAutoField(primary_key=True)
    date = models.CharField(max_length=20)
    month = models.CharField(max_length=20)
    country = models.CharField(max_length=50)
    portfolio = models.CharField(max_length=100)
    asset_no = models.CharField(max_length=50)
    battery_capacity_mw = models.FloatField(null=True, blank=True)
    export_energy_kwh = models.FloatField(null=True, blank=True)
    pv_energy_kwh = models.FloatField(null=True, blank=True)
    charge_energy_kwh = models.FloatField(null=True, blank=True)
    discharge_energy_kwh = models.FloatField(null=True, blank=True)
    min_soc = models.FloatField(null=True, blank=True)
    max_soc = models.FloatField(null=True, blank=True)
    min_ess_temperature = models.FloatField(null=True, blank=True)
    max_ess_temperature = models.FloatField(null=True, blank=True)
    min_ess_humidity = models.FloatField(null=True, blank=True)
    max_ess_humidity = models.FloatField(null=True, blank=True)
    rte = models.FloatField(null=True, blank=True)
    actual_no_of_cycles = models.IntegerField(null=True, blank=True, help_text='Actual No of cycles')
    cuf = models.FloatField(null=True, blank=True, help_text='CUF (Capacity Utilization Factor)')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    def __str__(self):
        return f"{self.asset_no} - {self.date}"


class BESSV1Data(models.Model):
    """Enhanced BESS dataset aligned with bessv1 CSV schema"""
    id = models.BigAutoField(primary_key=True)
    month = models.CharField(max_length=20)
    country = models.CharField(max_length=100)
    portfolio = models.CharField(max_length=100)
    asset_no = models.CharField(max_length=100)
    battery_capacity_mwh = models.FloatField(null=True, blank=True)
    actual_pv_energy_kwh = models.FloatField(null=True, blank=True)
    actual_export_energy_kwh = models.FloatField(null=True, blank=True)
    actual_charge_energy_kwh = models.FloatField(null=True, blank=True)
    actual_discharge_energy = models.FloatField(null=True, blank=True)
    actual_pv_grid_kwh = models.FloatField(null=True, blank=True)
    actual_system_losses = models.FloatField(null=True, blank=True)
    min_soc = models.FloatField(null=True, blank=True)
    max_soc = models.FloatField(null=True, blank=True)
    min_ess_temp = models.FloatField(null=True, blank=True)
    max_ess_temp = models.FloatField(null=True, blank=True)
    actual_avg_rte = models.FloatField(null=True, blank=True)
    actual_cuf = models.FloatField(null=True, blank=True)
    actual_no_of_cycles = models.IntegerField(null=True, blank=True)
    budget_pv_energy_kwh = models.FloatField(null=True, blank=True)
    budget_export_energy_kwh = models.FloatField(null=True, blank=True)
    budget_charge_energy_kwh = models.FloatField(null=True, blank=True)
    budget_discharge_energy = models.FloatField(null=True, blank=True)
    budget_pv_grid_kwh = models.FloatField(null=True, blank=True)
    budget_system_losses = models.FloatField(null=True, blank=True)
    budget_cuf = models.FloatField(null=True, blank=True)
    budget_no_of_cycles = models.IntegerField(null=True, blank=True)
    budget_grid_import_kwh = models.FloatField(null=True, blank=True)
    actual_grid_import_kwh = models.FloatField(null=True, blank=True)
    budget_avg_rte = models.FloatField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'bess_v1_data'
        constraints = [
            models.UniqueConstraint(fields=['month', 'asset_no'], name='unique_bess_v1_month_asset')
        ]
        indexes = [
            models.Index(fields=['month'], name='bess_v1_month_idx'),
            models.Index(fields=['portfolio'], name='bess_v1_portfolio_idx'),
        ]

    def __str__(self):
        return f"{self.asset_no} - {self.month}"

# AOCData matches AOC.csv
class AOCData(models.Model):
    id = models.BigAutoField(primary_key=True)
    s_no = models.CharField(max_length=20)
    month = models.CharField(max_length=20)
    asset_no = models.CharField(max_length=50)
    country = models.CharField(max_length=50)
    portfolio = models.CharField(max_length=100)
    remarks = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    def __str__(self):
        return f"{self.asset_no} - {self.month}"

# ICEData matches ICE.csv (normalized)
class ICEData(models.Model):
    id = models.BigAutoField(primary_key=True)
    month = models.CharField(max_length=150)
    portfolio = models.CharField(max_length=100)
    ic_approved = models.FloatField(null=True, blank=True)
    expected = models.FloatField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    def __str__(self):
        return f"{self.portfolio} - {self.month}"


class ICVSEXVSCURData(models.Model):
    """IC Budget vs Expected Generation data"""
    id = models.BigAutoField(primary_key=True)
    country = models.CharField(max_length=50)
    portfolio = models.CharField(max_length=100)
    dc_capacity_mwp = models.FloatField(null=True, blank=True)
    month = models.DateField(help_text='Month as first day of the month')
    ic_approved_budget_mwh = models.FloatField(null=True, blank=True)
    expected_budget_mwh = models.FloatField(null=True, blank=True)
    actual_generation_mwh = models.FloatField(null=True, blank=True)
    grid_curtailment_budget_mwh = models.FloatField(null=True, blank=True)
    actual_curtailment_mwh = models.FloatField(null=True, blank=True)
    budget_irradiation_kwh_m2 = models.FloatField(null=True, blank=True)
    actual_irradiation_kwh_m2 = models.FloatField(null=True, blank=True)
    expected_pr_percent = models.FloatField(null=True, blank=True)
    actual_pr_percent = models.FloatField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'icvsexvscur_data'
        ordering = ['month', 'portfolio']

    def __str__(self):
        return f"{self.portfolio} - {self.month.strftime('%b %Y')}"
    
    @property
    def month_year_display(self):
        """Return month and year in a readable format like 'Apr 2025'"""
        return self.month.strftime('%b %Y')

# MapData matches map_data.csv
class MapData(models.Model):
    id = models.BigAutoField(primary_key=True)
    asset_no = models.CharField(max_length=50)
    country = models.CharField(max_length=50)
    site_name = models.CharField(max_length=200)
    portfolio = models.CharField(max_length=100)
    installation_type = models.CharField(max_length=100)
    dc_capacity_mwp = models.FloatField(null=True, blank=True)
    pcs_capacity = models.CharField(max_length=50, blank=True)
    battery_capacity_mw = models.CharField(max_length=50, blank=True)
    plant_type = models.CharField(max_length=50)
    offtaker = models.CharField(max_length=200)
    cod = models.CharField(max_length=50)
    latitude = models.FloatField(null=True, blank=True)
    longitude = models.FloatField(null=True, blank=True)
    ac_capacity = models.FloatField(null=True, blank=True)    ####
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    def __str__(self):
        return f"{self.site_name} - {self.asset_no}"

# MinamataStringLossData matches Monthly String Loss.csv
class MinamataStringLossData(models.Model):
    id = models.BigAutoField(primary_key=True)
    month = models.CharField(max_length=20)
    no_of_strings_breakdown = models.IntegerField(null=True, blank=True)
    no_of_strings_modules_damaged = models.CharField(max_length=50, blank=True)
    designed_dc_capacity_mwh = models.FloatField(null=True, blank=True)
    breakdown_dc_capacity_mwh = models.FloatField(null=True, blank=True)
    operational_dc_capacity_mwh = models.FloatField(null=True, blank=True)
    budgeted_gen_mwh = models.FloatField(null=True, blank=True)
    actual_gen_mwh = models.FloatField(null=True, blank=True)
    loss_due_to_string_failure_mwh = models.FloatField(null=True, blank=True)
    loss_in_jpy = models.BigIntegerField(null=True, blank=True)
    loss_in_usd = models.BigIntegerField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    def __str__(self):
        return f"{self.month} - {self.no_of_strings_breakdown}"

# DataImportLog for tracking imports
class DataImportLog(models.Model):
    """Model to track data import history"""
    STATUS_CHOICES = [
        ('success', 'Success'),
        ('failed', 'Failed'),
        ('partial', 'Partial Success'),
    ]
    
    file_name = models.CharField(max_length=255)
    data_type = models.CharField(max_length=50)
    upload_mode = models.CharField(max_length=20, default='append')
    records_imported = models.IntegerField(default=0)
    records_skipped = models.IntegerField(default=0)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='success')
    error_message = models.TextField(blank=True, null=True)
    imported_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='data_imports')
    import_date = models.DateTimeField(auto_now_add=True)
    file_size = models.IntegerField(default=0, help_text="File size in bytes")
    processing_time = models.FloatField(default=0.0, help_text="Processing time in seconds")
    
    class Meta:
        ordering = ['-import_date']
        verbose_name = 'Data Import Log'
        verbose_name_plural = 'Data Import Logs'
    
    def __str__(self):
        return f"{self.file_name} - {self.data_type} - {self.import_date.strftime('%Y-%m-%d %H:%M')}"
    
    @property
    def file_size_mb(self):
        """Return file size in MB"""
        return round(self.file_size / (1024 * 1024), 2)
    
    @property
    def success_rate(self):
        """Calculate success rate as percentage"""
        total = self.records_imported + self.records_skipped
        if total == 0:
            return 0
        return round((self.records_imported / total) * 100, 1)

# Daily Data Models for new CSV files

class ActualGenerationDailyData(models.Model):
    """Daily actual generation data for each asset"""
    id = models.BigAutoField(primary_key=True)
    date = models.DateField(help_text='Date of generation')
    asset_code = models.CharField(max_length=50, help_text='Asset code (e.g., KR_BW_01, JP-MINA)')
    generation_kwh = models.FloatField(null=True, blank=True, help_text='Daily generation in kWh')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'actual_generation_daily_data'
        unique_together = [['date', 'asset_code']]
        ordering = ['date', 'asset_code']

    def __str__(self):
        return f"{self.asset_code} - {self.date}"

class ExpectedBudgetDailyData(models.Model):
    """Daily expected budget data for each asset"""
    id = models.BigAutoField(primary_key=True)
    date = models.DateField(help_text='Date of budget')
    asset_code = models.CharField(max_length=50, help_text='Asset code (e.g., KR_BW_01, JP-MINA)')
    expected_budget_kwh = models.FloatField(null=True, blank=True, help_text='Daily expected budget in kWh')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'expected_budget_daily_data'
        unique_together = [['date', 'asset_code']]
        ordering = ['date', 'asset_code']

    def __str__(self):
        return f"{self.asset_code} - {self.date}"

class BudgetGIIDailyData(models.Model):
    """Daily budget GII data for each asset"""
    id = models.BigAutoField(primary_key=True)
    date = models.DateField(help_text='Date of budget GII')
    asset_code = models.CharField(max_length=50, help_text='Asset code (e.g., KR_BW_01, JP-MINA)')
    budget_gii_kwh = models.FloatField(null=True, blank=True, help_text='Daily budget GII in kWh')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'budget_gii_daily_data'
        unique_together = [['date', 'asset_code']]
        ordering = ['date', 'asset_code']

    def __str__(self):
        return f"{self.asset_code} - {self.date}"

class ActualGIIDailyData(models.Model):
    """Daily actual GII data for each asset"""
    id = models.BigAutoField(primary_key=True)
    date = models.DateField(help_text='Date of actual GII')
    asset_code = models.CharField(max_length=50, help_text='Asset code (e.g., KR_BW_01, JP-MINA)')
    actual_gii_kwh = models.FloatField(null=True, blank=True, help_text='Daily actual GII in kWh')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'actual_gii_daily_data'
        unique_together = [['date', 'asset_code']]
        ordering = ['date', 'asset_code']

    def __str__(self):
        return f"{self.asset_code} - {self.date}"

class ICApprovedBudgetDailyData(models.Model):
    """Daily IC approved budget data for each asset"""
    id = models.BigAutoField(primary_key=True)
    date = models.DateField(help_text='Date of IC approved budget')
    asset_code = models.CharField(max_length=50, help_text='Asset code (e.g., KR_BW_01, JP-MINA)')
    ic_approved_budget_kwh = models.FloatField(null=True, blank=True, help_text='Daily IC approved budget in kWh')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'ic_approved_budget_daily_data'
        unique_together = [['date', 'asset_code']]
        ordering = ['date', 'asset_code']
    
    def __str__(self):
        return f"{self.asset_code} - {self.date} - {self.ic_approved_budget_kwh}"
    

class LossCalculationData(models.Model):
    """Loss calculation data for breakdowns and incidents"""
    id = models.BigAutoField(primary_key=True)
    l = models.CharField(max_length=20, blank=True, help_text='Loss ID')
    month = models.CharField(max_length=20, help_text='Month (e.g., 25-Jan)')
    start_date = models.CharField(max_length=20, blank=True, help_text='Start date')
    start_time = models.CharField(max_length=20, blank=True, help_text='Start time')
    end_date = models.CharField(max_length=20, blank=True, help_text='End date')
    end_time = models.CharField(max_length=20, blank=True, help_text='End time')
    asset_no = models.CharField(max_length=50, help_text='Asset number')
    country = models.CharField(max_length=50, blank=True, help_text='Country')
    portfolio = models.CharField(max_length=100, blank=True, help_text='Portfolio')
    dc_capacity = models.CharField(max_length=50, blank=True, help_text='DC Capacity')
    site_name = models.CharField(max_length=200, blank=True, help_text='Site name')
    category = models.CharField(max_length=100, blank=True, help_text='Category')
    subcategory = models.CharField(max_length=100, blank=True, help_text='Subcategory')
    breakdown_equipment = models.CharField(max_length=200, blank=True, help_text='Breakdown equipment')
    bd_description = models.TextField(blank=True, help_text='Breakdown description')
    action_to_be_taken = models.TextField(blank=True, help_text='Action to be taken')
    status_of_bd = models.CharField(max_length=50, blank=True, help_text='Status of breakdown')
    breakdown_dc_capacity_kw = models.FloatField(null=True, blank=True, help_text='Breakdown DC capacity (kW)')
    irradiation_during_breakdown_kwh_m2 = models.FloatField(null=True, blank=True, help_text='Irradiation during breakdown (kWh/M2)')
    budget_pr_percent = models.FloatField(null=True, blank=True, help_text='Budget PR (%)')
    generation_loss_kwh = models.FloatField(null=True, blank=True, help_text='Generation loss (kWh)')
    ppa_rate_usd = models.FloatField(null=True, blank=True, help_text='PPA rate in USD')
    revenue_loss_usd = models.FloatField(null=True, blank=True, help_text='Revenue loss in USD')
    severity = models.IntegerField(null=True, blank=True, help_text='Severity level')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'loss_calculation_data'
        ordering = ['month', 'asset_no']
    
    def __str__(self):
        return f"{self.asset_no} - {self.month} - {self.category}"
    

class UserProfile(models.Model):
    ROLE_CHOICES = get_role_choices()
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    role = models.CharField(max_length=20, choices=ROLE_CHOICES)
    
    # Hierarchical access control - using simple text fields instead of M2M
    accessible_countries = models.TextField(blank=True, help_text="Comma-separated list of countries the user has access to")
    accessible_portfolios = models.TextField(blank=True, help_text="Comma-separated list of portfolios the user has access to")
    accessible_sites = models.TextField(blank=True, help_text="Comma-separated list of specific sites the user has access to")
    app_access = models.TextField(
        blank=True,
        default="",
        help_text="Comma-separated list of application access keys granted to the user.",
    )
    
    # Feature access control
    ticketing_access = models.BooleanField(default=False, help_text="Whether user has access to the ticketing system")
    
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='created_users')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username} - {self.role}"

    # ------------------------------------------------------------------
    # Capability helpers
    # ------------------------------------------------------------------
    def _app_access_list(self):
        if not self.app_access:
            return []
        return [key.strip() for key in self.app_access.split(",") if key.strip()]

    def set_app_access(self, app_keys):
        cleaned = sorted({key.strip() for key in app_keys if key})
        self.app_access = ",".join(cleaned)
        self.ticketing_access = "ticketing" in cleaned

    def has_app_access(self, app_key: str) -> bool:
        if not app_key:
            return True
        if getattr(self.user, "is_superuser", False):
            return True
        apps = set(self._app_access_list())
        if not apps:
            # Default legacy behaviour: assume web access
            return app_key == "web"
        return app_key in apps

    def list_app_access(self):
        apps = self._app_access_list()
        if not apps:
            apps = ["web"]
        return [APP_ACCESS_LABELS.get(key, key.title()) for key in apps]

    def has_capability(self, capability: str) -> bool:
        """Return True if this profile grants the specified capability."""
        return role_has_capability(self.role, capability)

    def has_any_capability(self, capabilities) -> bool:
        """
        Return True if the profile grants at least one capability in the iterable.
        """
        if not capabilities:
            return False
        return any(self.has_capability(capability) for capability in capabilities)

    def list_capabilities(self, *, expand_all: bool = False):
        """
        Return the capability keys granted to this profile.

        Args:
            expand_all: When True, expands ALL_CAPABILITIES into explicit keys.
        """
        return get_capabilities_for_role(self.role, expand_all=expand_all)
    
    def get_accessible_sites(self):
        """
        Get all sites the user has access to based on hierarchical access control:
        1. If user has specific sites assigned, return only those sites
        2. If user has portfolios assigned, return all sites in those portfolios
        3. If user has countries assigned, return all sites in those countries
        4. If user is admin, return all sites
        """
        if self.has_capability('ticketing.view_all_sites'):
            return AssetList.objects.all()
        
        # If specific sites are assigned, return only those sites
        if self.accessible_sites:
            site_codes = [code.strip() for code in self.accessible_sites.split(',') if code.strip()]
            if site_codes:
                # Try to match by asset_code first, then by asset_number
                sites = AssetList.objects.filter(asset_code__in=site_codes)
                if not sites.exists():
                    sites = AssetList.objects.filter(asset_number__in=site_codes)
                return sites
        
        # If portfolios are assigned, return all sites in those portfolios
        if self.accessible_portfolios:
            portfolio_names = [name.strip() for name in self.accessible_portfolios.split(',') if name.strip()]
            if portfolio_names:
                return AssetList.objects.filter(portfolio__in=portfolio_names)
        
        # If countries are assigned, return all sites in those countries
        if self.accessible_countries:
            country_names = [name.strip() for name in self.accessible_countries.split(',') if name.strip()]
            if country_names:
                return AssetList.objects.filter(country__in=country_names)
        
        # No access
        return AssetList.objects.none()

    def get_distinct_countries(self):
        """
        Get distinct country names for display purposes
        """
        if self.accessible_countries:
            return [name.strip() for name in self.accessible_countries.split(',') if name.strip()]
        return []

    def get_distinct_portfolios(self):
        """
        Get distinct portfolio names for display purposes
        """
        if self.accessible_portfolios:
            return [name.strip() for name in self.accessible_portfolios.split(',') if name.strip()]
        return []

    def get_accessible_countries(self):
        """
        Get all countries the user has access to
        Combines all access sources and deduplicates
        """
        if self.has_capability('ticketing.view_all_sites'):
            # For admin users, get all countries and deduplicate
            all_countries = list(AssetList.objects.values_list('country', flat=True))
            return list(set(all_countries))
        
        countries = set()
        
        # If specific sites are assigned, get countries of those sites
        if self.accessible_sites:
            site_codes = [code.strip() for code in self.accessible_sites.split(',') if code.strip()]
            if site_codes:
                # Try to match by asset_code first, then by asset_number
                sites = AssetList.objects.filter(asset_code__in=site_codes)
                if not sites.exists():
                    sites = AssetList.objects.filter(asset_number__in=site_codes)
                site_countries = list(sites.values_list('country', flat=True))
                countries.update(site_countries)
        
        # If portfolios are assigned, get countries of sites in those portfolios
        if self.accessible_portfolios:
            portfolio_names = [name.strip() for name in self.accessible_portfolios.split(',') if name.strip()]
            if portfolio_names:
                portfolio_countries = list(AssetList.objects.filter(portfolio__in=portfolio_names).values_list('country', flat=True))
                countries.update(portfolio_countries)
        
        # If countries are directly assigned, add those countries
        if self.accessible_countries:
            direct_countries = [name.strip() for name in self.accessible_countries.split(',') if name.strip()]
            countries.update(direct_countries)
        
        return list(countries)

    def get_accessible_portfolios(self):
        """
        Get all portfolios the user has access to
        Combines all access sources and deduplicates
        """
        if self.has_capability('ticketing.view_all_sites'):
            # For admin users, get all portfolios and deduplicate
            all_portfolios = list(AssetList.objects.values_list('portfolio', flat=True))
            return list(set(all_portfolios))
        
        portfolios = set()
        
        # If specific sites are assigned, get portfolios of those sites
        if self.accessible_sites:
            site_codes = [code.strip() for code in self.accessible_sites.split(',') if code.strip()]
            if site_codes:
                # Try to match by asset_code first, then by asset_number
                sites = AssetList.objects.filter(asset_code__in=site_codes)
                if not sites.exists():
                    sites = AssetList.objects.filter(asset_number__in=site_codes)
                site_portfolios = list(sites.values_list('portfolio', flat=True))
                portfolios.update(site_portfolios)
        
        # If portfolios are directly assigned, add those portfolios
        if self.accessible_portfolios:
            direct_portfolios = [name.strip() for name in self.accessible_portfolios.split(',') if name.strip()]
            portfolios.update(direct_portfolios)
        
        # If countries are assigned, get portfolios of sites in those countries
        if self.accessible_countries:
            country_names = [name.strip() for name in self.accessible_countries.split(',') if name.strip()]
            if country_names:
                country_portfolios = list(AssetList.objects.filter(country__in=country_names).values_list('portfolio', flat=True))
                portfolios.update(country_portfolios)
        
        return list(portfolios)

    def has_access_to_site(self, site_code):
        """
        Check if user has access to a specific site
        """
        if self.has_capability('ticketing.view_all_sites'):
            return True
        
        # Check if site is in accessible_sites
        if self.accessible_sites:
            site_codes = [code.strip() for code in self.accessible_sites.split(',') if code.strip()]
            if site_code in site_codes:
                return True
        
        # Check if site is in accessible portfolios
        if self.accessible_portfolios:
            try:
                # Try to find site by asset_code first, then by asset_number
                try:
                    site = AssetList.objects.get(asset_code=site_code)
                except AssetList.DoesNotExist:
                    site = AssetList.objects.get(asset_number=site_code)
                
                portfolio_names = [name.strip() for name in self.accessible_portfolios.split(',') if name.strip()]
                if site.portfolio in portfolio_names:
                    return True
            except AssetList.DoesNotExist:
                pass
        
        # Check if site is in accessible countries
        if self.accessible_countries:
            try:
                # Try to find site by asset_code first, then by asset_number
                try:
                    site = AssetList.objects.get(asset_code=site_code)
                except AssetList.DoesNotExist:
                    site = AssetList.objects.get(asset_number=site_code)
                
                country_names = [name.strip() for name in self.accessible_countries.split(',') if name.strip()]
                if site.country in country_names:
                    return True
            except AssetList.DoesNotExist:
                pass
        
        return False

    def has_access_to_country(self, country):
        """
        Check if user has access to a specific country
        """
        if self.has_capability('ticketing.view_all_sites'):
            return True
        
        if self.accessible_countries:
            country_names = [name.strip() for name in self.accessible_countries.split(',') if name.strip()]
            return country in country_names
        
        return False

    def has_access_to_portfolio(self, portfolio):
        """
        Check if user has access to a specific portfolio
        """
        if self.has_capability('ticketing.view_all_sites'):
            return True
        
        if self.accessible_portfolios:
            portfolio_names = [name.strip() for name in self.accessible_portfolios.split(',') if name.strip()]
            return portfolio in portfolio_names
        
        return False

    def get_role(self):
        return self.role

    def set_role(self, role):
        self.role = role
        self.save()


class RealTimeKPI(models.Model):
    """Real-time KPI data calculated from timeseries database and Realtime.csv"""
    id = models.BigAutoField(primary_key=True)
    asset_code = models.CharField(max_length=255, help_text="Asset code")
    date = models.DateField(help_text="Date for which KPI is calculated")
    daily_kwh = models.FloatField(null=True, blank=True, help_text="Daily energy generation in kWh")
    daily_irr = models.FloatField(null=True, blank=True, help_text="Daily irradiation in kWh/m²")
    
    # New columns from Realtime.csv
    daily_generation_mwh = models.FloatField(null=True, blank=True, help_text="Daily generation in MWh from Realtime.csv")
    daily_irradiation_mwh = models.FloatField(null=True, blank=True, help_text="Daily irradiation in MWh from Realtime.csv")
    daily_ic_mwh = models.FloatField(null=True, blank=True, help_text="Daily IC budget in MWh from Realtime.csv")
    daily_expected_mwh = models.FloatField(null=True, blank=True, help_text="Daily expected budget in MWh from Realtime.csv")
    daily_budget_irradiation_mwh = models.FloatField(null=True, blank=True, help_text="Daily budget irradiation in MWh from Realtime.csv")
    expect_pr = models.FloatField(null=True, blank=True, help_text="Expected PR from Realtime.csv")
    actual_pr = models.FloatField(null=True, blank=True, help_text="Actual PR from Realtime.csv")
    dc_capacity_mw = models.FloatField(null=True, blank=True, help_text="DC capacity in MW from Realtime.csv")
    country = models.CharField(max_length=100, null=True, blank=True, help_text="Country from Realtime.csv")
    portfolio = models.CharField(max_length=100, null=True, blank=True, help_text="Portfolio from Realtime.csv")
    
    last_updated = models.DateTimeField(auto_now=True, help_text="Timestamp when data was last updated")
    is_frozen = models.BooleanField(default=False, help_text="True if data is frozen after 8 PM local time")
    site_state = models.CharField(
        max_length=20, 
        choices=[
            ('active', 'Active'),
            ('inactive', 'Inactive'),
            ('unknown', 'Unknown')
        ],
        default='unknown',
        null=True,
        help_text="Site state based on daily_kwh increments - active if daily_kwh increased, inactive if no increment"
    )
    
    class Meta:
        db_table = 'real_time_kpi'
        unique_together = [['asset_code', 'date']]
        ordering = ['-date', 'asset_code']
        indexes = [
            models.Index(fields=['asset_code', 'date']),
            models.Index(fields=['date']),
            models.Index(fields=['last_updated']),
        ]
    
    def __str__(self):
        return f"{self.asset_code} - {self.date}"
    
    @property
    def asset(self):
        """Get related asset information"""
        try:
            return AssetList.objects.get(asset_code=self.asset_code)
        except AssetList.DoesNotExist:
            return None
    
    def update_site_state(self):
        """
        Update site state based on daily_kwh increments for the current date.
        Active: if daily_kwh has increased compared to the previous record for the same date
        Inactive: if daily_kwh has not increased compared to the previous record for the same date
        Unknown: if no previous data exists or daily_kwh is None
        """
        if self.daily_kwh is None:
            self.site_state = 'unknown'
            return
        
        # Get the previous record for the same asset and date (ordered by last_updated)
        previous_record = RealTimeKPI.objects.filter(
            asset_code=self.asset_code,
            date=self.date,
            last_updated__lt=self.last_updated
        ).order_by('-last_updated').first()
        
        if previous_record is None or previous_record.daily_kwh is None:
            # No previous data exists, set as unknown
            self.site_state = 'unknown'
        else:
            # Compare daily_kwh values
            if self.daily_kwh > previous_record.daily_kwh:
                self.site_state = 'active'
            else:
                self.site_state = 'inactive'
    
    def save(self, *args, **kwargs):
        """Override save to automatically update site state"""
        # Don't update site_state on the first save (when id is None)
        if self.id is not None:
            self.update_site_state()
        super().save(*args, **kwargs)
        
class Feedback(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('attended', 'Attended'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    user_email = models.EmailField()
    subject = models.CharField(max_length=200)
    message = models.TextField()
    attended_status = models.CharField(
        max_length=20, 
        choices=STATUS_CHOICES, 
        default='pending',
        help_text='Status of feedback handling'
    )
    attended_at = models.DateTimeField(null=True, blank=True, help_text='When feedback was marked as attended')
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"Feedback from {self.user.username} - {self.subject}"
    
    class Meta:
        db_table = 'main_feedback'
        verbose_name = 'Feedback'
        verbose_name_plural = 'Feedback'
        ordering = ['-created_at']


class FeedbackImage(models.Model):
    feedback = models.ForeignKey(Feedback, on_delete=models.CASCADE, related_name='images')
    image = models.ImageField(upload_to='feedback_images/')
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"Image for {self.feedback.subject}"
    
    class Meta:
        db_table = 'main_feedback_image'
        verbose_name = 'Feedback Image'
        verbose_name_plural = 'Feedback Images'
        ordering = ['created_at']


class UserActivityLog(models.Model):
    """Model to track all user activity and requests"""
    ACTION_CHOICES = [
        ('login', 'Login'),
        ('logout', 'Logout'),
        ('view', 'Page View'),
        ('create', 'Create'),
        ('update', 'Update'),
        ('delete', 'Delete'),
        ('download', 'Download'),
        ('upload', 'Upload'),
        ('api_call', 'API Call'),
        ('failed_login', 'Failed Login'),
        ('password_reset', 'Password Reset'),
        ('permission_denied', 'Permission Denied'),
    ]
    
    RISK_LEVEL_CHOICES = [
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
        ('critical', 'Critical'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    session_key = models.CharField(max_length=40, blank=True, null=True)
    ip_address = models.GenericIPAddressField()
    peer_ip = models.CharField(
        max_length=45,
        blank=True,
        default='',
        help_text='REMOTE_ADDR as seen by Django (e.g. proxy loopback vs direct)',
    )
    forwarded_for = models.TextField(
        blank=True,
        default='',
        help_text='Raw HTTP X-Forwarded-For header',
    )
    client_ip = models.GenericIPAddressField(
        help_text='Resolved client IP: first X-Forwarded-For hop when present, else peer',
    )
    user_agent = models.TextField()
    action = models.CharField(max_length=20, choices=ACTION_CHOICES)
    resource = models.CharField(max_length=500, help_text='URL path or resource accessed')
    method = models.CharField(max_length=10, help_text='HTTP method (GET, POST, etc.)')
    status_code = models.IntegerField(help_text='HTTP status code')
    response_time = models.FloatField(help_text='Response time in seconds')
    
    # Geolocation data
    country = models.CharField(max_length=100, blank=True)
    city = models.CharField(max_length=100, blank=True)
    region = models.CharField(max_length=100, blank=True)
    
    # Request details
    request_data = models.JSONField(default=dict, blank=True, help_text='Request parameters and data')
    response_size = models.IntegerField(default=0, help_text='Response size in bytes')
    
    # Security analysis
    is_suspicious = models.BooleanField(default=False)
    risk_level = models.CharField(max_length=10, choices=RISK_LEVEL_CHOICES, default='low')
    security_flags = models.JSONField(default=list, blank=True, help_text='Security flags raised')
    
    # Timestamps
    timestamp = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'user_activity_log'
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['user', 'timestamp']),
            models.Index(fields=['ip_address', 'timestamp']),
            models.Index(fields=['action', 'timestamp']),
            models.Index(fields=['is_suspicious']),
            models.Index(fields=['risk_level']),
            models.Index(fields=['timestamp']),
        ]
    
    def __str__(self):
        user_str = self.user.username if self.user else 'Anonymous'
        return f"{user_str} - {self.action} - {self.resource} at {self.timestamp}"


class ActiveUserSession(models.Model):
    """Model to track active user sessions"""
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    session_key = models.CharField(max_length=40, unique=True)
    ip_address = models.GenericIPAddressField()
    user_agent = models.TextField()
    last_activity = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)
    
    # Geolocation
    country = models.CharField(max_length=100, blank=True)
    city = models.CharField(max_length=100, blank=True)
    
    class Meta:
        db_table = 'active_user_session'
        ordering = ['-last_activity']
        indexes = [
            models.Index(fields=['user', 'is_active']),
            models.Index(fields=['session_key']),
            models.Index(fields=['last_activity']),
            models.Index(fields=['is_active']),
        ]
    
    def __str__(self):
        return f"{self.user.username} - {self.ip_address} - Active: {self.is_active}"
    
    @property
    def duration(self):
        """Get session duration"""
        from django.utils import timezone
        return timezone.now() - self.created_at


class SecurityAlert(models.Model):
    """Model to track security alerts and malicious activities"""
    ALERT_TYPE_CHOICES = [
        ('brute_force', 'Brute Force Attack'),
        ('suspicious_location', 'Suspicious Location'),
        ('rate_limit_exceeded', 'Rate Limit Exceeded'),
        ('unusual_activity', 'Unusual Activity'),
        ('sql_injection', 'SQL Injection Attempt'),
        ('xss_attempt', 'XSS Attempt'),
        ('unauthorized_access', 'Unauthorized Access'),
        ('data_breach_attempt', 'Data Breach Attempt'),
        ('malicious_user_agent', 'Malicious User Agent'),
        ('suspicious_request', 'Suspicious Request'),
    ]
    
    SEVERITY_CHOICES = [
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
        ('critical', 'Critical'),
    ]
    
    STATUS_CHOICES = [
        ('open', 'Open'),
        ('investigating', 'Investigating'),
        ('resolved', 'Resolved'),
        ('false_positive', 'False Positive'),
    ]
    
    alert_type = models.CharField(max_length=30, choices=ALERT_TYPE_CHOICES)
    severity = models.CharField(max_length=10, choices=SEVERITY_CHOICES)
    status = models.CharField(max_length=15, choices=STATUS_CHOICES, default='open')
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    ip_address = models.GenericIPAddressField()
    user_agent = models.TextField(blank=True)
    
    title = models.CharField(max_length=200)
    description = models.TextField()
    details = models.JSONField(default=dict, help_text='Additional alert details')
    
    # Related activity log entries
    related_activities = models.ManyToManyField(UserActivityLog, blank=True)
    
    # Response
    resolved_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='resolved_alerts')
    resolved_at = models.DateTimeField(null=True, blank=True)
    resolution_notes = models.TextField(blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'security_alert'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['alert_type', 'severity']),
            models.Index(fields=['status']),
            models.Index(fields=['created_at']),
            models.Index(fields=['ip_address']),
        ]
    
    def __str__(self):
        return f"{self.get_severity_display()} - {self.title} - {self.created_at}"


class IPBlockingLog(models.Model):
    """Model to track all IP blocking activities and decisions"""
    BLOCK_TYPE_CHOICES = [
        ('automatic', 'Automatic Block'),
        ('manual', 'Manual Block'),
        ('temporary', 'Temporary Block'),
        ('permanent', 'Permanent Block'),
    ]
    
    BLOCK_REASON_CHOICES = [
        ('high_risk_pattern', 'High Risk Pattern'),
        ('malicious_user_agent', 'Malicious User Agent'),
        ('critical_exploit', 'Critical Exploit'),
        ('failed_logins', 'Excessive Failed Logins'),
        ('rate_limit_violation', 'Rate Limit Violation'),
        ('suspicious_activity', 'Suspicious Activity'),
        ('known_malicious', 'Known Malicious IP'),
        ('brute_force', 'Brute Force Attack'),
        ('sql_injection', 'SQL Injection Attempt'),
        ('xss_attempt', 'XSS Attempt'),
        ('directory_traversal', 'Directory Traversal'),
        ('command_injection', 'Command Injection'),
        ('other', 'Other'),
    ]
    
    STATUS_CHOICES = [
        ('active', 'Active'),
        ('expired', 'Expired'),
        ('unblocked', 'Unblocked'),
        ('whitelisted', 'Whitelisted'),
    ]
    
    ip_address = models.GenericIPAddressField(help_text='Blocked IP address')
    block_type = models.CharField(max_length=15, choices=BLOCK_TYPE_CHOICES, default='automatic')
    block_reason = models.CharField(max_length=25, choices=BLOCK_REASON_CHOICES)
    reason_details = models.TextField(blank=True, help_text='Detailed reason for blocking')
    
    # Blocking details
    blocked_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, 
                                 help_text='User who initiated the block (if manual)')
    blocked_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(null=True, blank=True, help_text='When the block expires (if temporary)')
    status = models.CharField(max_length=15, choices=STATUS_CHOICES, default='active')
    
    # Context information
    user_agent = models.TextField(blank=True, help_text='User agent when blocked')
    country = models.CharField(max_length=100, blank=True)
    city = models.CharField(max_length=100, blank=True)
    region = models.CharField(max_length=100, blank=True)
    
    # Blocking statistics
    failed_attempts = models.IntegerField(default=0, help_text='Number of failed attempts before blocking')
    suspicious_activities = models.IntegerField(default=0, help_text='Number of suspicious activities detected')
    
    # Resolution
    unblocked_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, 
                                   related_name='unblocked_ips', help_text='User who unblocked the IP')
    unblocked_at = models.DateTimeField(null=True, blank=True)
    unblock_reason = models.TextField(blank=True, help_text='Reason for unblocking')
    
    # Additional metadata
    metadata = models.JSONField(default=dict, blank=True, help_text='Additional blocking metadata')
    
    class Meta:
        db_table = 'ip_blocking_log'
        ordering = ['-blocked_at']
        indexes = [
            models.Index(fields=['ip_address', 'status']),
            models.Index(fields=['block_type', 'block_reason']),
            models.Index(fields=['blocked_at']),
            models.Index(fields=['status', 'expires_at']),
            models.Index(fields=['country', 'city']),
        ]
    
    def __str__(self):
        return f"IP {self.ip_address} - {self.get_block_reason_display()} - {self.blocked_at}"
    
    @property
    def is_expired(self):
        """Check if the block has expired"""
        if not self.expires_at:
            return False
        return timezone.now() > self.expires_at
    
    @property
    def is_active(self):
        """Check if the block is currently active"""
        return self.status == 'active' and not self.is_expired


class UserBlockingLog(models.Model):
    """Model to track all user account blocking activities and decisions"""
    BLOCK_TYPE_CHOICES = [
        ('automatic', 'Automatic Block'),
        ('manual', 'Manual Block'),
        ('temporary', 'Temporary Block'),
        ('permanent', 'Permanent Block'),
    ]
    
    BLOCK_REASON_CHOICES = [
        ('suspicious_activity', 'Suspicious Activity'),
        ('failed_logins', 'Excessive Failed Logins'),
        ('security_violation', 'Security Violation'),
        ('policy_violation', 'Policy Violation'),
        ('account_compromise', 'Account Compromise'),
        ('brute_force', 'Brute Force Attack'),
        ('malicious_behavior', 'Malicious Behavior'),
        ('other', 'Other'),
    ]
    
    STATUS_CHOICES = [
        ('active', 'Active'),
        ('expired', 'Expired'),
        ('unblocked', 'Unblocked'),
        ('account_deleted', 'Account Deleted'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, help_text='Blocked user account')
    block_type = models.CharField(max_length=15, choices=BLOCK_TYPE_CHOICES, default='automatic')
    block_reason = models.CharField(max_length=25, choices=BLOCK_REASON_CHOICES)
    reason_details = models.TextField(blank=True, help_text='Detailed reason for blocking')
    
    # Blocking details
    blocked_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, 
                                 related_name='blocked_users', help_text='User who initiated the block')
    blocked_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(null=True, blank=True, help_text='When the block expires')
    status = models.CharField(max_length=15, choices=STATUS_CHOICES, default='active')
    
    # Context information
    ip_address = models.GenericIPAddressField(help_text='IP address when blocked')
    user_agent = models.TextField(blank=True, help_text='User agent when blocked')
    country = models.CharField(max_length=100, blank=True)
    city = models.CharField(max_length=100, blank=True)
    
    # Blocking statistics
    failed_attempts = models.IntegerField(default=0, help_text='Number of failed attempts before blocking')
    suspicious_activities = models.IntegerField(default=0, help_text='Number of suspicious activities detected')
    
    # Resolution
    unblocked_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, 
                                   related_name='unblocked_users', help_text='User who unblocked the account')
    unblocked_at = models.DateTimeField(null=True, blank=True)
    unblock_reason = models.TextField(blank=True, help_text='Reason for unblocking')
    
    # Additional metadata
    metadata = models.JSONField(default=dict, blank=True, help_text='Additional blocking metadata')
    
    class Meta:
        db_table = 'user_blocking_log'
        ordering = ['-blocked_at']
        indexes = [
            models.Index(fields=['user', 'status']),
            models.Index(fields=['block_type', 'block_reason']),
            models.Index(fields=['blocked_at']),
            models.Index(fields=['status', 'expires_at']),
            models.Index(fields=['ip_address']),
        ]
    
    def __str__(self):
        return f"User {self.user.username} - {self.get_block_reason_display()} - {self.blocked_at}"
    
    @property
    def is_expired(self):
        """Check if the block has expired"""
        if not self.expires_at:
            return False
        return timezone.now() > self.expires_at
    
    @property
    def is_active(self):
        """Check if the block is currently active"""
        return self.status == 'active' and not self.is_expired


class BlockedIP(models.Model):
    """Model for persistent IP blocking management"""
    STATUS_CHOICES = [
        ('active', 'Active'),
        ('inactive', 'Inactive'),
        ('whitelisted', 'Whitelisted'),
    ]
    
    PRIORITY_CHOICES = [
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
        ('critical', 'Critical'),
    ]
    
    ip_address = models.GenericIPAddressField(unique=True, help_text='Blocked IP address')
    status = models.CharField(max_length=15, choices=STATUS_CHOICES, default='active')
    priority = models.CharField(max_length=10, choices=PRIORITY_CHOICES, default='medium')
    
    # Blocking details
    reason = models.CharField(max_length=200, help_text='Reason for blocking')
    description = models.TextField(blank=True, help_text='Detailed description')
    blocked_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # Expiration
    expires_at = models.DateTimeField(null=True, blank=True, help_text='When the block expires')
    
    # Statistics
    block_count = models.IntegerField(default=1, help_text='Number of times this IP has been blocked')
    last_seen = models.DateTimeField(null=True, blank=True, help_text='Last time this IP was seen')
    
    # Additional metadata
    metadata = models.JSONField(default=dict, blank=True, help_text='Additional IP metadata')
    
    class Meta:
        db_table = 'blocked_ip'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['ip_address', 'status']),
            models.Index(fields=['status', 'priority']),
            models.Index(fields=['created_at']),
            models.Index(fields=['expires_at']),
        ]
    
    def __str__(self):
        return f"Blocked IP: {self.ip_address} - {self.reason}"
    
    @property
    def is_expired(self):
        """Check if the block has expired"""
        if not self.expires_at:
            return False
        return timezone.now() > self.expires_at
    
    @property
    def is_active(self):
        """Check if the block is currently active"""
        return self.status == 'active' and not self.is_expired


class BlockedUser(models.Model):
    """Model for persistent user account blocking management"""
    STATUS_CHOICES = [
        ('active', 'Active'),
        ('inactive', 'Inactive'),
        ('whitelisted', 'Whitelisted'),
    ]
    
    PRIORITY_CHOICES = [
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
        ('critical', 'Critical'),
    ]
    
    user = models.OneToOneField(User, on_delete=models.CASCADE, help_text='Blocked user account')
    status = models.CharField(max_length=15, choices=STATUS_CHOICES, default='active')
    priority = models.CharField(max_length=10, choices=PRIORITY_CHOICES, default='medium')
    
    # Blocking details
    reason = models.CharField(max_length=200, help_text='Reason for blocking')
    description = models.TextField(blank=True, help_text='Detailed description')
    blocked_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, 
                                 related_name='blocked_user_accounts')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # Expiration
    expires_at = models.DateTimeField(null=True, blank=True, help_text='When the block expires')
    
    # Statistics
    block_count = models.IntegerField(default=1, help_text='Number of times this user has been blocked')
    last_seen = models.DateTimeField(null=True, blank=True, help_text='Last time this user was seen')
    
    # Additional metadata
    metadata = models.JSONField(default=dict, blank=True, help_text='Additional user metadata')
    
    class Meta:
        db_table = 'blocked_user'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'status']),
            models.Index(fields=['status', 'priority']),
            models.Index(fields=['created_at']),
            models.Index(fields=['expires_at']),
        ]
    
    def __str__(self):
        return f"Blocked User: {self.user.username} - {self.reason}"
    
    @property
    def is_expired(self):
        """Check if the block has expired"""
        if not self.expires_at:
            return False
        return timezone.now() > self.expires_at
    
    @property
    def is_active(self):
        """Check if the block is currently active"""
        return self.status == 'active' and not self.is_expired


# ==========================================
# PV MODULE DATASHEET AND POWER CALCULATION MODELS
# ==========================================


class PVModuleDatasheet(models.Model):
    """PV module datasheet specifications - reusable across installations"""
    id = models.AutoField(primary_key=True)
    module_model = models.CharField(max_length=100, unique=True)
    manufacturer = models.CharField(max_length=100)
    technology = models.CharField(max_length=50, choices=[
        ('mono_perc', 'Mono PERC'), ('poly', 'Poly'), ('thin_film', 'Thin Film'),
        ('bifacial', 'Bifacial'), ('heterojunction', 'HJT'), ('topcon', 'TOPCon'),
    ], default='mono_perc')
    pmax_stc = models.FloatField(validators=[MinValueValidator(0)])
    isc_stc = models.FloatField(validators=[MinValueValidator(0)])
    imp_stc = models.FloatField(validators=[MinValueValidator(0)])
    voc_stc = models.FloatField(validators=[MinValueValidator(0)])
    vmp_stc = models.FloatField(validators=[MinValueValidator(0)])
    module_efficiency_stc = models.FloatField(validators=[MinValueValidator(0), MaxValueValidator(100)])
    noct = models.FloatField(null=True, blank=True, default=45.0, help_text='Nominal Operating Cell Temperature in °C. Typical: 42-47°C. Optional.')
    temp_coeff_pmax = models.FloatField()
    temp_coeff_voc = models.FloatField()
    temp_coeff_isc = models.FloatField()
    temp_coeff_type_voc = models.CharField(max_length=10, choices=[('absolute', 'V/°C'), ('percentage', '%/°C')], default='absolute')
    temp_coeff_type_isc = models.CharField(max_length=10, choices=[('absolute', 'A/°C'), ('percentage', '%/°C')], default='percentage')
    cells_per_module = models.IntegerField(null=True, blank=True, validators=[MinValueValidator(1)], help_text='Number of cells in module (e.g., 60, 72, 144). Optional if not in datasheet.')
    length = models.FloatField(validators=[MinValueValidator(0)])
    width = models.FloatField(validators=[MinValueValidator(0)])
    area = models.FloatField(validators=[MinValueValidator(0)])
    low_irr_200 = models.FloatField(null=True, blank=True)
    low_irr_400 = models.FloatField(null=True, blank=True)
    low_irr_600 = models.FloatField(null=True, blank=True)
    low_irr_800 = models.FloatField(null=True, blank=True)
    warranty_year_1 = models.FloatField(null=True, blank=True)
    warranty_year_25 = models.FloatField(null=True, blank=True)
    linear_degradation_rate = models.FloatField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='created_module_datasheets')
    
    class Meta:
        db_table = 'pv_module_datasheet'
        ordering = ['manufacturer', 'module_model']
        indexes = [models.Index(fields=['manufacturer', 'module_model']), models.Index(fields=['technology'])]
    
    def __str__(self):
        return f"{self.manufacturer} - {self.module_model} ({self.pmax_stc}Wp)"
    
    @property
    def fill_factor(self):
        """Calculate fill factor at STC"""
        if self.voc_stc and self.isc_stc and self.vmp_stc and self.imp_stc:
            return (self.vmp_stc * self.imp_stc) / (self.voc_stc * self.isc_stc)
        return None
    
    @property
    def estimated_degradation_year1(self):
        """Estimate first year degradation from warranty"""
        return (100 - self.warranty_year_1) if self.warranty_year_1 else 2.5
    
    @property
    def estimated_annual_degradation(self):
        """Estimate annual degradation rate from warranty"""
        if self.linear_degradation_rate:
            return self.linear_degradation_rate
        if self.warranty_year_1 and self.warranty_year_25:
            return (self.warranty_year_1 - self.warranty_year_25) / 24
        return 0.5


class PowerModelRegistry(models.Model):
    """Registry of power calculation models (SDM, ML, etc.)"""
    id = models.AutoField(primary_key=True)
    model_code = models.CharField(max_length=50, unique=True)
    model_name = models.CharField(max_length=100)
    model_version = models.CharField(max_length=20)
    model_type = models.CharField(max_length=50)
    is_active = models.BooleanField(default=True)
    is_default = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'power_model_registry'
        ordering = ['-is_default', 'model_name']
    
    def __str__(self):
        return f"{self.model_name} v{self.model_version}"


class StringPowerCalculation(models.Model):
    """String-level power calculation results"""
    id = models.BigAutoField(primary_key=True)
    device_id = models.CharField(max_length=120)
    asset_code = models.CharField(max_length=255)
    timestamp = models.DateTimeField()
    string_current = models.FloatField()
    string_voltage = models.FloatField()
    actual_power = models.FloatField()
    expected_power = models.FloatField()
    irradiance = models.FloatField(null=True, blank=True)
    module_temp = models.FloatField(null=True, blank=True)
    ambient_temp = models.FloatField(null=True, blank=True)
    power_loss = models.FloatField()
    loss_percentage = models.FloatField()
    calculation_status = models.CharField(max_length=20, default='success')
    task_id = models.CharField(max_length=255, null=True, blank=True)
    calculation_time = models.FloatField()
    power_model = models.ForeignKey(PowerModelRegistry, on_delete=models.SET_NULL, null=True, blank=True, db_column='power_model_id')
    power_model_version = models.CharField(max_length=20, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'string_power_calculation'
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['device_id', 'timestamp']),
            models.Index(fields=['asset_code', 'timestamp']),
        ]


class JBPowerCalculation(models.Model):
    """JB-level aggregated power calculations"""
    id = models.BigAutoField(primary_key=True)
    device_id = models.CharField(max_length=120)
    asset_code = models.CharField(max_length=255)
    timestamp = models.DateTimeField()
    total_actual_power = models.FloatField()
    total_expected_power = models.FloatField()
    string_count = models.IntegerField()
    string_device_ids = models.TextField()
    total_power_loss = models.FloatField()
    loss_percentage = models.FloatField()
    calculation_status = models.CharField(max_length=20, default='success')
    task_id = models.CharField(max_length=255, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'jb_power_calculation'
        ordering = ['-timestamp']
        indexes = [models.Index(fields=['device_id', 'timestamp']), models.Index(fields=['asset_code', 'timestamp'])]


class InverterPowerCalculation(models.Model):
    """Inverter-level aggregated power calculations"""
    id = models.BigAutoField(primary_key=True)
    device_id = models.CharField(max_length=120)
    asset_code = models.CharField(max_length=255)
    timestamp = models.DateTimeField()
    total_actual_power = models.FloatField()
    total_expected_power = models.FloatField()
    source_device_count = models.IntegerField()
    source_device_ids = models.TextField()
    total_power_loss = models.FloatField()
    loss_percentage = models.FloatField()
    calculation_status = models.CharField(max_length=20, default='success')
    task_id = models.CharField(max_length=255, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'inverter_power_calculation'
        ordering = ['-timestamp']
        indexes = [models.Index(fields=['device_id', 'timestamp']), models.Index(fields=['asset_code', 'timestamp'])]


class LossCalculationTask(models.Model):
    """Track Celery task execution"""
    id = models.BigAutoField(primary_key=True)
    task_id = models.CharField(max_length=255, unique=True)
    task_type = models.CharField(max_length=50, default='full_site')
    asset_code = models.CharField(max_length=255, null=True, blank=True)
    start_time = models.DateTimeField()
    end_time = models.DateTimeField()
    status = models.CharField(max_length=20, default='pending')
    total_devices = models.IntegerField(default=0)
    processed_devices = models.IntegerField(default=0)
    failed_devices = models.IntegerField(default=0)
    strings_calculated = models.IntegerField(default=0)
    jbs_calculated = models.IntegerField(default=0)
    inverters_calculated = models.IntegerField(default=0)
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    execution_time = models.FloatField(null=True, blank=True)
    error_message = models.TextField(null=True, blank=True)
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='loss_calc_tasks')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'loss_calculation_task'
        ordering = ['-created_at']
        indexes = [models.Index(fields=['task_id']), models.Index(fields=['status', 'created_at'])]
    
    def __str__(self):
        return f"Task {self.task_id}: {self.status}"


def log_loss_task_enqueued(
    task_id: str,
    task_name: str,
    asset_code: str | None = None,
    user: User | None = None,
    total_devices: int | None = None,
) -> LossCalculationTask:
    """
    Create or update a LossCalculationTask row when a Celery task is enqueued.

    - Sets status to 'pending'
    - start_time/end_time are initialized to now (non-nullable columns)
    - Does not mark started_at/completed_at yet
    """
    now = timezone.now()
    defaults = {
        "task_type": (task_name or "")[:50],
        "asset_code": asset_code,
        "status": "pending",
        "start_time": now,
        "end_time": now,
        "started_at": None,
        "completed_at": None,
        "execution_time": None,
        "error_message": None,
    }
    if total_devices is not None:
        defaults["total_devices"] = total_devices
    if user is not None:
        defaults["user"] = user
    obj, _created = LossCalculationTask.objects.update_or_create(
        task_id=task_id,
        defaults=defaults,
    )
    return obj


def log_loss_task_started(task_id: str) -> LossCalculationTask:
    """
    Mark a LossCalculationTask as running when the Celery task begins execution.
    """
    now = timezone.now()
    obj, created = LossCalculationTask.objects.get_or_create(
        task_id=task_id,
        defaults={
            "task_type": "",
            "status": "running",
            "start_time": now,
            "end_time": now,
            "started_at": now,
        },
    )
    if not created:
        obj.status = "running"
        obj.started_at = now
        obj.start_time = now
        obj.save(update_fields=["status", "started_at", "start_time", "updated_at"])
    return obj


def log_loss_task_completed(
    task_id: str,
    success: bool,
    error_message: str | None = None,
    processed_devices: int | None = None,
    failed_devices: int | None = None,
) -> LossCalculationTask:
    """
    Mark a LossCalculationTask as completed (success or failure).
    """
    now = timezone.now()
    obj, created = LossCalculationTask.objects.get_or_create(
        task_id=task_id,
        defaults={
            "task_type": "",
            "status": "success" if success else "failure",
            "start_time": now,
            "end_time": now,
        },
    )
    obj.status = "success" if success else "failure"
    obj.completed_at = now
    obj.end_time = now
    if obj.started_at:
        obj.execution_time = (now - obj.started_at).total_seconds()
    if error_message:
        # Append to existing error_message if present
        if obj.error_message:
            obj.error_message = f"{obj.error_message}\n{error_message}"
        else:
            obj.error_message = error_message
    if processed_devices is not None:
        obj.processed_devices = processed_devices
    if failed_devices is not None:
        obj.failed_devices = failed_devices
    obj.save()
    return obj


class PowerModelParametersHistory(models.Model):
    """
    Generic storage for power model parameters (SDM, ML, etc.)
    
    This table stores parameters for any power calculation model in a flexible way:
    - Datasheet-based parameters: Linked to module_datasheet_id (panel-specific)
    - Device-based parameters: Linked to device_id (ML-learned, device-specific)
    - Parameters stored as JSON for flexibility across different models
    
    This enables:
    - ML algorithms to learn optimal parameters
    - Using historical parameters for past date calculations
    - Tracking parameter changes over time (degradation, soiling effects)
    - Supporting multiple model types with different parameter sets
    """
    id = models.BigAutoField(primary_key=True)
    
    # Model identification
    model_code = models.CharField(max_length=50, db_index=True, help_text='Power model code (e.g., sdm_array_v1, ml_lstm_v1)')
    model_version = models.CharField(max_length=20, null=True, blank=True, help_text='Model version')
    
    # Parameter scope: datasheet-based or device-based
    parameter_type = models.CharField(
        max_length=20,
        choices=[
            ('datasheet', 'Datasheet-based (panel parameters)'),
            ('device', 'Device-based (ML-learned, device-specific)'),
            ('hybrid', 'Hybrid (combination of datasheet and device)'),
        ],
        default='datasheet',
        db_index=True,
        help_text='Type of parameters: datasheet-based or device-specific'
    )
    
    # Links to datasheet and/or device
    module_datasheet_id = models.IntegerField(
        null=True, 
        blank=True, 
        db_index=True,
        help_text='PVModuleDatasheet ID (for datasheet-based parameters)'
    )
    device_id = models.CharField(
        max_length=120, 
        null=True, 
        blank=True,
        db_index=True, 
        help_text='Device ID (for device-specific ML parameters)'
    )
    asset_code = models.CharField(
        max_length=255, 
        null=True,
        blank=True,
        db_index=True, 
        help_text='Asset/Site code (for reference)'
    )
    
    # Parameters stored as JSON (flexible for any model)
    parameters = models.JSONField(help_text='Model parameters in JSON format. Structure varies by model.')
    
    # Timestamp and timezone
    calculated_at = models.DateTimeField(db_index=True, help_text='When parameters were calculated (UTC)')
    timezone = models.CharField(
        max_length=10,
        validators=[
            RegexValidator(
                regex=r'^[+-](0[0-9]|1[0-2]):[0-5][0-9]$',
                message='Timezone must be in format "+05:30" or "-08:00"',
                code='invalid_timezone'
            )
        ],
        help_text="Site timezone offset in format '+05:30' or '-08:00'"
    )
    
    # Quality and training metadata
    fit_quality = models.FloatField(null=True, blank=True, help_text='Quality metric of the fit (lower is better)')
    fit_method = models.CharField(
        max_length=50,
        null=True,
        blank=True,
        help_text='Method used to fit parameters (e.g., least_squares, ml_training, manual)'
    )
    training_data_count = models.IntegerField(null=True, blank=True, help_text='Number of data points used for fitting/training')
    
    # Context data (for ML training and analysis)
    context_data = models.JSONField(
        null=True, 
        blank=True, 
        help_text='Context data when parameters were calculated (e.g., weather conditions, array config, irradiance_avg, temperature_avg)'
    )
    
    # Additional metadata
    metadata = models.JSONField(
        null=True, 
        blank=True, 
        help_text='Additional metadata (e.g., calculation settings, model config, notes)'
    )
    
    # Status
    is_active = models.BooleanField(default=True, db_index=True, help_text='Whether these parameters are currently active/used')
    is_validated = models.BooleanField(default=False, help_text='Whether parameters have been validated')
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'power_model_parameters_history'
        ordering = ['-calculated_at']
        indexes = [
            models.Index(fields=['model_code', 'parameter_type', '-calculated_at']),
            models.Index(fields=['module_datasheet_id', '-calculated_at']),
            models.Index(fields=['device_id', '-calculated_at']),
            models.Index(fields=['asset_code', '-calculated_at']),
            models.Index(fields=['device_id', 'model_code', '-calculated_at']),
            models.Index(fields=['module_datasheet_id', 'model_code', '-calculated_at']),
            models.Index(fields=['calculated_at']),
            models.Index(fields=['is_active', '-calculated_at']),
        ]
        # Allow multiple entries per device/datasheet (historical tracking)
        # No unique constraint - we want historical data
    
    def __str__(self):
        scope = f"datasheet:{self.module_datasheet_id}" if self.module_datasheet_id else f"device:{self.device_id}"
        return f"{self.model_code} - {scope} @ {self.calculated_at}"
    
    @property
    def parameters_dict(self) -> dict:
        """Return parameters as dictionary (alias for parameters field)"""
        return self.parameters if isinstance(self.parameters, dict) else {}
    
    def get_parameter(self, key: str, default=None):
        """Get a specific parameter value"""
        if isinstance(self.parameters, dict):
            return self.parameters.get(key, default)
        return default
    
    def set_parameter(self, key: str, value):
        """Set a specific parameter value"""
        if not isinstance(self.parameters, dict):
            self.parameters = {}
        self.parameters[key] = value


# ----------------------------------------------------------------------
# Spare Management Models
# ----------------------------------------------------------------------


class SpareMaster(models.Model):
    """Master catalog of spare parts (global, not site-specific)."""

    spare_id = models.AutoField(primary_key=True, db_column="Spare_ID")
    spare_code = models.CharField(
        max_length=50,
        unique=True,
        db_column="Spare_Code",
        help_text="Unique code for spare part",
    )
    spare_name = models.CharField(
        max_length=255, db_column="Spare_Name", help_text="Name of the spare part"
    )
    description = models.TextField(
        blank=True,
        null=True,
        db_column="Description",
        help_text="Detailed description",
    )
    category = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        db_column="Category",
        help_text="Category classification",
    )
    unit = models.CharField(
        max_length=20, db_column="Unit", help_text="Unit of measurement (e.g. Pcs)"
    )
    min_stock = models.IntegerField(
        blank=True,
        null=True,
        db_column="Min_Stock",
        help_text="Minimum stock level (global/default)",
    )
    max_stock = models.IntegerField(
        blank=True,
        null=True,
        db_column="Max_Stock",
        help_text="Maximum stock level (global/default)",
    )
    is_critical = models.BooleanField(
        default=False,
        db_column="Is_Critical",
        help_text="Is critical spare (Yes/No)",
    )

    class Meta:
        db_table = "Spare_Master"
        ordering = ["spare_name"]

    def __str__(self):
        return f"{self.spare_code} - {self.spare_name}"


class LocationMaster(models.Model):
    """Warehouse / store / location where spare stock is kept."""

    location_id = models.AutoField(primary_key=True, db_column="Location_ID")
    location_code = models.CharField(
        max_length=50,
        unique=True,
        db_column="Location_Code",
        help_text="Unique code for location (e.g. WH-01)",
    )
    location_name = models.CharField(
        max_length=255,
        db_column="Location_Name",
        help_text="Name of the location (e.g. Main Warehouse)",
    )
    location_type = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        db_column="Location_Type",
        help_text="Type of location (Warehouse, Site Store, Van, etc.)",
    )

    class Meta:
        db_table = "Location_Master"
        ordering = ["location_code"]

    def __str__(self):
        return f"{self.location_code} - {self.location_name}"


class SpareSiteMap(models.Model):
    """
    Map spares to sites and warehouses.

    This allows:
    - Multiple sites to share a warehouse.
    - One spare to be valid for multiple sites and locations.
    """

    map_id = models.AutoField(primary_key=True, db_column="Map_ID")
    spare = models.ForeignKey(
        SpareMaster,
        on_delete=models.CASCADE,
        db_column="Spare_ID",
        related_name="site_mappings",
        help_text="Reference to Spare Master",
    )
    asset = models.ForeignKey(
        AssetList,
        on_delete=models.CASCADE,
        to_field="asset_code",
        db_column="Asset_Code",
        related_name="spare_mappings",
        help_text="Reference to Site (asset_list.asset_code)",
    )
    location = models.ForeignKey(
        LocationMaster,
        on_delete=models.CASCADE,
        db_column="Location_ID",
        related_name="spare_mappings",
        help_text="Reference to issuing warehouse/location",
    )
    is_active = models.BooleanField(
        default=True,
        db_column="Is_Active",
        help_text="Active status (Yes/No)",
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        db_column="Created_At",
        help_text="Creation timestamp",
    )

    class Meta:
        db_table = "Spare_Site_Map"
        unique_together = ("spare", "asset", "location")
        ordering = ["asset__asset_code", "spare__spare_code"]

    def __str__(self):
        return f"{self.asset.asset_code} / {self.location.location_code} / {self.spare.spare_code}"


class StockBalance(models.Model):
    """Current stock quantity per spare per location."""

    stock_balance_id = models.AutoField(primary_key=True, db_column="Stock_Balance_ID")
    spare = models.ForeignKey(
        SpareMaster,
        on_delete=models.CASCADE,
        db_column="Spare_ID",
        related_name="stock_balances",
        help_text="Reference to Spare Master",
    )
    spare_code = models.CharField(
        max_length=50,
        db_column="Spare_Code",
        help_text="Spare code for reference (denormalized)",
    )
    location = models.ForeignKey(
        LocationMaster,
        on_delete=models.CASCADE,
        db_column="Location_ID",
        related_name="stock_balances",
        help_text="Reference to Location Master",
    )
    location_code = models.CharField(
        max_length=50,
        db_column="Location_Code",
        help_text="Location code for reference (denormalized)",
    )
    quantity = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        db_column="Quantity",
        help_text="Current stock quantity",
    )
    unit = models.CharField(
        max_length=20,
        db_column="Unit",
        help_text="Unit of measurement",
    )
    last_updated = models.DateTimeField(
        auto_now=True,
        db_column="Last_Updated",
        help_text="Last update timestamp",
    )

    class Meta:
        db_table = "Stock_Balance"
        unique_together = ("spare", "location")
        ordering = ["spare_code", "location_code"]

    def __str__(self):
        return f"{self.spare_code} @ {self.location_code}: {self.quantity} {self.unit}"


class StockEntry(models.Model):
    """Stock entry (IN) transactions."""

    entry_id = models.AutoField(primary_key=True, db_column="Entry_ID")
    spare = models.ForeignKey(
        SpareMaster,
        on_delete=models.CASCADE,
        db_column="Spare_ID",
        related_name="stock_entries",
        help_text="Reference to Spare Master",
    )
    spare_code = models.CharField(
        max_length=50,
        db_column="Spare_Code",
        help_text="Spare code",
    )
    location = models.ForeignKey(
        LocationMaster,
        on_delete=models.CASCADE,
        db_column="Location_ID",
        related_name="stock_entries",
        help_text="Reference to Location Master",
    )
    location_code = models.CharField(
        max_length=50,
        db_column="Location_Code",
        help_text="Location code",
    )
    quantity = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        db_column="Quantity",
        help_text="Entry quantity",
    )
    entry_type = models.CharField(
        max_length=50,
        db_column="Entry_Type",
        help_text="Type: Purchase/Repair Return/Initial Stock/Transfer In",
    )
    reference_number = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        db_column="Reference_Number",
        help_text="PO number / invoice number / reference",
    )
    remarks = models.TextField(
        blank=True,
        null=True,
        db_column="Remarks",
        help_text="Additional notes",
    )
    entry_date = models.DateTimeField(
        default=timezone.now,
        db_column="Entry_Date",
        help_text="Entry timestamp",
    )
    performed_by = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        db_column="performed_by_user_id",
        related_name="spare_stock_entries",
        help_text="User who performed entry",
    )

    class Meta:
        db_table = "Stock_Entry"
        ordering = ["-entry_date"]

    def __str__(self):
        return f"IN {self.spare_code} {self.quantity} {self.unit_display} @ {self.location_code}"

    @property
    def unit_display(self) -> str:
        return getattr(self.spare, "unit", "")


class StockIssue(models.Model):
    """Stock issue (OUT) transactions."""

    issue_id = models.AutoField(primary_key=True, db_column="Issue_ID")
    spare = models.ForeignKey(
        SpareMaster,
        on_delete=models.CASCADE,
        db_column="Spare_ID",
        related_name="stock_issues",
        help_text="Reference to Spare Master",
    )
    spare_code = models.CharField(
        max_length=50,
        db_column="Spare_Code",
        help_text="Spare code",
    )
    location = models.ForeignKey(
        LocationMaster,
        on_delete=models.CASCADE,
        db_column="Location_ID",
        related_name="stock_issues",
        help_text="Reference to Location Master",
    )
    location_code = models.CharField(
        max_length=50,
        db_column="Location_Code",
        help_text="Location code",
    )
    quantity = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        db_column="Quantity",
        help_text="Issue quantity",
    )
    issue_type = models.CharField(
        max_length=50,
        db_column="Issue_Type",
        help_text="Type: Breakdown/Preventive/Other",
    )
    ticket = models.ForeignKey(
        "ticketing.Ticket",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        db_column="ticket_id",
        related_name="spare_issues",
        help_text="Linked ticket (optional)",
    )
    issued_to = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        db_column="Issued_To",
        help_text="Who/where issued to (free text)",
    )
    remarks = models.TextField(
        blank=True,
        null=True,
        db_column="Remarks",
        help_text="Additional notes",
    )
    issue_date = models.DateTimeField(
        default=timezone.now,
        db_column="Issue_Date",
        help_text="Issue timestamp",
    )
    performed_by = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        db_column="performed_by_user_id",
        related_name="spare_stock_issues",
        help_text="User who performed issue",
    )

    class Meta:
        db_table = "Stock_Issue"
        ordering = ["-issue_date"]

    def __str__(self):
        return f"OUT {self.spare_code} {self.quantity} {self.unit_display} @ {self.location_code}"

    @property
    def unit_display(self) -> str:
        return getattr(self.spare, "unit", "")


class StockLedger(models.Model):
    """Consolidated stock ledger for all movements."""

    ledger_id = models.AutoField(primary_key=True, db_column="Ledger_ID")
    timestamp = models.DateTimeField(
        default=timezone.now,
        db_column="DateTime",
        help_text="Transaction timestamp",
    )
    spare = models.ForeignKey(
        SpareMaster,
        on_delete=models.CASCADE,
        db_column="Spare_ID",
        related_name="stock_ledger_entries",
        help_text="Reference to Spare Master",
    )
    spare_code = models.CharField(
        max_length=50,
        db_column="Spare_Code",
        help_text="Spare code",
    )
    location_code = models.CharField(
        max_length=50,
        db_column="Location_Code",
        help_text="Location code",
    )
    transaction_type = models.CharField(
        max_length=30,
        db_column="Transaction_Type",
        help_text="Type: IN/OUT/ADJUSTMENT/TRANSFER_IN/TRANSFER_OUT",
    )
    quantity = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        db_column="Quantity",
        help_text="Transaction quantity",
    )
    balance_after = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        db_column="Balance_After",
        help_text="Stock balance after transaction",
    )
    reference = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        db_column="Reference",
        help_text="Reference number (PO, Issue ID, etc.)",
    )
    remarks = models.TextField(
        blank=True,
        null=True,
        db_column="Remarks",
        help_text="Additional notes",
    )
    performed_by = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        db_column="performed_by_user_id",
        related_name="spare_stock_ledger_entries",
        help_text="User who performed transaction",
    )

    class Meta:
        db_table = "Stock_Ledger"
        ordering = ["-timestamp"]
        indexes = [
            models.Index(fields=["spare_code", "timestamp"]),
            models.Index(fields=["location_code", "timestamp"]),
            models.Index(fields=["transaction_type", "timestamp"]),
        ]

    def __str__(self):
        return f"{self.timestamp} {self.transaction_type} {self.spare_code} {self.quantity}"


class InventoryAuditLog(models.Model):
    """Audit log for spare/inventory actions (DB-level view, separate from app UserActivityLog)."""

    audit_id = models.AutoField(primary_key=True, db_column="Audit_ID")
    timestamp = models.DateTimeField(
        default=timezone.now,
        db_column="Timestamp",
        help_text="Action timestamp",
    )
    user = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        db_column="user_id",
        help_text="User who performed the action",
    )
    user_name = models.CharField(
        max_length=255,
        db_column="User_Name",
        help_text="User name (denormalized)",
    )
    action = models.CharField(
        max_length=20,
        db_column="Action",
        help_text="Action: CREATE/UPDATE/DELETE/VIEW",
    )
    entity_type = models.CharField(
        max_length=100,
        db_column="Entity_Type",
        help_text="Type of entity (StockEntry, StockIssue, StockBalance, etc.)",
    )
    entity_id = models.IntegerField(
        db_column="Entity_ID",
        help_text="ID of the entity",
    )
    entity_name = models.CharField(
        max_length=255,
        db_column="Entity_Name",
        help_text="Name/description of the entity",
    )
    ip_address = models.GenericIPAddressField(
        blank=True,
        null=True,
        db_column="IP_Address",
        help_text="IP address of the user",
    )
    changes = models.JSONField(
        blank=True,
        null=True,
        db_column="Changes",
        help_text="JSON string / object of changes made",
    )

    class Meta:
        db_table = "Audit_Log"
        ordering = ["-timestamp"]
        indexes = [
            models.Index(fields=["user", "timestamp"]),
            models.Index(fields=["entity_type", "entity_id"]),
            models.Index(fields=["action", "timestamp"]),
        ]

    def __str__(self):
        return f"{self.timestamp} {self.user_name} {self.action} {self.entity_type}#{self.entity_id}"