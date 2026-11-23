from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from customers.models import CustomerProfile

User = get_user_model()


class CustomerManagementTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.password = "ComplexPass123!#"
        self.staff = User.objects.create_user(
            username="underwriter",
            email="underwriter@sunmortgages.com",
            password=self.password,
            role="STAFF",
            is_staff=True
        )
        self.customer = User.objects.create_user(
            username="john_doe",
            email="john@example.com",
            password=self.password,
            role="INDIVIDUAL"
        )
        self.profile = CustomerProfile.objects.create(
            user=self.customer,
            customer_type=CustomerProfile.CustomerType.INDIVIDUAL,
            address="10 Downing Street, London",
            notes="Confidential underwriting note"
        )

    def test_customer_data_access_restrictions(self):
        # Non-staff cannot view customer list
        self.client.login(username="john_doe", password=self.password)
        response = self.client.get(reverse("customer-list"))
        self.assertEqual(response.status_code, 302)  # Redirected away

    def test_staff_can_view_customer_list(self):
        self.client.login(username="underwriter", password=self.password)
        response = self.client.get(reverse("customer-list"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "john_doe")

    def test_customer_profile_editing(self):
        self.client.login(username="john_doe", password=self.password)
        response = self.client.post(reverse("my-profile"), {
            "address": "221B Baker Street, London",
            "company_name": ""
        }, follow=True)
        self.assertEqual(response.status_code, 200)
        self.profile.refresh_from_db()
        self.assertEqual(self.profile.address, "221B Baker Street, London")

    def test_customer_notes_not_exposed_to_customer(self):
        self.client.login(username="john_doe", password=self.password)
        response = self.client.get(reverse("my-profile"))
        self.assertNotContains(response, "Confidential underwriting note")
