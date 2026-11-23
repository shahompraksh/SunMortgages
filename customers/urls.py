from django.urls import path
from . import views

urlpatterns = [
    path("my-profile/", views.my_profile, name="my-profile"),
    path("", views.customer_list, name="customer-list"),
    path("<int:pk>/", views.customer_detail, name="customer-detail"),
    path("<int:pk>/edit/", views.customer_edit, name="customer-edit"),
    path("<int:pk>/delete/", views.customer_delete, name="customer-delete"),
]
