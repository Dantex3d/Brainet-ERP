from django.test import TestCase

from brainet.templatetags.text_filters import register


class SchoolLogoStorageTests(TestCase):
    def test_get_school_logo_url_filter_is_registered(self):
        self.assertIn("get_school_logo_url", register.filters)
