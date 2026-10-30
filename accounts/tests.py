
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

User = get_user_model()


class UserModelTests(TestCase):
    def test_default_role_is_resident(self):
        user = User.objects.create_user(
            username="resident_test",
            password="TestPass123!",
        )

        self.assertEqual(user.role, "RESIDENT")

    def test_user_string_representation(self):
        user = User.objects.create_user(
            username="manager_test",
            password="TestPass123!",
            role="MANAGEMENT",
        )

        self.assertEqual(
            str(user),
            "manager_test (Management)",
        )

    def test_phone_number_can_be_blank(self):
        user = User.objects.create_user(
            username="phone_test",
            password="TestPass123!",
        )

        self.assertEqual(user.phone_number, "")

    def test_password_is_hashed(self):
        user = User.objects.create_user(
            username="password_test",
            password="TestPass123!",
        )

        self.assertNotEqual(user.password, "TestPass123!")
        self.assertTrue(user.check_password("TestPass123!"))


class AuthenticationViewTests(TestCase):
    def test_dashboard_redirects_anonymous_user(self):
        response = self.client.get(reverse("dashboard"))

        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse("login"), response.url)

    def test_authenticated_user_can_access_dashboard(self):
        user = User.objects.create_user(
            username="dashboard_test",
            password="TestPass123!",
            role="RESIDENT",
        )
        self.client.force_login(user)

        response = self.client.get(reverse("dashboard"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["user"], user)
        self.assertEqual(response.context["role"], "RESIDENT")

    def test_login_page_is_available(self):
        response = self.client.get(reverse("login"))

        self.assertEqual(response.status_code, 200)

    def test_valid_credentials_can_log_in(self):
        User.objects.create_user(
            username="login_test",
            password="TestPass123!",
        )

        response = self.client.post(
            reverse("login"),
            {
                "username": "login_test",
                "password": "TestPass123!",
            },
        )

        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.wsgi_request.user.is_authenticated)

    def test_invalid_credentials_do_not_log_in(self):
        User.objects.create_user(
            username="invalid_login_test",
            password="TestPass123!",
        )

        response = self.client.post(
            reverse("login"),
            {
                "username": "invalid_login_test",
                "password": "WrongPassword!",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.wsgi_request.user.is_authenticated)

    def test_logout_requires_post(self):
        user = User.objects.create_user(
            username="logout_test",
            password="TestPass123!",
        )
        self.client.force_login(user)

        response = self.client.get(reverse("logout"))

        self.assertEqual(response.status_code, 405)

    def test_logout_post_logs_user_out(self):
        user = User.objects.create_user(
            username="logout_post_test",
            password="TestPass123!",
        )
        self.client.force_login(user)

        response = self.client.post(reverse("logout"))

        self.assertEqual(response.status_code, 302)
        self.assertNotIn(
            "_auth_user_id",
            self.client.session,
        )
