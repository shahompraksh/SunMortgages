from django import forms
from django.contrib.auth.forms import UserCreationForm
from .models import User


class RegistrationForm(UserCreationForm):
    email = forms.EmailField(required=True)
    phone_number = forms.CharField(
        max_length=20,
        required=True
    )
    role = forms.ChoiceField(
        choices=[
            (User.Role.DEVELOPER, "Property Developer"),
            (User.Role.INDIVIDUAL, "Individual Customer"),
        ]
    )

    class Meta:
        model = User
        fields = [
            "username",
            "email",
            "phone_number",
            "role",
            "password1",
            "password2",
        ]

    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data["email"]
        user.phone_number = self.cleaned_data["phone_number"]
        user.role = self.cleaned_data["role"]
        if commit:
            user.save()
        return user
