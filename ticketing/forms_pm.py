"""
Forms for Preventive Maintenance Rule Management
"""
from django import forms
from main.permissions import get_role_choices_for_capability
from .models import PreventiveMaintenanceRule, TicketCategory


class PreventiveMaintenanceRuleForm(forms.ModelForm):
    """Form for creating/editing PM rules"""
    
    # Available device_list date fields
    DEVICE_DATE_FIELDS = [
        ('equipment_warranty_start_date', 'Equipment Warranty Start Date'),
        ('equipment_warranty_expire_date', 'Equipment Warranty Expire Date'),
        ('epc_warranty_start_date', 'EPC Warranty Start Date'),
        ('epc_warranty_expire_date', 'EPC Warranty Expire Date'),
        ('cod', 'COD (from Asset List)'),
    ]
    
    # Available device_list frequency fields
    DEVICE_FREQUENCY_FIELDS = [
        ('calibration_frequency', 'Calibration Frequency'),
        ('pm_frequency', 'PM Frequency'),
        ('visual_inspection_frequency', 'Visual Inspection Frequency'),
    ]
    
    rule_type = forms.ChoiceField(
        choices=PreventiveMaintenanceRule.RULE_TYPE_CHOICES,
        widget=forms.RadioSelect,
        label="Rule Type"
    )
    
    # Date-based fields
    date_field_name = forms.ChoiceField(
        choices=[('', '-- Select Field --')] + DEVICE_DATE_FIELDS,
        required=False,
        widget=forms.Select(attrs={'class': 'form-control'}),
        label="Expiry Date Field",
        help_text="Select the date field to monitor for expiry"
    )
    
    alert_days_before = forms.IntegerField(
        initial=30,
        min_value=1,
        max_value=365,
        required=False,
        widget=forms.NumberInput(attrs={'class': 'form-control'}),
        label="Alert Days Before",
        help_text="Create ticket X days before expiry date"
    )
    
    # Frequency-based fields
    start_date_field = forms.ChoiceField(
        choices=[('', '-- Select Field --')] + DEVICE_DATE_FIELDS,
        required=False,
        widget=forms.Select(attrs={'class': 'form-control'}),
        label="Start Date Field",
        help_text="Field to use as the start date for frequency calculation"
    )
    
    frequency_field = forms.ChoiceField(
        choices=[('', '-- Select Field --')] + DEVICE_FREQUENCY_FIELDS,
        required=False,
        widget=forms.Select(attrs={'class': 'form-control'}),
        label="Frequency Field",
        help_text="Field containing the maintenance frequency"
    )
    
    name = forms.CharField(
        max_length=255,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g., Equipment Warranty Check'}),
        label="Rule Name"
    )
    
    description = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        label="Description"
    )
    
    category = forms.ModelChoiceField(
        queryset=TicketCategory.objects.filter(is_active=True),
        widget=forms.Select(attrs={'class': 'form-control'}),
        label="Ticket Category",
        help_text="Category for auto-generated tickets"
    )
    
    priority = forms.ChoiceField(
        choices=[('', '-- Select Priority --')] + PreventiveMaintenanceRule._meta.get_field('priority').choices,
        widget=forms.Select(attrs={'class': 'form-control'}),
        label="Priority",
        initial='medium'
    )
    
    title_template = forms.CharField(
        max_length=255,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'PM: {rule_name} - {device_name} at {site_name}'
        }),
        label="Ticket Title Template",
        help_text="Use placeholders: {rule_name}, {device_name}, {site_name}, {date}"
    )
    
    description_template = forms.CharField(
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 4,
            'placeholder': 'This is an automated preventive maintenance ticket for {device_name}...'
        }),
        label="Ticket Description Template",
        help_text="Use same placeholders as title"
    )
    
    ASSIGNABLE_ROLE_CAPABILITY = "ticketing.assignable"
    ROLE_CHOICES = [
        ('', '-- No Auto-Assignment --'),
        *get_role_choices_for_capability(ASSIGNABLE_ROLE_CAPABILITY),
    ]
    
    assign_to_role = forms.ChoiceField(
        choices=ROLE_CHOICES,
        required=False,
        widget=forms.Select(attrs={'class': 'form-control'}),
        label="Auto-assign To Role",
        help_text="Assign to users with this role who have access to the device's site"
    )
    
    send_email_notification = forms.BooleanField(
        required=False,
        initial=True,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        label="Send Email Notification",
        help_text="Send email when PM ticket is created"
    )
    
    is_active = forms.BooleanField(
        required=False,
        initial=True,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        label="Active"
    )
    
    class Meta:
        model = PreventiveMaintenanceRule
        fields = [
            'name', 'description', 'rule_type',
            'date_field_name', 'alert_days_before',
            'start_date_field', 'frequency_field',
            'category', 'priority',
            'title_template', 'description_template',
            'assign_to_role', 'send_email_notification', 'is_active'
        ]
    
    def clean(self):
        cleaned_data = super().clean()
        rule_type = cleaned_data.get('rule_type')
        
        if rule_type == 'date_based':
            if not cleaned_data.get('date_field_name'):
                raise forms.ValidationError("Date field is required for date-based rules")
            if not cleaned_data.get('alert_days_before'):
                raise forms.ValidationError("Alert days before is required for date-based rules")
        
        elif rule_type == 'frequency_based':
            if not cleaned_data.get('start_date_field'):
                raise forms.ValidationError("Start date field is required for frequency-based rules")
            if not cleaned_data.get('frequency_field'):
                raise forms.ValidationError("Frequency field is required for frequency-based rules")
        
        return cleaned_data

