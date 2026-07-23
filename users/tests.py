from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import RequestFactory, TestCase
from django.urls import reverse

from users.views import _get_trusted_device_key

from schools.middleware import ErrorReporterMiddleware
from schools.models import SecurityLog
from schools.views import get_pending_verification_items


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
            follow=True,
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Superuser verification")
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
            follow=True,
        )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(
            SecurityLog.objects.filter(
                user=self.superuser,
                event_type="login_failed",
            ).exists()
        )

    def test_superuser_login_can_trust_device_and_skip_verification(self):
        response = self.client.post(
            reverse("login"),
            {
                "username": "super@example.com",
                "password": "StrongPass123!",
                "trust_device": "on",
            },
            follow=True,
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.request['PATH_INFO'], reverse("superuser_dashboard"))
        self.assertNotIn("pending_superuser_login_user_id", self.client.session)

    def test_pending_verification_items_exclude_students(self):
        student_user = User.objects.create_user(
            email="student.pending@example.com",
            password="StrongPass123!",
            role="student",
        )
        student_user.email_verified = False
        student_user.save(update_fields=["email_verified"])

        items = get_pending_verification_items()

        self.assertFalse(any(item["email"] == student_user.email for item in items))

    @patch("users.views.send_email", side_effect=RuntimeError("smtp unavailable"))
    def test_superuser_login_continues_when_email_delivery_fails(self, _mock_send_email):
        response = self.client.post(
            reverse("login"),
            {"username": "super@example.com", "password": "StrongPass123!"},
            follow=True,
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Superuser verification")
        self.assertIn("pending_superuser_login_code", self.client.session)

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
