from datetime import timedelta

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from traces.models import ApiToken

from ._helpers import make_user


class ProfileGetTest(TestCase):

    def setUp(self):
        self.user = make_user()
        self.client.login(username="alice", password="pass")

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
            self.assertIn(key, resp.context)


class ProfileGenerateTokenTest(TestCase):

    def setUp(self):
        self.user = make_user()
        self.client.login(username="alice", password="pass")

    def test_generate_token(self):
        resp = self.client.post(reverse("profile"), {"action": "generate_token"})
        self.assertEqual(resp.status_code, 302)
        self.assertTrue(ApiToken.objects.filter(user=self.user).exists())

    def test_regenerate_replaces_old_token(self):
        ApiToken.objects.create(
            user=self.user, expires_at=timezone.now() + timedelta(days=31),
        )
        self.client.post(reverse("profile"), {"action": "generate_token"})
        self.assertEqual(ApiToken.objects.filter(user=self.user).count(), 1)


class ProfileUpdateEmailTest(TestCase):

    def setUp(self):
        self.user = make_user()
        self.client.login(username="alice", password="pass")

    def test_update_email(self):
        resp = self.client.post(reverse("profile"), {
            "action": "update_email",
            "email": "new@example.com",
        })
        self.assertEqual(resp.status_code, 302)
        self.user.refresh_from_db()
        self.assertEqual(self.user.email, "new@example.com")

    def test_empty_email_shows_error(self):
        resp = self.client.post(reverse("profile"), {
            "action": "update_email",
            "email": "",
        })
        self.assertEqual(resp.status_code, 200)

    def test_invalid_email_shows_error(self):
        resp = self.client.post(reverse("profile"), {
            "action": "update_email",
            "email": "notanemail",
        })
        self.assertEqual(resp.status_code, 200)

    def test_duplicate_email_shows_error(self):
        other = make_user("bob")
        other.email = "taken@example.com"
        other.save()
        resp = self.client.post(reverse("profile"), {
            "action": "update_email",
            "email": "taken@example.com",
        })
        self.assertEqual(resp.status_code, 200)


class ProfileUpdateHomeLocationTest(TestCase):

    def setUp(self):
        self.user = make_user()
        self.client.login(username="alice", password="pass")

    def test_update_home_location(self):
        resp = self.client.post(reverse("profile"), {
            "action": "update_home_location",
            "lat": "48.85",
            "lng": "2.35",
        })
        self.assertEqual(resp.status_code, 302)

    def test_invalid_coords_ignored(self):
        resp = self.client.post(reverse("profile"), {
            "action": "update_home_location",
            "lat": "abc",
            "lng": "2.35",
        })
        self.assertEqual(resp.status_code, 302)
