from django.conf import settings
from django.db import models


class GeneratedReport(models.Model):
    class ReportType(models.TextChoices):
        CUSTOMERS = "CUSTOMERS", "Customer Directory Report"
        APPLICATIONS = "APPLICATIONS", "Mortgage Applications Report"
        APPROVALS = "APPROVALS", "Approval & Underwriting Report"
        PRODUCTS = "PRODUCTS", "Mortgage Products Performance"

    class Format(models.TextChoices):
        CSV = "CSV", "CSV Spreadsheet"
        PDF = "PDF", "PDF Document"
        HTML = "HTML", "Web Dashboard View"

    report_type = models.CharField(max_length=50, choices=ReportType.choices)
    format = models.CharField(max_length=10, choices=Format.choices)
    generated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="generated_reports"
    )
    records_count = models.PositiveIntegerField(default=0)
    parameters = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.get_report_type_display()} ({self.format}) - {self.created_at:%Y-%m-%d %H:%M}"
