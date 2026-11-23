from django import forms
from .models import MortgageApplication, MortgageProduct


class MortgageProductForm(forms.ModelForm):
    class Meta:
        model = MortgageProduct
        fields = [
            "name",
            "description",
            "annual_interest_rate",
            "minimum_amount",
            "maximum_amount",
            "maximum_term_years",
            "is_active",
        ]
        widgets = {
            "name": forms.TextInput(attrs={"class": "form-control", "placeholder": "e.g. 5-Year Fixed Residential"}),
            "description": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
            "annual_interest_rate": forms.NumberInput(attrs={"class": "form-control", "step": "0.01"}),
            "minimum_amount": forms.NumberInput(attrs={"class": "form-control", "step": "1000"}),
            "maximum_amount": forms.NumberInput(attrs={"class": "form-control", "step": "1000"}),
            "maximum_term_years": forms.NumberInput(attrs={"class": "form-control", "min": "1", "max": "50"}),
            "is_active": forms.CheckboxInput(attrs={"class": "form-check-input"}),
        }


class MortgageApplicationForm(forms.ModelForm):
    product = forms.ModelChoiceField(
        queryset=MortgageProduct.objects.none(),
        widget=forms.Select(attrs={"class": "form-select"})
    )

    class Meta:
        model = MortgageApplication
        fields = [
            "product",
            "requested_amount",
            "term_years",
            "applicant_notes",
        ]
        widgets = {
            "requested_amount": forms.NumberInput(attrs={"class": "form-control", "step": "0.01", "placeholder": "e.g. 250000"}),
            "term_years": forms.NumberInput(attrs={"class": "form-control", "min": "1", "max": "50", "placeholder": "e.g. 25"}),
            "applicant_notes": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 4,
                    "placeholder": "Provide any relevant employment, property, or collateral information."
                }
            )
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["product"].queryset = (
            MortgageProduct.objects.filter(is_active=True)
        )

    def clean(self):
        cleaned_data = super().clean()
        product = cleaned_data.get("product")
        requested_amount = cleaned_data.get("requested_amount")
        term_years = cleaned_data.get("term_years")

        if product and requested_amount:
            if requested_amount < product.minimum_amount:
                self.add_error(
                    "requested_amount",
                    f"Minimum loan amount for {product.name} is £{product.minimum_amount:,.2f}."
                )
            if requested_amount > product.maximum_amount:
                self.add_error(
                    "requested_amount",
                    f"Maximum loan amount for {product.name} is £{product.maximum_amount:,.2f}."
                )

        if product and term_years:
            if term_years > product.maximum_term_years:
                self.add_error(
                    "term_years",
                    f"Maximum allowed term for {product.name} is {product.maximum_term_years} years."
                )

        return cleaned_data
