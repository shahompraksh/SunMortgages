from django.test import TestCase, Client
from django.urls import reverse
from banking.services import BankGatewayService
from banking.models import ApiRequestLog, BankPartner


class BankingGatewayTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.service = BankGatewayService()

    def test_bank_account_verification_success(self):
        result = self.service.verify_account(
            bank_name="Barclays Bank UK",
            account_number="123456789",
            account_name="Sarah Jenkins"
        )
        self.assertTrue(result["success"])
        self.assertIsNotNone(result["reference"])
        # Check ApiRequestLog creation
        log = ApiRequestLog.objects.filter(is_success=True).first()
        self.assertIsNotNone(log)
        self.assertEqual(log.status_code, 200)

    def test_bank_account_verification_failure(self):
        # Accounts ending in 0000 simulate rejection
        result = self.service.verify_account(
            bank_name="NatWest Interbank",
            account_number="9990000",
            account_name="Ghost Account"
        )
        self.assertFalse(result["success"])
        log = ApiRequestLog.objects.filter(is_success=False).first()
        self.assertIsNotNone(log)
        self.assertEqual(log.status_code, 404)

    def test_market_rate_retrieval(self):
        rates = self.service.fetch_market_interest_rates()
        self.assertGreaterEqual(len(rates), 3)
        self.assertIn("bank", rates[0])
        self.assertIn("effective_rate", rates[0])

    def test_credit_bureau_eligibility(self):
        assessment = self.service.check_credit_eligibility(
            monthly_income=10000,
            requested_amount=200000,
            term_years=25
        )
        self.assertTrue(assessment["eligible"])
        self.assertIn(assessment["risk_rating"], ["LOW_RISK", "MODERATE_RISK", "ELEVATED_RISK"])

    def test_rest_api_account_verification_endpoint(self):
        response = self.client.post(
            reverse("api-bank-verify"),
            data={
                "bank_name": "Barclays Bank UK",
                "account_number": "5566778899",
                "account_name": "Apex Developments"
            },
            content_type="application/json"
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["success"])
