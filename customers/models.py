from django.conf import settings
from django.db import models


class CustomerProfile(models.Model):
    class CustomerType(models.TextChoices):
        INDIVIDUAL = "INDIVIDUAL", "Individual"
        DEVELOPER = "DEVELOPER", "Property Developer"

    class AccountStatus(models.TextChoices):
        ACTIVE = "ACTIVE", "Active"
        INACTIVE = "INACTIVE", "Inactive"
        SUSPENDED = "SUSPENDED", "Suspended"

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="customer_profile"
    )

    customer_type = models.CharField(
        max_length=20,
        choices=CustomerType.choices
    )

    status = models.CharField(
        max_length=20,
        choices=AccountStatus.choices,
        default=AccountStatus.ACTIVE
    )

    address = models.TextField(blank=True)

    company_name = models.CharField(
        max_length=200,
        blank=True
    )

    notes = models.TextField(
        blank=True,
        help_text="Internal notes for authorised staff only."
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    @property
    def full_name(self):
        full = self.user.get_full_name().strip()
        return full if full else self.user.username

    @property
    def email(self):
        return self.user.email

    @property
    def phone_number(self):
        return getattr(self.user, "phone_number", "")

    def __str__(self):
        return f"{self.user.username} - {self.get_customer_type_display()} ({self.get_status_display()})"
