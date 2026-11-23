import csv
from django.http import HttpResponse
from django.shortcuts import render
from django.contrib.auth.decorators import login_required, user_passes_test
from django.db.models import Count, Sum, Avg
from django.utils import timezone
from accounts.models import User
from customers.models import CustomerProfile
from mortgages.models import MortgageProduct, MortgageApplication
from .models import GeneratedReport
from core.utils import log_audit


def staff_required(user):
    return user.is_authenticated and (user.is_staff or getattr(user, "role", "") == "STAFF")


@login_required
@user_passes_test(staff_required)
def reports_dashboard(request):
    """
    Staff-only analytics and reporting dashboard.
    Provides multi-dimensional filtering, aggregate financial figures,
    and direct triggers for CSV/PDF compliance exports.
    """
    status_filter = request.GET.get("status", "")
    customer_type_filter = request.GET.get("customer_type", "")

    # Base querysets
    applications = MortgageApplication.objects.select_related("customer__user", "product")
    customers = CustomerProfile.objects.select_related("user")

    if status_filter:
        applications = applications.filter(status=status_filter)
    if customer_type_filter:
        customers = customers.filter(customer_type=customer_type_filter)
        applications = applications.filter(customer__customer_type=customer_type_filter)

    # Key Metrics
    total_apps_count = applications.count()
    total_requested_volume = applications.aggregate(total=Sum("requested_amount"))["total"] or 0
    approved_volume = applications.filter(status=MortgageApplication.Status.APPROVED).aggregate(total=Sum("requested_amount"))["total"] or 0

    status_counts = dict(applications.values_list("status").annotate(count=Count("id")))
    product_stats = MortgageProduct.objects.annotate(
        app_count=Count("applications"),
        total_volume=Sum("applications__requested_amount")
    ).order_by("-app_count")

    return render(request, "reports/reports_dashboard.html", {
        "total_apps_count": total_apps_count,
        "total_requested_volume": total_requested_volume,
        "approved_volume": approved_volume,
        "status_counts": status_counts,
        "product_stats": product_stats,
        "status_filter": status_filter,
        "customer_type_filter": customer_type_filter,
        "statuses": MortgageApplication.Status.choices,
        "customer_types": CustomerProfile.CustomerType.choices,
    })


@login_required
@user_passes_test(staff_required)
def export_customers_csv(request):
    """
    Generates a secure, RFC-4180 compliant CSV export of customer profiles.
    """
    response = HttpResponse(content_type="text/csv")
    filename = f"sunmortgages_customers_{timezone.now():%Y%m%d_%H%M%S}.csv"
    response["Content-Disposition"] = f'attachment; filename="{filename}"'

    writer = csv.writer(response)
    writer.writerow([
        "Customer ID",
        "Username",
        "Full Name",
        "Email",
        "Phone Number",
        "Customer Type",
        "Account Status",
        "Company Name",
        "Address",
        "Registration Date"
    ])

    customers = CustomerProfile.objects.select_related("user").order_by("-created_at")
    for c in customers:
        writer.writerow([
            c.id,
            c.user.username,
            c.full_name,
            c.email,
            c.phone_number,
            c.get_customer_type_display(),
            c.get_status_display(),
            c.company_name or "N/A",
            c.address.replace("\n", ", "),
            c.created_at.strftime("%Y-%m-%d %H:%M:%S")
        ])

    GeneratedReport.objects.create(
        report_type=GeneratedReport.ReportType.CUSTOMERS,
        format=GeneratedReport.Format.CSV,
        generated_by=request.user,
        records_count=customers.count()
    )
    log_audit(request=request, action="REPORT_EXPORT", model_name="CustomerProfile", details=f"Exported {customers.count()} customers to CSV")

    return response


@login_required
@user_passes_test(staff_required)
def export_applications_csv(request):
    """
    Generates a secure CSV export of all mortgage applications.
    """
    response = HttpResponse(content_type="text/csv")
    filename = f"sunmortgages_applications_{timezone.now():%Y%m%d_%H%M%S}.csv"
    response["Content-Disposition"] = f'attachment; filename="{filename}"'

    writer = csv.writer(response)
    writer.writerow([
        "Application ID",
        "Customer Username",
        "Customer Email",
        "Customer Type",
        "Mortgage Product",
        "Requested Amount",
        "Term (Years)",
        "Application Status",
        "Submitted Date",
        "Last Updated",
        "Applicant Notes",
        "Staff Notes"
    ])

    applications = MortgageApplication.objects.select_related("customer__user", "product").order_by("-submitted_at")
    for app in applications:
        writer.writerow([
            app.id,
            app.customer.user.username,
            app.customer.user.email,
            app.customer.get_customer_type_display(),
            app.product.name,
            float(app.requested_amount),
            app.term_years,
            app.get_status_display(),
            app.submitted_at.strftime("%Y-%m-%d %H:%M:%S"),
            app.updated_at.strftime("%Y-%m-%d %H:%M:%S"),
            app.applicant_notes.replace("\n", " "),
            app.staff_notes.replace("\n", " ")
        ])

    GeneratedReport.objects.create(
        report_type=GeneratedReport.ReportType.APPLICATIONS,
        format=GeneratedReport.Format.CSV,
        generated_by=request.user,
        records_count=applications.count()
    )
    log_audit(request=request, action="REPORT_EXPORT", model_name="MortgageApplication", details=f"Exported {applications.count()} mortgage applications to CSV")

    return response


@login_required
@user_passes_test(staff_required)
def print_application_report(request):
    """
    Renders an executive, print-optimized document view suitable for PDF printing.
    """
    applications = MortgageApplication.objects.select_related("customer__user", "product").order_by("-submitted_at")
    total_volume = applications.aggregate(total=Sum("requested_amount"))["total"] or 0

    GeneratedReport.objects.create(
        report_type=GeneratedReport.ReportType.APPLICATIONS,
        format=GeneratedReport.Format.PDF,
        generated_by=request.user,
        records_count=applications.count()
    )

    return render(request, "reports/print_report.html", {
        "applications": applications,
        "total_volume": total_volume,
        "generated_at": timezone.now(),
        "generated_by": request.user
    })
