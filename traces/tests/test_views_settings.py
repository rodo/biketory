from datetime import timedelta

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from traces.models import ApiToken, Subscription

from ._helpers import make_user


class SettingsGenerateTokenTest(TestCase):

    def setUp(self):
        self.user = make_user()
        self.client.force_login(self.user)
        today = timezone.now().date()
        Subscription.objects.create(
            user=self.user,
            start_date=today - timedelta(days=1),
            end_date=today + timedelta(days=30),
        )

    def test_generate_token(self):
        resp = self.client.post(reverse("settings"), {"action": "generate_token"})
        self.assertEqual(resp.status_code, 302)
        self.assertTrue(ApiToken.objects.filter(user=self.user).exists())

    def test_regenerate_replaces_old_token(self):
        ApiToken.objects.create(
            user=self.user, expires_at=timezone.now() + timedelta(days=31),
        )
        self.client.post(reverse("settings"), {"action": "generate_token"})
        self.assertEqual(ApiToken.objects.filter(user=self.user).count(), 1)


class SettingsUpdateNameTest(TestCase):

    def setUp(self):
        self.user = make_user()
        self.client.force_login(self.user)

    def test_update_first_and_last_name(self):
        resp = self.client.post(reverse("settings"), {
            "action": "update_name",
            "first_name": "Jean",
            "last_name": "Dupont",
        })
        self.assertEqual(resp.status_code, 200)
        self.user.refresh_from_db()
        self.assertEqual(self.user.first_name, "Jean")
        self.assertEqual(self.user.last_name, "Dupont")
        self.assertEqual(resp.context["success_field"], "name")

    def test_first_name_too_long_shows_error(self):
        resp = self.client.post(reverse("settings"), {
            "action": "update_name",
            "first_name": "a" * 151,
            "last_name": "Dupont",
        })
        self.assertEqual(resp.status_code, 200)
        self.assertIsNotNone(resp.context["name_error"])
        self.user.refresh_from_db()
        self.assertEqual(self.user.first_name, "")

    def test_last_name_too_long_shows_error(self):
        resp = self.client.post(reverse("settings"), {
            "action": "update_name",
            "first_name": "Jean",
            "last_name": "b" * 151,
        })
        self.assertEqual(resp.status_code, 200)
        self.assertIsNotNone(resp.context["name_error"])
        self.user.refresh_from_db()
        self.assertEqual(self.user.last_name, "")


class SettingsUpdateUsernameTest(TestCase):

    def setUp(self):
        self.user = make_user()
        self.client.force_login(self.user)

    def test_update_username(self):
        resp = self.client.post(reverse("settings"), {
            "action": "update_username",
            "username": "new_name",
        })
        self.assertEqual(resp.status_code, 200)
        self.user.refresh_from_db()
        self.assertEqual(self.user.username, "new_name")
        self.assertEqual(resp.context["success_field"], "username")

    def test_empty_username_shows_error(self):
        resp = self.client.post(reverse("settings"), {
            "action": "update_username",
            "username": "",
        })
        self.assertEqual(resp.status_code, 200)

    def test_too_long_username_shows_error(self):
        resp = self.client.post(reverse("settings"), {
            "action": "update_username",
            "username": "a" * 151,
        })
        self.assertEqual(resp.status_code, 200)

    def test_invalid_chars_shows_error(self):
        resp = self.client.post(reverse("settings"), {
            "action": "update_username",
            "username": "bad name!",
        })
        self.assertEqual(resp.status_code, 200)

    def test_duplicate_username_shows_error(self):
        other = make_user("bob")
        resp = self.client.post(reverse("settings"), {
            "action": "update_username",
            "username": other.username,
        })
        self.assertEqual(resp.status_code, 200)


class SettingsUpdateEmailTest(TestCase):

    def setUp(self):
        self.user = make_user()
        self.client.force_login(self.user)

    def test_update_email(self):
        resp = self.client.post(reverse("settings"), {
            "action": "update_email",
            "email": "new@example.com",
        })
        self.assertEqual(resp.status_code, 200)
        self.user.refresh_from_db()
        self.assertEqual(self.user.email, "new@example.com")
        self.assertEqual(resp.context["success_field"], "email")

    def test_empty_email_shows_error(self):
        resp = self.client.post(reverse("settings"), {
            "action": "update_email",
            "email": "",
        })
        self.assertEqual(resp.status_code, 200)

    def test_invalid_email_shows_error(self):
        resp = self.client.post(reverse("settings"), {
            "action": "update_email",
            "email": "notanemail",
        })
        self.assertEqual(resp.status_code, 200)

    def test_duplicate_email_shows_error(self):
        other = make_user("bob")
        other.email = "taken@example.com"
        other.save()
        resp = self.client.post(reverse("settings"), {
            "action": "update_email",
            "email": "taken@example.com",
        })
        self.assertEqual(resp.status_code, 200)


class SettingsUpdateHomeLocationTest(TestCase):

    def setUp(self):
        self.user = make_user()
        self.client.force_login(self.user)

    def test_update_home_location(self):
        resp = self.client.post(reverse("settings"), {
            "action": "update_home_location",
            "lat": "48.85",
            "lng": "2.35",
        })
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.context["success_field"], "home_location")

    def test_invalid_coords_ignored(self):
        resp = self.client.post(reverse("settings"), {
            "action": "update_home_location",
            "lat": "abc",
            "lng": "2.35",
        })
        self.assertEqual(resp.status_code, 200)
        self.assertIsNone(resp.context["success_field"])
