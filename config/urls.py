from django.contrib import admin
from django.urls import path, include
from django.views.generic import RedirectView

urlpatterns = [
    path("", include("core.urls")),
    path("admin/", admin.site.urls),
    path("accounts/", include("accounts.urls")),
    path("customers/", include("customers.urls")),
    path("mortgages/", include("mortgages.urls")),
    path("banking/", include("banking.urls")),
    path("reports/", include("reports.urls")),
]
