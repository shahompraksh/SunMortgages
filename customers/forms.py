from django import forms
from .models import CustomerProfile


class CustomerProfileForm(forms.ModelForm):
    class Meta:
        model = CustomerProfile
        fields = [
            "address",
            "company_name",
        ]
        widgets = {
            "address": forms.Textarea(attrs={
                "rows": 3,
                "placeholder": "Enter customer address"
            }),
            "company_name": forms.TextInput(attrs={
                "placeholder": "Enter company name"
            }),
        }
