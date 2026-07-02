from django.test import TestCase

from brainet.templatetags.text_filters import register
from schools.views import normalize_storage_name


class SchoolLogoStorageTests(TestCase):
    def test_normalize_storage_name_handles_cloudinary_url(self):
        raw_name = "https://res.cloudinary.com/demo/image/upload/school_logos/logo_lidnjm"

        self.assertEqual(
            normalize_storage_name(raw_name),
            "school_logos/logo_lidnjm",
        )

    def test_get_school_logo_url_filter_is_registered(self):
        self.assertIn("get_school_logo_url", register.filters)
