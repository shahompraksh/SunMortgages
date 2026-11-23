from decimal import Decimal
from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from customers.models import CustomerProfile
from mortgages.models import MortgageProduct, MortgageApplication, ApplicationStatusHistory
from mortgages.views import calculate_amortisation

User = get_user_model()


class MortgageSystemTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.password = "StrongMortgagePass123!@"
        self.staff = User.objects.create_user(
            username="credit_officer",
            email="credit@sunmortgages.com",
            password=self.password,
            role="STAFF",
            is_staff=True
        )
        self.borrower = User.objects.create_user(
            username="home_buyer",
            email="buyer@example.com",
            password=self.password,
            role="INDIVIDUAL"
        )
        self.profile = CustomerProfile.objects.create(
            user=self.borrower,
            customer_type=CustomerProfile.CustomerType.INDIVIDUAL
        )
        self.product = MortgageProduct.objects.create(
            name="Standard Fixed 25",
            description="25 year fixed repayment mortgage.",
            annual_interest_rate=Decimal("4.50"),
            minimum_amount=Decimal("50000.00"),
            maximum_amount=Decimal("1000000.00"),
            maximum_term_years=35,
            is_active=True
        )

    def test_mortgage_product_clean_validation(self):
        # Min amount cannot exceed max amount
        invalid_product = MortgageProduct(
            name="Invalid Product",
            annual_interest_rate=Decimal("3.50"),
            minimum_amount=Decimal("500000.00"),
            maximum_amount=Decimal("100000.00")
        )
        with self.assertRaises(ValidationError):
            invalid_product.clean()

    def test_mortgage_application_submission_valid(self):
        self.client.login(username="home_buyer", password=self.password)
        response = self.client.post(reverse("apply-mortgage"), {
            "product": self.product.id,
            "requested_amount": "200000.00",
            "term_years": 25,
            "applicant_notes": "First home purchase"
        }, follow=True)
        self.assertEqual(response.status_code, 200)
        app = MortgageApplication.objects.filter(customer=self.profile).first()
        self.assertIsNotNone(app)
        self.assertEqual(app.requested_amount, Decimal("200000.00"))
        self.assertEqual(app.status, MortgageApplication.Status.SUBMITTED)
        # Check initial status history
        self.assertTrue(app.status_history.filter(new_status=MortgageApplication.Status.SUBMITTED).exists())

    def test_mortgage_application_violates_bounds(self):
        self.client.login(username="home_buyer", password=self.password)
        # Below minimum amount
        response = self.client.post(reverse("apply-mortgage"), {
            "product": self.product.id,
            "requested_amount": "10000.00",
            "term_years": 25,
        })
        self.assertEqual(response.status_code, 200)
        form = response.context["form"]
        self.assertFormError(form, "requested_amount", f"Minimum loan amount for {self.product.name} is £50,000.00.")

    def test_application_status_transition_and_history(self):
        app = MortgageApplication.objects.create(
            customer=self.profile,
            product=self.product,
            requested_amount=Decimal("250000.00"),
            term_years=25
        )
        self.client.login(username="credit_officer", password=self.password)
        response = self.client.post(reverse("update-application-status", kwargs={"pk": app.pk}), {
            "status": MortgageApplication.Status.APPROVED,
            "staff_notes": "Underwriting approved based on clean credit file."
        }, follow=True)
        self.assertEqual(response.status_code, 200)
        app.refresh_from_db()
        self.assertEqual(app.status, MortgageApplication.Status.APPROVED)
        # Verify status history entry was created
        history = ApplicationStatusHistory.objects.filter(application=app, new_status=MortgageApplication.Status.APPROVED).first()
        self.assertIsNotNone(history)
        self.assertEqual(history.changed_by, self.staff)
        self.assertIn("approved", history.notes)

    def test_amortisation_calculator_math(self):
        # £200,000 at 4.5% for 25 years
        monthly, total_cost, total_interest = calculate_amortisation("200000.00", "4.50", 25)
        self.assertEqual(monthly, Decimal("1111.66"))
        self.assertEqual(total_cost, Decimal("333498.00"))
        self.assertEqual(total_interest, Decimal("133498.00"))

    def test_zero_interest_amortisation(self):
        # Zero interest edge case: £120,000 at 0% for 10 years (120 months)
        monthly, total_cost, total_interest = calculate_amortisation("120000.00", "0", 10)
        self.assertEqual(monthly, Decimal("1000.00"))
        self.assertEqual(total_cost, Decimal("120000.00"))
        self.assertEqual(total_interest, Decimal("0.00"))
