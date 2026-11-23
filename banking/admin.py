from django.contrib import admin
from .models import BankPartner, ApiRequestLog, BankAccountVerification


@admin.register(BankPartner)
class BankPartnerAdmin(admin.ModelAdmin):
    list_display = ("name", "code", "is_mock", "is_active", "created_at")
    list_filter = ("is_mock", "is_active")
    search_fields = ("name", "code")


@admin.register(ApiRequestLog)
class ApiRequestLogAdmin(admin.ModelAdmin):
    list_display = ("timestamp", "partner", "method", "endpoint", "status_code", "response_time_ms", "is_success")
    list_filter = ("is_success", "status_code", "method")
    search_fields = ("endpoint", "request_summary", "response_summary", "error_message")
    readonly_fields = (
        "partner",
        "endpoint",
        "method",
        "status_code",
        "request_summary",
        "response_summary",
        "response_time_ms",
        "is_success",
        "error_message",
        "timestamp",
    )


@admin.register(BankAccountVerification)
class BankAccountVerificationAdmin(admin.ModelAdmin):
    list_display = ("customer", "bank_name", "account_number", "is_verified", "verified_at")
    list_filter = ("is_verified", "bank_name")
    search_fields = ("customer__user__username", "account_number", "account_name")
