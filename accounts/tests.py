from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from customers.models import CustomerProfile

User = get_user_model()


class AuthenticationTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user_password = "SecurePassword123!@"
        self.staff_user = User.objects.create_user(
            username="staff_officer",
            email="staff@sunmortgages.com",
            password=self.user_password,
            role="STAFF",
            is_staff=True
        )
        self.customer_user = User.objects.create_user(
            username="individual_borrower",
            email="borrower@example.com",
            password=self.user_password,
            role="INDIVIDUAL"
        )

    def test_user_registration_individual(self):
        response = self.client.post(reverse("register"), {
            "username": "new_applicant",
            "email": "applicant@example.com",
            "phone_number": "07700900999",
            "role": "INDIVIDUAL",
            "password1": "StrongPass123!@#",
            "password2": "StrongPass123!@#",
        }, follow=True)
        self.assertEqual(response.status_code, 200)
        user = User.objects.get(username="new_applicant")
        self.assertEqual(user.role, "INDIVIDUAL")
        self.assertTrue(CustomerProfile.objects.filter(user=user).exists())

    def test_public_registration_cannot_create_staff(self):
        # Attempt to inject STAFF role in registration form
        response = self.client.post(reverse("register"), {
            "username": "hacker_staff",
            "email": "hacker@example.com",
            "phone_number": "07700900111",
            "role": "STAFF",
            "password1": "StrongPass123!@#",
            "password2": "StrongPass123!@#",
        })
        self.assertFalse(User.objects.filter(username="hacker_staff").exists())
        form = response.context["form"]
        self.assertFormError(form, "role", "Select a valid choice. STAFF is not one of the available choices.")

    def test_user_login_success(self):
        response = self.client.post(reverse("login"), {
            "username": "individual_borrower",
            "password": self.user_password
        }, follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context["user"].is_authenticated)

    def test_user_login_invalid_credentials(self):
        response = self.client.post(reverse("login"), {
            "username": "individual_borrower",
            "password": "WrongPassword999"
        })
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.context["user"].is_authenticated)

    def test_user_logout(self):
        self.client.login(username="individual_borrower", password=self.user_password)
        response = self.client.post(reverse("logout"), follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.context["user"].is_authenticated)
