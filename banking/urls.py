from django.urls import path
from . import views, views_api

urlpatterns = [
    path("", views.banking_dashboard, name="banking-dashboard"),
    path("api/account-verify/", views_api.BankAccountVerificationAPIView.as_view(), name="api-bank-verify"),
    path("api/rates/", views_api.BankMarketRatesAPIView.as_view(), name="api-bank-rates"),
    path("api/credit-score/", views_api.BankCreditAssessmentAPIView.as_view(), name="api-credit-score"),
]
