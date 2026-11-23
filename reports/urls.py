from django.urls import path
from . import views

urlpatterns = [
    path("", views.reports_dashboard, name="reports-dashboard"),
    path("export/customers/csv/", views.export_customers_csv, name="export-customers-csv"),
    path("export/applications/csv/", views.export_applications_csv, name="export-applications-csv"),
    path("print/applications/", views.print_application_report, name="print-applications-report"),
]
