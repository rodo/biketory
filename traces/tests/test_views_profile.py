from django.test import TestCase
from django.urls import reverse

from ._helpers import make_user


class DashboardGetTest(TestCase):

    def setUp(self):
        self.user = make_user()
        self.client.force_login(self.user)

    def test_get_returns_200(self):
        resp = self.client.get(reverse("dashboard"))
        self.assertEqual(resp.status_code, 200)

    def test_requires_login(self):
        self.client.logout()
        resp = self.client.get(reverse("dashboard"))
        self.assertEqual(resp.status_code, 302)

    def test_context_contains_expected_keys(self):
        resp = self.client.get(reverse("dashboard"))
        for key in ("traces_count", "hexagons_acquired", "total_points",
                     "rank_points", "streak_daily", "distance_total",
                     "distance_monthly", "recent_badges", "friend_activity"):
            self.assertIn(key, resp.context, f"Missing context key: {key}")

    def test_profile_url_redirects_to_dashboard(self):
        """Legacy /profile/ still works via the 'profile' URL name."""
        resp = self.client.get(reverse("profile"))
        self.assertEqual(resp.status_code, 200)
