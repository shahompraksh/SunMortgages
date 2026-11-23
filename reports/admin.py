from django.contrib import admin
from .models import GeneratedReport


@admin.register(GeneratedReport)
class GeneratedReportAdmin(admin.ModelAdmin):
    list_display = ("report_type", "format", "records_count", "generated_by", "created_at")
    list_filter = ("report_type", "format", "created_at")
    readonly_fields = ("report_type", "format", "records_count", "generated_by", "parameters", "created_at")
