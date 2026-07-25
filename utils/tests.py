import os
from unittest.mock import patch

from django.test import SimpleTestCase, override_settings

from utils.email_service import send_email


class EmailServiceTests(SimpleTestCase):
    @override_settings(
        EMAIL_BACKEND='django.core.mail.backends.smtp.EmailBackend',
        EMAIL_HOST='',
        EMAIL_HOST_USER='',
        EMAIL_HOST_PASSWORD='',
        DEFAULT_FROM_EMAIL='',
        DEBUG=False,
    )
    def test_send_email_without_configuration_reports_missing_setup(self):
        with patch.dict(os.environ, {'BREVO_API_KEY': ''}, clear=False):
            with self.assertRaisesRegex(RuntimeError, 'Email service is not configured'):
                send_email('test@example.com', 'Subject', 'Body', html=False)
