from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import RequestFactory, TestCase
from django.urls import reverse

from schools.middleware import ErrorReporterMiddleware
from schools.models import SecurityLog


User = get_user_model()


class SuperuserSecurityTests(TestCase):
    def setUp(self):
        self.superuser = User.objects.create_user(
            email="super@example.com",
            password="StrongPass123!",
            role="superuser",
        )
        self.superuser.is_superuser = True
        self.superuser.save(update_fields=["is_superuser"])

    @patch("users.views.send_email")
    def test_superuser_login_requests_two_factor_code(self, mock_send_email):
        mock_send_email.return_value = True

        response = self.client.post(
            reverse("login"),
            {"username": "super@example.com", "password": "StrongPass123!"},
            follow=False,
        )

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse("superuser_two_factor"))
        self.assertTrue(
            SecurityLog.objects.filter(
                user=self.superuser,
                event_type="superuser_login_requested",
            ).exists()
        )

    def test_failed_superuser_login_is_logged(self):
        response = self.client.post(
            reverse("login"),
            {"username": "super@example.com", "password": "wrong-password"},
            follow=False,
        )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(
            SecurityLog.objects.filter(
                user=self.superuser,
                event_type="login_failed",
            ).exists()
        )

    @patch("schools.middleware.mail_admins")
    def test_server_errors_notify_superusers(self, mock_mail_admins):
        mock_mail_admins.return_value = True

        def raise_error(request):
            raise RuntimeError("template exploded")

        middleware = ErrorReporterMiddleware(raise_error)
        request = RequestFactory().get("/broken-page/")
        request.user = self.superuser

        response = middleware(request)

        self.assertEqual(response.status_code, 500)
        self.assertIn(b"page error", response.content.lower())
        self.assertTrue(mock_mail_admins.called)
