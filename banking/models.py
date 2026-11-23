from django.db import models


class BankPartner(models.Model):
    name = models.CharField(max_length=150)
    code = models.CharField(max_length=50, unique=True)
    base_url = models.URLField(max_length=255)
    api_key_masked = models.CharField(max_length=100, default="sk_test_••••••••••••")
    is_active = models.BooleanField(default=True)
    is_mock = models.BooleanField(
        default=True,
        help_text="Explicit indicator: Set to True for simulated sandbox/mock environments."
    )
    supported_services = models.CharField(
        max_length=255,
        default="account_verification,credit_check,rate_sync",
        help_text="Comma-separated capabilities."
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        mode = "Mock/Sandbox" if self.is_mock else "Live Partner"
        return f"{self.name} ({self.code}) - [{mode}]"


class ApiRequestLog(models.Model):
    partner = models.ForeignKey(
        BankPartner,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="logs"
    )
    endpoint = models.CharField(max_length=255)
    method = models.CharField(max_length=10, default="GET")
    status_code = models.PositiveSmallIntegerField(null=True, blank=True)
    request_summary = models.TextField(blank=True)
    response_summary = models.TextField(blank=True)
    response_time_ms = models.PositiveIntegerField(
        default=0,
        help_text="Round-trip latency in milliseconds."
    )
    is_success = models.BooleanField(default=False)
    error_message = models.TextField(blank=True)
    timestamp = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ["-timestamp"]
        indexes = [
            models.Index(fields=["status_code", "timestamp"]),
            models.Index(fields=["endpoint", "timestamp"]),
        ]

    def __str__(self):
        status = self.status_code or "ERR"
        return f"[{self.timestamp:%Y-%m-%d %H:%M:%S}] {self.method} {self.endpoint} -> {status} ({self.response_time_ms}ms)"


class BankAccountVerification(models.Model):
    customer = models.ForeignKey(
        "customers.CustomerProfile",
        on_delete=models.CASCADE,
        related_name="bank_verifications"
    )
    bank_name = models.CharField(max_length=100)
    account_number = models.CharField(max_length=50)
    account_name = models.CharField(max_length=150)
    is_verified = models.BooleanField(default=False)
    verification_reference = models.CharField(max_length=100, blank=True)
    verified_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        state = "Verified" if self.is_verified else "Pending/Failed"
        return f"{self.customer.user.username} - {self.bank_name} ({state})"
