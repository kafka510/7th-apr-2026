from django import forms
from django.core.exceptions import ValidationError
from .models import Ticket, TicketCategory, TicketSubCategory, LossCategory, TicketComment, TicketAttachment
from main.models import AssetList, device_list


class TicketForm(forms.ModelForm):
    """Form for creating and editing tickets"""
    
    asset_code = forms.ModelChoiceField(
        queryset=AssetList.objects.all(),
        label="Site",
        widget=forms.Select(attrs={'class': 'form-control', 'id': 'asset-select'}),
        help_text="Select the site/asset"
    )
    
    device_type = forms.CharField(
        required=False,
        widget=forms.HiddenInput(),
        label="Device Type"
    )
    
    device_sub_group = forms.CharField(
        required=False,
        widget=forms.HiddenInput(),
        label="Device Sub Group"
    )
    
    device_id = forms.CharField(
        required=False,  # We'll validate in clean_device_id
        label="Device Name",
        widget=forms.HiddenInput(attrs={'id': 'device-id-hidden'}),
        help_text="Select the device (required)"
    )
    
    sub_device_id = forms.CharField(
        required=False,
        label="Sub Device",
        widget=forms.HiddenInput(attrs={'id': 'sub-device-id-hidden'}),
        help_text="Select sub device (optional)"
    )
    
    title = forms.CharField(
        max_length=255,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter ticket title'
        }),
        label="Title",
        help_text="Brief description of the issue"
    )
    
    description = forms.CharField(
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 5,
            'placeholder': 'Provide detailed description of the issue...'
        }),
        label="Description",
        help_text="Detailed description of the maintenance or loss issue"
    )
    
    category = forms.ModelChoiceField(
        queryset=TicketCategory.objects.filter(is_active=True),
        widget=forms.Select(attrs={'class': 'form-control'}),
        label="Category",
        help_text="Select maintenance category"
    )
    sub_category = forms.ModelChoiceField(
        queryset=TicketSubCategory.objects.filter(is_active=True),
        required=False,
        widget=forms.Select(attrs={'class': 'form-control'}),
        label="Sub-Category",
        help_text="Select sub-category (optional)"
    )
    
    loss_category = forms.ModelChoiceField(
        queryset=LossCategory.objects.filter(is_active=True),
        required=False,
        widget=forms.Select(attrs={'class': 'form-control'}),
        label="Loss Category",
        help_text="Select loss categorization (optional)"
    )
    
    loss_value = forms.DecimalField(
        required=False,
        max_digits=12,
        decimal_places=2,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'placeholder': '0.00',
            'step': '0.01',
            'min': '0'
        }),
        label="Loss Value",
        help_text="Financial loss incurred (in local currency, optional)"
    )
    
    priority = forms.ChoiceField(
        choices=Ticket.PRIORITY_CHOICES,
        widget=forms.Select(attrs={'class': 'form-control'}),
        label="Priority",
        initial='medium',
        help_text="Select priority level"
    )
    
    assigned_to = forms.ModelChoiceField(
        queryset=None,  # Will be set in __init__
        required=False,
        widget=forms.Select(attrs={'class': 'form-control'}),
        label="Assign To",
        help_text="Assign ticket to a user (optional)"
    )
    watchers = forms.ModelMultipleChoiceField(
        queryset=None,  # Will be set in __init__
        required=False,
        widget=forms.SelectMultiple(attrs={'class': 'form-control', 'size': '5'}),
        label="Watchers/Collaborators",
        help_text="Select users who can view and update this ticket (hold Ctrl/Cmd to select multiple)"
    )

    class Meta:
        model = Ticket
        fields = [
            'asset_code', 'title', 'description',
            'category', 'sub_category', 'loss_category', 'loss_value', 'priority', 'assigned_to', 'watchers'
        ]
        # Note: device_id is handled as CharField (not in fields) and converted in clean_device_id
        # sub_device_id is handled as CharField (not in fields) and stored in metadata JSON field

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        
        # Filter assets based on user access
        if self.user:
            from .utils import get_accessible_sites_for_user
            accessible_sites = get_accessible_sites_for_user(self.user)
            self.fields['asset_code'].queryset = accessible_sites
            
            # Set assigned_to and watchers queryset to all active users
            from django.contrib.auth.models import User
            users_queryset = User.objects.filter(is_active=True).order_by('username')
            self.fields['assigned_to'].queryset = users_queryset
            self.fields['watchers'].queryset = users_queryset
        
        # If editing, populate device fields
        if self.instance and self.instance.pk:
            if self.instance.device_id:
                device = self.instance.device_id
                self.fields['device_type'].initial = device.device_type
                self.fields['device_sub_group'].initial = device.device_sub_group

    def clean_device_id(self):
        device_id_value = self.cleaned_data.get('device_id')
        if not device_id_value:
            raise ValidationError('Device selection is required.')
        
        # Convert string device_id to device_list object
        try:
            device = device_list.objects.get(device_id=device_id_value)
            return device
        except device_list.DoesNotExist:
            raise ValidationError('Selected device does not exist.')

    def clean(self):
        cleaned_data = super().clean()
        asset_code = cleaned_data.get('asset_code')
        device_id = cleaned_data.get('device_id')
        
        # Validate that device belongs to selected asset
        if device_id and asset_code:
            if device_id.parent_code != asset_code.asset_code:
                raise ValidationError({
                    'device_id': 'Selected device does not belong to the selected site.'
                })
        
        return cleaned_data


class TicketCategoryForm(forms.ModelForm):
    """Form for creating and editing ticket categories"""
    
    class Meta:
        model = TicketCategory
        fields = ['name', 'description', 'display_order', 'is_active']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'display_order': forms.NumberInput(attrs={'class': 'form-control'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
        labels = {
            'name': 'Category Name',
            'description': 'Description',
            'display_order': 'Display Order',
            'is_active': 'Active',
        }
    
    def clean_name(self):
        name = self.cleaned_data.get('name')
        if name:
            # Check for duplicate names (excluding current instance if editing)
            queryset = TicketCategory.objects.filter(name=name)
            if self.instance and self.instance.pk:
                queryset = queryset.exclude(pk=self.instance.pk)
            if queryset.exists():
                raise ValidationError('A category with this name already exists.')
        return name


class LossCategoryForm(forms.ModelForm):
    """Form for creating and editing loss categories"""
    
    class Meta:
        model = LossCategory
        fields = ['name', 'description', 'display_order', 'is_active']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'display_order': forms.NumberInput(attrs={'class': 'form-control'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
        labels = {
            'name': 'Category Name',
            'description': 'Description',
            'display_order': 'Display Order',
            'is_active': 'Active',
        }
    
    def clean_name(self):
        name = self.cleaned_data.get('name')
        if name:
            # Check for duplicate names (excluding current instance if editing)
            queryset = LossCategory.objects.filter(name=name)
            if self.instance and self.instance.pk:
                queryset = queryset.exclude(pk=self.instance.pk)
            if queryset.exists():
                raise ValidationError('A category with this name already exists.')
        return name


class TicketCommentForm(forms.ModelForm):
    """Form for adding comments to tickets"""
    
    class Meta:
        model = TicketComment
        fields = ['comment', 'is_internal']
        widgets = {
            'comment': forms.Textarea(attrs={
            'class': 'form-control',
                'rows': 4,
            'placeholder': 'Enter your comment...'
        }),
            'is_internal': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
        labels = {
            'comment': 'Comment',
            'is_internal': 'Internal Note (not visible to customer)',
        }


class TicketAttachmentForm(forms.ModelForm):
    """Form for uploading ticket attachments"""

    class Meta:
        model = TicketAttachment
        fields = ['file']
        widgets = {
            'file': forms.FileInput(attrs={'class': 'form-control'}),
        }
    
    def clean_file(self):
        file = self.cleaned_data.get('file')
        if file:
            # Check file size (max 10MB)
            max_size = 10 * 1024 * 1024  # 10MB
            if file.size > max_size:
                raise ValidationError(f'File size cannot exceed 10MB. Current size: {file.size / 1024 / 1024:.2f}MB')
            
            # Check file name length
            if len(file.name) > 255:
                raise ValidationError('File name is too long. Maximum length is 255 characters.')
        return file


class TicketAssignForm(forms.Form):
    """Form for assigning tickets to users"""
    
    assigned_to = forms.ModelChoiceField(
        queryset=None,  # Will be set in __init__
        required=False,
        widget=forms.Select(attrs={'class': 'form-control'}),
        label="Assign To",
        help_text="Select user to assign this ticket"
    )
    notes = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 3,
            'placeholder': 'Optional notes about the assignment...'
        }),
        label="Notes",
        help_text="Optional notes about the assignment"
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        from django.contrib.auth.models import User
        self.fields['assigned_to'].queryset = User.objects.filter(is_active=True).order_by('username')


class TicketStatusForm(forms.Form):
    """Form for changing ticket status"""
    
    status = forms.ChoiceField(
        choices=Ticket.STATUS_CHOICES,
        widget=forms.Select(attrs={'class': 'form-control'}),
        label="Status",
        help_text="Select new status for the ticket"
    )
    notes = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 3,
            'placeholder': 'Optional notes about the status change...'
        }),
        label="Notes",
        help_text="Optional notes about the status change"
    )


class TicketFilterForm(forms.Form):
    """Form for filtering tickets"""
    
    status = forms.ChoiceField(
        choices=[('', 'All Statuses')] + list(Ticket.STATUS_CHOICES),
        required=False,
        widget=forms.Select(attrs={'class': 'form-control form-select-sm'}),
        label="Status"
    )
    priority = forms.ChoiceField(
        choices=[('', 'All Priorities')] + list(Ticket.PRIORITY_CHOICES),
        required=False,
        widget=forms.Select(attrs={'class': 'form-control form-select-sm'}),
        label="Priority"
    )
    category = forms.ModelChoiceField(
        queryset=TicketCategory.objects.filter(is_active=True),
        required=False,
        widget=forms.Select(attrs={'class': 'form-control form-select-sm'}),
        label="Category",
        empty_label="All Categories"
    )
    asset_code = forms.ModelChoiceField(
        queryset=None,  # Will be set in __init__
        required=False,
        widget=forms.Select(attrs={'class': 'form-control form-select-sm'}),
        label="Site",
        empty_label="All Sites"
    )
    assigned_to = forms.ModelChoiceField(
        queryset=None,  # Will be set in __init__
        required=False,
        widget=forms.Select(attrs={'class': 'form-control form-select-sm'}),
        label="Assigned To",
        empty_label="All Users"
    )
    search = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control form-control-sm',
            'placeholder': 'Search tickets...'
        }),
        label="Search",
        help_text="Search by title, description, or ticket number"
    )

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        from django.contrib.auth.models import User
        from main.models import AssetList
        self.fields['assigned_to'].queryset = User.objects.filter(is_active=True).order_by('username')
        self.fields['asset_code'].queryset = AssetList.objects.all().order_by('asset_name')


class TicketWatcherForm(forms.Form):
    """Form for updating ticket watchers"""

    watchers = forms.ModelMultipleChoiceField(
        queryset=None,
        required=False,
        widget=forms.SelectMultiple(attrs={'class': 'form-control', 'size': '8', 'id': 'watchers-select'}),
        label="Watchers"
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        from django.contrib.auth.models import User
        self.fields['watchers'].queryset = User.objects.filter(is_active=True).order_by('username')
