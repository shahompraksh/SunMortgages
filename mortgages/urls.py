from django.urls import path
from . import views

urlpatterns = [
    path("products/", views.product_list, name="product-list"),
    path("products/manage/", views.product_manage, name="product-manage"),
    path("products/create/", views.product_create, name="product-create"),
    path("products/<int:pk>/edit/", views.product_edit, name="product-edit"),
    path("products/<int:pk>/toggle/", views.product_toggle_active, name="product-toggle-active"),
    path("apply/", views.apply_mortgage, name="apply-mortgage"),
    path("my-applications/", views.my_applications, name="my-applications"),
    path("applications/", views.application_list, name="application-list"),
    path("applications/<int:pk>/", views.application_detail, name="application-detail"),
    path("applications/<int:pk>/update/", views.update_application_status, name="update-application-status"),
    path("repayment-estimator/", views.repayment_estimator, name="repayment-estimator"),
]
