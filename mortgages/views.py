from decimal import Decimal, ROUND_HALF_UP
from django.db import transaction
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.views.decorators.http import require_POST
from customers.models import CustomerProfile
from .models import MortgageProduct, MortgageApplication, ApplicationStatusHistory
from .forms import MortgageApplicationForm, MortgageProductForm
from core.utils import log_audit


def staff_required(user):
    return user.is_authenticated and (user.is_staff or getattr(user, "role", "") == "STAFF")


def calculate_amortisation(amount_val, annual_rate_val, years_val):
    """
    Standard amortisation formula using Python Decimal arithmetic:
    M = P * r(1+r)^n / ((1+r)^n - 1)
    """
    amount = Decimal(str(amount_val))
    annual_rate = Decimal(str(annual_rate_val))
    years = int(years_val)
    n = Decimal(str(years * 12))

    if annual_rate == Decimal("0"):
        monthly = (amount / n).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        total_payment = (monthly * n).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        total_interest = Decimal("0.00")
        return monthly, total_payment, total_interest

    r = (annual_rate / Decimal("100")) / Decimal("12")
    one_plus_r_pow_n = (Decimal("1") + r) ** int(n)
    monthly = (amount * (r * one_plus_r_pow_n) / (one_plus_r_pow_n - Decimal("1"))).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    total_payment = (monthly * n).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    total_interest = (total_payment - amount).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    return monthly, total_payment, total_interest


@login_required
def product_list(request):
    """
    Displays active mortgage products for customers, and shows staff management shortcuts.
    """
    products = MortgageProduct.objects.filter(is_active=True).order_by("name")
    return render(request, "mortgages/product_list.html", {"products": products})


@login_required
@user_passes_test(staff_required)
def product_manage(request):
    """
    Staff-only portal to view all products (active & inactive), add new ones, and edit terms.
    """
    products = MortgageProduct.objects.all().order_by("-is_active", "name")
    return render(request, "mortgages/product_manage.html", {"products": products})


@login_required
@user_passes_test(staff_required)
def product_create(request):
    if request.method == "POST":
        form = MortgageProductForm(request.POST)
        if form.is_valid():
            product = form.save()
            log_audit(request=request, action="CREATE", model_name="MortgageProduct", object_id=product.pk, details=f"Created mortgage product {product.name}")
            messages.success(request, f"Mortgage product '{product.name}' created successfully.")
            return redirect("product-manage")
    else:
        form = MortgageProductForm()
    return render(request, "mortgages/product_form.html", {"form": form, "title": "Create Mortgage Product"})


@login_required
@user_passes_test(staff_required)
def product_edit(request, pk):
    product = get_object_or_404(MortgageProduct, pk=pk)
    if request.method == "POST":
        form = MortgageProductForm(request.POST, instance=product)
        if form.is_valid():
            product = form.save()
            log_audit(request=request, action="UPDATE", model_name="MortgageProduct", object_id=product.pk, details=f"Updated mortgage product {product.name}")
            messages.success(request, f"Mortgage product '{product.name}' updated successfully.")
            return redirect("product-manage")
    else:
        form = MortgageProductForm(instance=product)
    return render(request, "mortgages/product_form.html", {"form": form, "title": f"Edit {product.name}", "product": product})


@login_required
@user_passes_test(staff_required)
@require_POST
def product_toggle_active(request, pk):
    product = get_object_or_404(MortgageProduct, pk=pk)
    product.is_active = not product.is_active
    product.save()
    status_str = "activated" if product.is_active else "deactivated"
    log_audit(request=request, action="STATUS_CHANGE", model_name="MortgageProduct", object_id=product.pk, details=f"Product {status_str}")
    messages.success(request, f"Product '{product.name}' {status_str}.")
    return redirect("product-manage")


@login_required
def apply_mortgage(request):
    """
    Submits a new mortgage application. Restricted to customers (DEVELOPER or INDIVIDUAL).
    """
    if getattr(request.user, "role", "") not in ["INDIVIDUAL", "DEVELOPER"]:
        messages.error(request, "Only customer accounts (Individual or Developer) can submit mortgage applications.")
        return redirect("dashboard")

    # Auto-link customer profile
    profile, _ = CustomerProfile.objects.get_or_create(
        user=request.user,
        defaults={
            "customer_type": (
                CustomerProfile.CustomerType.DEVELOPER
                if getattr(request.user, "role", "") == "DEVELOPER"
                else CustomerProfile.CustomerType.INDIVIDUAL
            )
        }
    )

    if request.method == "POST":
        form = MortgageApplicationForm(request.POST)
        if form.is_valid():
            with transaction.atomic():
                application = form.save(commit=False)
                application.customer = profile
                application.save()

                # Record Initial Status History
                ApplicationStatusHistory.objects.create(
                    application=application,
                    previous_status="",
                    new_status=MortgageApplication.Status.SUBMITTED,
                    changed_by=request.user,
                    notes="Application submitted by customer."
                )
                log_audit(request=request, action="CREATE", model_name="MortgageApplication", object_id=application.pk, details=f"Submitted application for £{application.requested_amount:,.2f}")

            messages.success(request, f"Your application for £{application.requested_amount:,.2f} has been submitted successfully!")
            return redirect("my-applications")
    else:
        # Pre-select product if passed in GET param
        product_id = request.GET.get("product")
        initial = {"product": product_id} if product_id else {}
        form = MortgageApplicationForm(initial=initial)

    return render(request, "mortgages/apply.html", {"form": form})


@login_required
def my_applications(request):
    """
    Displays the authenticated customer's own mortgage applications.
    """
    try:
        profile = request.user.customer_profile
        applications = profile.mortgage_applications.select_related("product").order_by("-submitted_at")
    except CustomerProfile.DoesNotExist:
        applications = []

    return render(request, "mortgages/my_applications.html", {"applications": applications})


@login_required
def application_detail(request, pk):
    """
    Displays full details of a mortgage application including decision history.
    Customers may only view their own applications; Staff can view any application.
    """
    if request.user.is_staff or getattr(request.user, "role", "") == "STAFF":
        application = get_object_or_404(MortgageApplication.objects.select_related("customer__user", "product"), pk=pk)
    else:
        application = get_object_or_404(
            MortgageApplication.objects.select_related("customer__user", "product"),
            pk=pk,
            customer__user=request.user
        )

    history = application.status_history.select_related("changed_by").order_by("-timestamp")
    monthly, total_cost, total_interest = calculate_amortisation(
        application.requested_amount,
        application.product.annual_interest_rate,
        application.term_years
    )

    return render(request, "mortgages/application_detail.html", {
        "application": application,
        "history": history,
        "monthly_estimate": monthly,
        "total_cost": total_cost,
        "total_interest": total_interest,
    })


@login_required
@user_passes_test(staff_required)
def application_list(request):
    """
    Staff underwriting pipeline. Displays all applications with search and status filtering.
    """
    query = request.GET.get("q", "").strip()
    status_filter = request.GET.get("status", "")

    applications = MortgageApplication.objects.select_related("customer__user", "product").order_by("-submitted_at")

    if status_filter:
        applications = applications.filter(status=status_filter)
    if query:
        applications = applications.filter(customer__user__username__icontains=query)

    return render(request, "mortgages/application_list.html", {
        "applications": applications,
        "query": query,
        "status_filter": status_filter,
        "statuses": MortgageApplication.Status.choices
    })


@login_required
@user_passes_test(staff_required)
@require_POST
def update_application_status(request, pk):
    """
    Staff decision update. Executes in a database transaction, records
    ApplicationStatusHistory, and writes an AuditLog entry.
    """
    application = get_object_or_404(MortgageApplication, pk=pk)
    new_status = request.POST.get("status")
    staff_notes = request.POST.get("staff_notes", "").strip()

    if new_status in MortgageApplication.Status.values:
        old_status = application.status
        with transaction.atomic():
            application.status = new_status
            application.staff_notes = staff_notes
            application.save()

            # Record decision history
            ApplicationStatusHistory.objects.create(
                application=application,
                previous_status=old_status,
                new_status=new_status,
                changed_by=request.user,
                notes=staff_notes
            )

            log_audit(
                request=request,
                action="STATUS_CHANGE",
                model_name="MortgageApplication",
                object_id=application.pk,
                details=f"Status transitioned from {old_status} to {new_status}. Notes: {staff_notes}"
            )

        messages.success(request, f"Application #{application.pk} status updated to {application.get_status_display()}.")
    else:
        messages.error(request, "Invalid status choice selected.")

    return redirect("application-detail", pk=pk)


@login_required
def repayment_estimator(request):
    """
    Financial amortisation calculator using Python Decimal precision.
    Outputs: Monthly payment, Total repayment, Total interest payable, with edge-case handling.
    """
    calculation = None
    amount_input = 250000
    rate_input = 4.5
    years_input = 25

    if request.method == "POST":
        try:
            amount_val = request.POST.get("amount", "0")
            rate_val = request.POST.get("rate", "0")
            years_val = request.POST.get("years", "0")

            amount_input = float(amount_val)
            rate_input = float(rate_val)
            years_input = int(years_val)

            if amount_input > 0 and years_input > 0 and rate_input >= 0:
                monthly, total_cost, total_interest = calculate_amortisation(amount_val, rate_val, years_val)
                calculation = {
                    "principal": Decimal(str(amount_val)),
                    "annual_rate": Decimal(str(rate_val)),
                    "years": years_input,
                    "monthly_payment": monthly,
                    "total_payment": total_cost,
                    "total_interest": total_interest,
                }
            else:
                messages.error(request, "Please enter valid positive loan terms and amounts.")
        except Exception as e:
            messages.error(request, f"Calculation error: {str(e)}")

    return render(request, "mortgages/repayment_estimator.html", {
        "calculation": calculation,
        "amount_input": amount_input,
        "rate_input": rate_input,
        "years_input": years_input,
    })
