import json
from decimal import Decimal
from unittest.mock import patch
from django.test import TestCase, Client
from django.urls import reverse
from accounts.models import User
from customers.models import CustomerProfile
from mortgages.models import MortgageProduct, MortgageApplication
from core.ai_service import GeminiAIService


class CoreLandingAndAITests(TestCase):
    def setUp(self):
        self.client = Client()

        # Users
        self.staff_user = User.objects.create_user(
            username="staff_officer",
            email="staff@sunmortgages.co.uk",
            password="SecureStaffPassword123!",
            role=User.Role.STAFF,
            is_staff=True,
        )
        self.customer_user = User.objects.create_user(
            username="homebuyer_alice",
            email="alice@example.com",
            password="SecureAlicePassword123!",
            role=User.Role.INDIVIDUAL,
        )
        self.customer_profile = CustomerProfile.objects.create(
            user=self.customer_user,
            customer_type=CustomerProfile.CustomerType.INDIVIDUAL,
            address="74 London Road, London",
        )

        # Mortgage Product & Application
        self.product = MortgageProduct.objects.create(
            name="Standard 2-Year Fixed",
            annual_interest_rate=Decimal("4.25"),
            minimum_amount=Decimal("50000.00"),
            maximum_amount=Decimal("1000000.00"),
            maximum_term_years=35,
            is_active=True,
        )
        self.application = MortgageApplication.objects.create(
            customer=self.customer_profile,
            product=self.product,
            requested_amount=Decimal("250000.00"),
            term_years=25,
            applicant_notes="First time homebuyer with 20% deposit.",
        )

    def test_landing_page_renders_successfully(self):
        response = self.client.get(reverse("landing"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "SunMortgages")
        self.assertContains(response, "Standard 2-Year Fixed")
        self.assertIn("products", response.context)
        self.assertIn("stats", response.context)

    def test_ai_chat_api_empty_message(self):
        response = self.client.post(
            reverse("ai-chat-api"),
            data=json.dumps({"message": ""}),
            content_type="application/json"
        )
        self.assertEqual(response.status_code, 400)

    def test_ai_chat_api_with_mocked_gemini(self):
        mock_response = {
            "candidates": [{
                "content": {
                    "parts": [{"text": "Hello! I can explain fixed rate mortgages."}]
                }
            }]
        }
        with patch.object(GeminiAIService, "_call_gemini_api", return_value=mock_response):
            response = self.client.post(
                reverse("ai-chat-api"),
                data=json.dumps({"message": "Tell me about fixed rates"}),
                content_type="application/json"
            )
            self.assertEqual(response.status_code, 200)
            data = response.json()
            self.assertEqual(data["status"], "success")
            self.assertIn("fixed rate mortgages", data["reply"])

    def test_ai_underwrite_forbidden_for_regular_customer(self):
        self.client.login(username="homebuyer_alice", password="SecureAlicePassword123!")
        response = self.client.post(
            reverse("ai-underwrite-api", kwargs={"pk": self.application.pk}),
            content_type="application/json"
        )
        self.assertEqual(response.status_code, 403)

    def test_ai_underwrite_success_for_staff(self):
        self.client.login(username="staff_officer", password="SecureStaffPassword123!")
        mock_gemini_response = {
            "candidates": [{
                "content": {
                    "parts": [{
                        "text": json.dumps({
                            "risk_score": 85,
                            "risk_rating": "LOW",
                            "recommendation": "RECOMMEND APPROVAL",
                            "executive_summary": "Solid application.",
                            "affordability_analysis": "Manageable debt-to-income.",
                            "key_strengths": ["Good credit"],
                            "risk_factors": ["None notable"],
                            "required_stipulations": ["Standard valuation"]
                        })
                    }]
                }
            }]
        }
        with patch.object(GeminiAIService, "_call_gemini_api", return_value=mock_gemini_response):
            response = self.client.post(
                reverse("ai-underwrite-api", kwargs={"pk": self.application.pk}),
                content_type="application/json"
            )
            self.assertEqual(response.status_code, 200)
            data = response.json()
            self.assertEqual(data["status"], "success")
            self.assertEqual(data["assessment"]["risk_score"], 85)
            self.assertEqual(data["assessment"]["risk_rating"], "LOW")

    def test_ai_save_notes_api_staff(self):
        self.client.login(username="staff_officer", password="SecureStaffPassword123!")
        response = self.client.post(
            reverse("ai-save-notes-api", kwargs={"pk": self.application.pk}),
            data=json.dumps({"notes": "Verified source of deposit funds."}),
            content_type="application/json"
        )
        self.assertEqual(response.status_code, 200)
        self.application.refresh_from_db()
        self.assertIn("Verified source of deposit funds", self.application.staff_notes)

    def test_password_reset_views_render(self):
        res1 = self.client.get(reverse("password_reset"))
        self.assertEqual(res1.status_code, 200)
        self.assertContains(res1, "Password Reset")

        res2 = self.client.get(reverse("password_reset_done"))
        self.assertEqual(res2.status_code, 200)
        self.assertContains(res2, "Instructions Sent")
