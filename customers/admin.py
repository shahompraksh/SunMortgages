from django.contrib import admin
from .models import CustomerProfile


@admin.register(CustomerProfile)
class CustomerProfileAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "user",
        "customer_type",
        "status",
        "company_name",
        "created_at",
    )
    list_filter = ("customer_type", "status")
    search_fields = (
        "user__username",
        "user__email",
        "company_name",
    )
    readonly_fields = (
        "created_at",
        "updated_at",
    )
