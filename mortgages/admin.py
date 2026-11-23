from django.contrib import admin
from .models import MortgageProduct, MortgageApplication, ApplicationStatusHistory


class ApplicationStatusHistoryInline(admin.TabularInline):
    model = ApplicationStatusHistory
    extra = 0
    readonly_fields = ("previous_status", "new_status", "changed_by", "notes", "timestamp")
    can_delete = False


@admin.register(MortgageProduct)
class MortgageProductAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "annual_interest_rate",
        "minimum_amount",
        "maximum_amount",
        "is_active",
    )
    list_filter = ("is_active",)
    search_fields = ("name",)


@admin.register(MortgageApplication)
class MortgageApplicationAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "customer",
        "product",
        "requested_amount",
        "status",
        "submitted_at",
    )
    list_filter = ("status", "product")
    search_fields = (
        "customer__user__username",
        "customer__user__email",
    )
    readonly_fields = ("submitted_at", "updated_at")
    inlines = [ApplicationStatusHistoryInline]


@admin.register(ApplicationStatusHistory)
class ApplicationStatusHistoryAdmin(admin.ModelAdmin):
    list_display = ("application", "previous_status", "new_status", "changed_by", "timestamp")
    list_filter = ("previous_status", "new_status")
    search_fields = ("application__customer__user__username", "notes")
    readonly_fields = ("application", "previous_status", "new_status", "changed_by", "notes", "timestamp")
