from django.test import TestCase

from brainet.templatetags.text_filters import register
from schools.views import assign_competition_ranks


class SchoolLogoStorageTests(TestCase):
    def test_get_school_logo_url_filter_is_registered(self):
        self.assertIn("get_school_logo_url", register.filters)

    def test_assign_competition_ranks_skips_tied_positions(self):
        rows = [
            {"score": 100},
            {"score": 100},
            {"score": 90},
            {"score": 80},
            {"score": 80},
        ]

        ranked_rows = assign_competition_ranks(rows, lambda row: row["score"], rank_attr="position")

        self.assertEqual([row["position"] for row in ranked_rows], [1, 1, 3, 4, 4])
