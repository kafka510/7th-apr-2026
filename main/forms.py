from django import forms
from .models import Feedback, FeedbackImage


class FeedbackForm(forms.ModelForm):
    images = forms.FileField(
        widget=forms.FileInput(attrs={
            'class': 'form-control',
            'accept': 'image/*'
        }),
        required=False,
        label='Upload Images (Optional)',
        help_text='You can select multiple images or paste them from clipboard'
    )
    
    class Meta:
        model = Feedback
        fields = ['subject', 'message']
        widgets = {
            'subject': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter feedback subject'
            }),
            'message': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 5,
                'placeholder': 'Enter your feedback message'
            })
        }
        labels = {
            'subject': 'Subject',
            'message': 'Feedback Message'
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['images'].widget.attrs.update({
            'id': 'id_images',
            'onchange': 'handleMultipleImages(this)'
        })
