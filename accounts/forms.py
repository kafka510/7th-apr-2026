from django import forms
from django.contrib.auth.forms import AuthenticationForm

try:
    from captcha.fields import ReCaptchaField
    from captcha.widgets import ReCaptchaV2Checkbox
except ImportError:  # pragma: no cover - optional dependency
    ReCaptchaField = None  # type: ignore[assignment]
    ReCaptchaV2Checkbox = None  # type: ignore[assignment]

from .models import Capability, Feature, Role


class CaptchaAuthenticationForm(AuthenticationForm):
    """
    Custom authentication form with reCAPTCHA v2 when the dependency is available.
    """

    if ReCaptchaField and ReCaptchaV2Checkbox:
        captcha = ReCaptchaField(
            widget=ReCaptchaV2Checkbox(
                attrs={
                    "data-theme": "light",
                    "data-size": "normal",
                }
            ),
            label=False,
            error_messages={
                "required": "Please complete the reCAPTCHA verification.",
                "invalid": "reCAPTCHA verification failed. Please try again.",
            },
        )


class FeatureForm(forms.ModelForm):
    class Meta:
        model = Feature
        fields = ["key", "name", "description", "category", "is_active", "ordering"]
        widgets = {
            "name": forms.TextInput(attrs={"class": "form-control"}),
            "key": forms.TextInput(attrs={"class": "form-control", "placeholder": "e.g. unified_operations_dashboard"}),
            "description": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
            "category": forms.TextInput(attrs={"class": "form-control", "placeholder": "Optional grouping label"}),
            "ordering": forms.NumberInput(attrs={"class": "form-control"}),
            "is_active": forms.CheckboxInput(attrs={"class": "form-check-input"}),
        }

    def clean_key(self):
        key = self.cleaned_data["key"]
        if key:
            key = key.strip().lower()
        return key


class CapabilityForm(forms.ModelForm):
    class Meta:
        model = Capability
        fields = ["key", "name", "description", "category", "is_active"]
        widgets = {
            "key": forms.TextInput(attrs={"class": "form-control", "placeholder": "e.g. ticketing.assign"}),
            "name": forms.TextInput(attrs={"class": "form-control"}),
            "description": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
            "category": forms.TextInput(attrs={"class": "form-control", "placeholder": "Optional grouping label"}),
            "is_active": forms.CheckboxInput(attrs={"class": "form-check-input"}),
        }

    def clean_key(self):
        key = self.cleaned_data["key"]
        if key:
            key = key.strip().lower()
        return key


class RoleForm(forms.ModelForm):
    features = forms.ModelMultipleChoiceField(
        queryset=Feature.objects.none(),
        required=False,
        widget=forms.SelectMultiple(attrs={"class": "form-select", "size": 12}),
        help_text="Select the features/pages accessible to this role.",
    )
    capabilities = forms.ModelMultipleChoiceField(
        queryset=Capability.objects.none(),
        required=False,
        widget=forms.SelectMultiple(attrs={"class": "form-select", "size": 12}),
        help_text="Select the capabilities granted to this role.",
    )

    class Meta:
        model = Role
        fields = [
            "key",
            "name",
            "description",
            "is_active",
            "ordering",
            "features",
            "capabilities",
        ]
        widgets = {
            "key": forms.TextInput(attrs={"class": "form-control", "placeholder": "e.g. asset_manager"}),
            "name": forms.TextInput(attrs={"class": "form-control"}),
            "description": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
            "ordering": forms.NumberInput(attrs={"class": "form-control"}),
            "is_active": forms.CheckboxInput(attrs={"class": "form-check-input"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["features"].queryset = Feature.objects.order_by("ordering", "name")
        self.fields["capabilities"].queryset = Capability.objects.order_by("category", "name")
        if self.instance and self.instance.pk:
            self.fields["key"].disabled = True

    def clean_key(self):
        key = self.cleaned_data.get("key")
        if key:
            key = key.strip().lower()
        return key
