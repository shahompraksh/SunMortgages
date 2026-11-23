from django.db import models

# Create your models here.

from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):

    class Role(models.TextChoices):
        STAFF = "STAFF", "Staff"
        DEVELOPER = "DEVELOPER", "Property Developer"
        INDIVIDUAL = "INDIVIDUAL", "Individual Customer"

    email = models.EmailField(unique=True)

    role = models.CharField(
        max_length=20,
        choices=Role.choices,
        default=Role.INDIVIDUAL
    )

    phone_number = models.CharField(
        max_length=20,
        blank=True
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    updated_at = models.DateTimeField(
        auto_now=True
    )

    def __str__(self):
        return f"{self.username} ({self.role})"
