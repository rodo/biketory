from django.test import TestCase
from django.urls import reverse

from traces.base62 import uuid_to_base62
from traces.models import UserSurfaceStats

from ._helpers import make_user


class SharedProfileViewTest(TestCase):

    def setUp(self):
        self.user = make_user()
        self.stats, _ = UserSurfaceStats.objects.get_or_create(user=self.user)
        self.code = uuid_to_base62(self.stats.secret_uuid)

    def test_valid_code_returns_200(self):
        resp = self.client.get(reverse("shared_profile", args=[self.code]))
        self.assertEqual(resp.status_code, 200)

    def test_invalid_code_returns_404(self):
        resp = self.client.get(reverse("shared_profile", args=["!!invalid!!"]))
        self.assertEqual(resp.status_code, 404)

    def test_unknown_uuid_returns_404(self):
        resp = self.client.get(reverse("shared_profile", args=["1a2b3c4d5e6f7g8h9i0jkl"]))
        self.assertEqual(resp.status_code, 404)

    def test_context_contains_username(self):
        resp = self.client.get(reverse("shared_profile", args=[self.code]))
        self.assertEqual(resp.context["username"], self.user.username)

    def test_context_contains_stats(self):
        resp = self.client.get(reverse("shared_profile", args=[self.code]))
        self.assertIn("hexagons_count", resp.context)
        self.assertIn("total_points", resp.context)
        self.assertIn("traces_count", resp.context)
        self.assertIn("hexagons_geojson", resp.context)

    def test_public_no_login_required(self):
        self.client.logout()
        resp = self.client.get(reverse("shared_profile", args=[self.code]))
        self.assertEqual(resp.status_code, 200)
