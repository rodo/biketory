from django.test import TestCase
from django.urls import reverse

from ._helpers import make_user


class ProfileGetTest(TestCase):

    def setUp(self):
        self.user = make_user()
        self.client.force_login(self.user)

    def test_get_returns_200(self):
        resp = self.client.get(reverse("profile"))
        self.assertEqual(resp.status_code, 200)

    def test_requires_login(self):
        self.client.logout()
        resp = self.client.get(reverse("profile"))
        self.assertEqual(resp.status_code, 302)

    def test_context_contains_expected_keys(self):
        resp = self.client.get(reverse("profile"))
        for key in ("traces_count", "hexagons_count", "total_points",
                     "hexagons_geojson", "secret_uuid", "friends_count"):
            self.assertIn(key, resp.context, f"Missing context key: {key}")
