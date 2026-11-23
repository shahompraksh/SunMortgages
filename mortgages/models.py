from decimal import Decimal
from django.conf import settings
from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from django.core.exceptions import ValidationError


class MortgageProduct(models.Model):
    name = models.CharField(max_length=150)
    description = models.TextField(blank=True)
    annual_interest_rate = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        validators=[
            MinValueValidator(Decimal("0.00")),
            MaxValueValidator(Decimal("100.00"))
        ]
    )
    minimum_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("1.00"))]
    )
    maximum_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("1.00"))]
    )
    maximum_term_years = models.PositiveSmallIntegerField(
        default=30,
        validators=[
            MinValueValidator(1),
            MaxValueValidator(50)
        ]
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name

    def clean(self):
        if (
            self.minimum_amount is not None
            and self.maximum_amount is not None
            and self.minimum_amount > self.maximum_amount
        ):
            raise ValidationError(
                "Minimum amount cannot exceed maximum amount."
            )


class MortgageApplication(models.Model):
    class Status(models.TextChoices):
        SUBMITTED = "SUBMITTED", "Submitted"
        UNDER_REVIEW = "UNDER_REVIEW", "Under Review"
        APPROVED = "APPROVED", "Approved"
        REJECTED = "REJECTED", "Rejected"

    customer = models.ForeignKey(
        "customers.CustomerProfile",
        on_delete=models.PROTECT,
        related_name="mortgage_applications"
    )
    product = models.ForeignKey(
        MortgageProduct,
        on_delete=models.PROTECT,
        related_name="applications"
    )
    requested_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("1.00"))]
    )
    term_years = models.PositiveSmallIntegerField(
        validators=[
            MinValueValidator(1),
            MaxValueValidator(50)
        ]
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.SUBMITTED
    )
    applicant_notes = models.TextField(blank=True)
    staff_notes = models.TextField(blank=True)
    submitted_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return (
            f"{self.customer.user.username} - "
            f"{self.product.name} ({self.get_status_display()})"
        )


class ApplicationStatusHistory(models.Model):
    application = models.ForeignKey(
        MortgageApplication,
        on_delete=models.CASCADE,
        related_name="status_history"
    )
    previous_status = models.CharField(
        max_length=20,
        choices=MortgageApplication.Status.choices,
        blank=True
    )
    new_status = models.CharField(
        max_length=20,
        choices=MortgageApplication.Status.choices
    )
    changed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="status_decisions"
    )
    notes = models.TextField(blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-timestamp"]
        verbose_name_plural = "Application status histories"

    def __str__(self):
        return f"App #{self.application_id}: {self.previous_status} -> {self.new_status} at {self.timestamp:%Y-%m-%d %H:%M}"
