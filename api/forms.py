"""
API Management Forms
--------------------
Forms for web-based API configuration
"""

from django import forms
from django.contrib.auth.models import User
from .models import APIUser, TablePermission, ColumnRestriction


# CreateAPIUserForm removed - user creation now handled in User Management page


class SetupAPIPermissionsForm(forms.Form):
    """Form to setup API permissions for a user"""
    user = forms.ModelChoiceField(
        queryset=User.objects.all(),
        help_text='Select user to grant API access'
    )
    name = forms.CharField(
        max_length=200,
        initial='API Access',
        help_text='Name for this API user configuration'
    )
    description = forms.CharField(
        widget=forms.Textarea(attrs={'rows': 3}),
        required=False,
        help_text='Optional description'
    )
    
    # Rate limiting
    rate_limit_per_minute = forms.IntegerField(
        initial=60,
        min_value=1,
        max_value=1000,
        help_text='Maximum requests per minute'
    )
    rate_limit_per_hour = forms.IntegerField(
        initial=1000,
        min_value=1,
        max_value=100000,
        help_text='Maximum requests per hour'
    )
    rate_limit_per_day = forms.IntegerField(
        initial=10000,
        min_value=1,
        max_value=1000000,
        help_text='Maximum requests per day'
    )
    
    # IP restrictions
    allowed_ips = forms.CharField(
        required=False,
        help_text='Comma-separated IP addresses (leave empty for no restriction)',
        widget=forms.Textarea(attrs={'rows': 2, 'placeholder': '203.0.113.0, 198.51.100.0'})
    )
    
    # Table selection
    ALL_TABLES = [
        ('AssetList', 'AssetList - Asset/site information'),
        ('kpis', 'kpis - KPI metrics'),
        ('device_list', 'device_list - Device inventory'),
        ('device_mapping', 'device_mapping - Device configuration'),
        ('budget_values', 'budget_values - Budget data'),
        ('ic_budget', 'ic_budget - IC budget'),
        ('timeseries_data', 'timeseries_data - Time series metrics'),
        ('YieldData', 'YieldData - Yield information'),
        ('BESSData', 'BESSData - Battery storage data'),
        ('AOCData', 'AOCData - AOC data'),
        ('ICEData', 'ICEData - ICE data'),
        ('ICVSEXVSCURData', 'ICVSEXVSCURData - Comparison data'),
        ('MapData', 'MapData - Geographic data'),
        ('MinamataStringLossData', 'MinamataStringLossData - String loss data'),
        ('ActualGenerationDailyData', 'ActualGenerationDailyData - Daily generation'),
        ('ExpectedBudgetDailyData', 'ExpectedBudgetDailyData - Daily budget'),
        ('BudgetGIIDailyData', 'BudgetGIIDailyData - Daily GII budget'),
        ('ActualGIIDailyData', 'ActualGIIDailyData - Daily actual GII'),
        ('ICApprovedBudgetDailyData', 'ICApprovedBudgetDailyData - IC approved budget'),
        ('LossCalculationData', 'LossCalculationData - Loss calculations'),
        ('RealTimeKPI', 'RealTimeKPI - Real-time KPIs'),
    ]
    
    tables = forms.MultipleChoiceField(
        choices=ALL_TABLES,
        widget=forms.CheckboxSelectMultiple,
        help_text='Select tables to grant access to',
        required=False
    )
    
    grant_all_tables = forms.BooleanField(
        required=False,
        help_text='Grant access to all tables'
    )
    
    # Table permissions
    can_filter = forms.BooleanField(
        initial=True,
        required=False,
        help_text='Allow filtering records'
    )
    can_aggregate = forms.BooleanField(
        initial=True,
        required=False,
        help_text='Allow aggregations (count, sum, avg, etc.)'
    )
    max_records_per_request = forms.IntegerField(
        initial=1000,
        min_value=1,
        max_value=10000,
        help_text='Maximum records per API request'
    )


class GrantTableAccessForm(forms.Form):
    """Form to grant table access to existing API user"""
    api_user = forms.ModelChoiceField(
        queryset=None,  # Set in __init__
        help_text='Select API user'
    )
    
    tables = forms.MultipleChoiceField(
        choices=SetupAPIPermissionsForm.ALL_TABLES,
        widget=forms.CheckboxSelectMultiple,
        help_text='Select additional tables to grant access to'
    )
    
    can_filter = forms.BooleanField(
        initial=True,
        required=False,
        help_text='Allow filtering records'
    )
    can_aggregate = forms.BooleanField(
        initial=True,
        required=False,
        help_text='Allow aggregations'
    )
    max_records_per_request = forms.IntegerField(
        initial=1000,
        min_value=1,
        max_value=10000
    )
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['api_user'].queryset = APIUser.objects.filter(status='active')


class RestrictColumnForm(forms.Form):
    """Form to restrict columns for a table"""
    api_user = forms.ModelChoiceField(
        queryset=None,  # Set in __init__
        help_text='Select API user'
    )
    
    table = forms.ChoiceField(
        choices=[],  # Set dynamically
        help_text='Select table'
    )
    
    columns = forms.MultipleChoiceField(
        choices=[],  # Set dynamically
        widget=forms.CheckboxSelectMultiple,
        help_text='Select columns to restrict',
        required=False
    )
    
    restriction_type = forms.ChoiceField(
        choices=[
            ('hidden', 'Hidden - Completely exclude from API responses'),
            ('masked', 'Masked - Return as NULL in API responses')
        ],
        initial='hidden',
        widget=forms.RadioSelect
    )
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['api_user'].queryset = APIUser.objects.filter(status='active')
        
        # Get tables for dropdown
        tables = TablePermission.objects.values_list('table_name', 'table_name').distinct()
        self.fields['table'].choices = list(tables)


class GenerateAPIKeyForm(forms.Form):
    """Form to generate API key for a user"""
    user = forms.ModelChoiceField(
        queryset=User.objects.all(),
        help_text='Select user to generate API key for'
    )
    
    name = forms.CharField(
        max_length=200,
        initial='API Key',
        help_text='Descriptive name for this key'
    )
    
    expires_in_days = forms.IntegerField(
        required=False,
        min_value=1,
        max_value=3650,
        help_text='Days until expiration (leave empty for no expiration)'
    )


class RevokeAPIKeyForm(forms.Form):
    """Form to revoke an API key"""
    api_key = forms.ModelChoiceField(
        queryset=None,  # Set in __init__
        help_text='Select API key to revoke'
    )
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        from .models import APIKey
        self.fields['api_key'].queryset = APIKey.objects.filter(status='active')


class APIUserUpdateForm(forms.Form):
    """Form to update an existing API user"""
    access_level = forms.ChoiceField(
        choices=APIUser.ACCESS_LEVEL_CHOICES,
        help_text='Type of access to grant to this user'
    )
    status = forms.ChoiceField(
        choices=APIUser.STATUS_CHOICES,
        help_text='Current status of the API user'
    )
    rate_limit_per_minute = forms.IntegerField(
        min_value=1,
        max_value=1000,
        help_text='Maximum requests per minute'
    )
    rate_limit_per_hour = forms.IntegerField(
        min_value=1,
        max_value=10000,
        help_text='Maximum requests per hour'
    )
    rate_limit_per_day = forms.IntegerField(
        min_value=1,
        max_value=100000,
        help_text='Maximum requests per day'
    )
    allowed_ips = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={'rows': 3}),
        help_text='Comma-separated list of allowed IP addresses (leave empty for no restriction)'
    )


class UpdateRateLimitsForm(forms.Form):
    """Form to update rate limits for an API user"""
    api_user = forms.ModelChoiceField(
        queryset=None,
        help_text='Select API user'
    )
    
    rate_limit_per_minute = forms.IntegerField(
        min_value=1,
        max_value=1000
    )
    rate_limit_per_hour = forms.IntegerField(
        min_value=1,
        max_value=100000
    )
    rate_limit_per_day = forms.IntegerField(
        min_value=1,
        max_value=1000000
    )
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['api_user'].queryset = APIUser.objects.filter(status='active')

