from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from .models import BankPartner, ApiRequestLog, BankAccountVerification
from .services import BankGatewayService


def staff_required(user):
    return user.is_authenticated and (user.is_staff or getattr(user, "role", "") == "STAFF")


@login_required
@user_passes_test(staff_required)
def banking_dashboard(request):
    """
    Staff dashboard to inspect banking integrations, test account verifications,
    review live market interest rates, and audit real-time API request logs.
    """
    service = BankGatewayService()
    partners = BankPartner.objects.all()
    logs = ApiRequestLog.objects.select_related("partner")[:25]
    verifications = BankAccountVerification.objects.select_related("customer__user")[:15]
    market_rates = service.fetch_market_interest_rates()

    test_result = None
    if request.method == "POST":
        action = request.POST.get("action")
        if action == "verify_test":
            bank_name = request.POST.get("bank_name", "Barclays Bank UK")
            account_number = request.POST.get("account_number", "").strip()
            account_name = request.POST.get("account_name", "").strip()

            if account_number and account_name:
                test_result = service.verify_account(bank_name, account_number, account_name)
                if test_result["success"]:
                    messages.success(request, f"Account Verified Successfully! Ref: {test_result['reference']}")
                else:
                    messages.error(request, "Account Verification Failed. The bank could not match the details.")
            else:
                messages.warning(request, "Please enter both an account number and account holder name.")

        elif action == "sync_rates":
            messages.success(request, "Market benchmark mortgage rates successfully synchronized from Banking Gateway.")
            return redirect("banking-dashboard")

    return render(request, "banking/banking_dashboard.html", {
        "partners": partners,
        "logs": logs,
        "verifications": verifications,
        "market_rates": market_rates,
        "test_result": test_result,
        "active_partner": service.partner
    })
