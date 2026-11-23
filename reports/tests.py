from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from customers.models import CustomerProfile
from mortgages.models import MortgageProduct, MortgageApplication
from decimal import Decimal

User = get_user_model()


class ReportingSystemTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.password = "StaffReporter123!#"
        self.staff = User.objects.create_user(
            username="risk_officer",
            email="risk@sunmortgages.com",
            password=self.password,
            role="STAFF",
            is_staff=True
        )
        self.customer = User.objects.create_user(
            username="regular_user",
            email="regular@example.com",
            password=self.password,
            role="INDIVIDUAL"
        )
        self.profile = CustomerProfile.objects.create(
            user=self.customer,
            customer_type=CustomerProfile.CustomerType.INDIVIDUAL
        )
        self.product = MortgageProduct.objects.create(
            name="Buy-To-Let Fixed",
            annual_interest_rate=Decimal("5.00"),
            minimum_amount=Decimal("40000.00"),
            maximum_amount=Decimal("500000.00"),
            maximum_term_years=30
        )
        self.app = MortgageApplication.objects.create(
            customer=self.profile,
            product=self.product,
            requested_amount=Decimal("150000.00"),
            term_years=20,
            status=MortgageApplication.Status.APPROVED
        )

    def test_reports_access_restricted_to_staff(self):
        self.client.login(username="regular_user", password=self.password)
        response = self.client.get(reverse("reports-dashboard"))
        self.assertEqual(response.status_code, 302)

    def test_staff_can_view_reports_dashboard(self):
        self.client.login(username="risk_officer", password=self.password)
        response = self.client.get(reverse("reports-dashboard"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "150000")

    def test_export_customers_csv(self):
        self.client.login(username="risk_officer", password=self.password)
        response = self.client.get(reverse("export-customers-csv"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "text/csv")
        content = response.content.decode("utf-8")
        self.assertIn("Customer ID,Username", content)
        self.assertIn("regular_user", content)

    def test_export_applications_csv(self):
        self.client.login(username="risk_officer", password=self.password)
        response = self.client.get(reverse("export-applications-csv"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "text/csv")
        content = response.content.decode("utf-8")
        self.assertIn("Application ID,Customer Username", content)
        self.assertIn("Buy-To-Let Fixed", content)
        self.assertIn("150000.0", content)
