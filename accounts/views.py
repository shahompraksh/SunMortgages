from django.shortcuts import render, redirect
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.contrib import messages
from django.db.models import Sum, Count
from .forms import RegistrationForm
from customers.models import CustomerProfile
from mortgages.models import MortgageProduct, MortgageApplication
from core.models import AuditLog
from core.utils import log_audit


def register_view(request):
    if request.user.is_authenticated:
        return redirect("dashboard")

    if request.method == "POST":
        form = RegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()
            # Ensure CustomerProfile is immediately generated
            customer_type = (
                CustomerProfile.CustomerType.DEVELOPER
                if user.role == "DEVELOPER"
                else CustomerProfile.CustomerType.INDIVIDUAL
            )
            CustomerProfile.objects.get_or_create(
                user=user,
                defaults={"customer_type": customer_type}
            )

            login(request, user)
            log_audit(request=request, user=user, action="CREATE", model_name="User", object_id=user.pk, details=f"Registered account ({user.role})")
            messages.success(request, f"Welcome to SunMortgages, {user.username}! Your account has been registered.")
            return redirect("dashboard")
    else:
        form = RegistrationForm()

    return render(request, "accounts/register.html", {"form": form})


@login_required
def dashboard_view(request):
    """
    Role-aware dynamic dashboard view.
    Dispatches tailored analytics and operational datasets for Staff, Developers, and Individuals.
    """
    user = request.user
    context = {"user": user}

    if user.is_staff or getattr(user, "role", "") == "STAFF":
        # Staff Dashboard KPI Metrics
        context.update({
            "total_customers": CustomerProfile.objects.count(),
            "individual_customers": CustomerProfile.objects.filter(customer_type="INDIVIDUAL").count(),
            "developer_customers": CustomerProfile.objects.filter(customer_type="DEVELOPER").count(),
            "total_products": MortgageProduct.objects.count(),
            "total_applications": MortgageApplication.objects.count(),
            "pending_applications": MortgageApplication.objects.filter(status__in=["SUBMITTED", "UNDER_REVIEW"]).count(),
            "approved_applications": MortgageApplication.objects.filter(status="APPROVED").count(),
            "rejected_applications": MortgageApplication.objects.filter(status="REJECTED").count(),
            "recent_applications": MortgageApplication.objects.select_related("customer__user", "product").order_by("-submitted_at")[:6],
            "recent_audits": AuditLog.objects.select_related("user").order_by("-timestamp")[:6],
        })

    elif getattr(user, "role", "") == "DEVELOPER":
        # Property Developer Dashboard
        profile, _ = CustomerProfile.objects.get_or_create(
            user=user,
            defaults={"customer_type": CustomerProfile.CustomerType.DEVELOPER}
        )
        apps = profile.mortgage_applications.select_related("product").order_by("-submitted_at")
        total_vol = apps.aggregate(total=Sum("requested_amount"))["total"] or 0

        context.update({
            "profile": profile,
            "applications": apps[:5],
            "total_applications_count": apps.count(),
            "total_requested_volume": total_vol,
            "available_products": MortgageProduct.objects.filter(is_active=True).order_by("name")[:4],
        })

    else:
        # Individual Customer Dashboard
        profile, _ = CustomerProfile.objects.get_or_create(
            user=user,
            defaults={"customer_type": CustomerProfile.CustomerType.INDIVIDUAL}
        )
        apps = profile.mortgage_applications.select_related("product").order_by("-submitted_at")
        total_vol = apps.aggregate(total=Sum("requested_amount"))["total"] or 0

        context.update({
            "profile": profile,
            "applications": apps[:5],
            "total_applications_count": apps.count(),
            "total_requested_volume": total_vol,
            "available_products": MortgageProduct.objects.filter(is_active=True).order_by("name")[:4],
        })

    return render(request, "accounts/dashboard.html", context)


@require_POST
def logout_view(request):
    username = request.user.username if request.user.is_authenticated else "Anonymous"
    log_audit(request=request, action="LOGOUT", details=f"User {username} logged out.")
    logout(request)
    messages.info(request, "You have been securely signed out of SunMortgages.")
    return redirect("login")
