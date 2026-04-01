from datetime import timedelta

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from traces.models import Subscription

from ._helpers import make_entry, make_user, make_zone


class ZoneLeaderboardAuthTest(TestCase):

    def test_requires_login(self):
        zone = make_zone(code="FR", active=True)
        resp = self.client.get(reverse("zone_leaderboard", args=[zone.code]))
        self.assertEqual(resp.status_code, 302)

    def test_non_premium_redirects(self):
        user = make_user()
        self.client.force_login(user)
        zone = make_zone(code="FR", active=True)
        resp = self.client.get(reverse("zone_leaderboard", args=[zone.code]))
        self.assertEqual(resp.status_code, 302)
        self.assertIn("premium", resp.url)

    def test_premium_returns_200(self):
        user = make_user()
        today = timezone.now().date()
        Subscription.objects.create(
            user=user,
            start_date=today - timedelta(days=1),
            end_date=today + timedelta(days=30),
        )
        self.client.force_login(user)
        zone = make_zone(code="FR", active=True)
        resp = self.client.get(reverse("zone_leaderboard", args=[zone.code]))
        self.assertEqual(resp.status_code, 200)


class ZoneLeaderboardActiveFilterTest(TestCase):

    @classmethod
    def setUpTestData(cls):
        cls.user = make_user()
        today = timezone.now().date()
        Subscription.objects.create(
            user=cls.user,
            start_date=today - timedelta(days=1),
            end_date=today + timedelta(days=30),
        )
        cls.zone_inactive = make_zone(code="DE", active=False)

    def setUp(self):
        self.client.force_login(self.user)

    def test_inactive_zone_returns_404(self):
        resp = self.client.get(
            reverse("zone_leaderboard", args=[self.zone_inactive.code])
        )
        self.assertEqual(resp.status_code, 404)


class ZoneLeaderboardContentTest(TestCase):

    @classmethod
    def setUpTestData(cls):
        cls.user = make_user()
        today = timezone.now().date()
        Subscription.objects.create(
            user=cls.user,
            start_date=today - timedelta(days=1),
            end_date=today + timedelta(days=30),
        )
        cls.zone = make_zone(code="FR", name="France", admin_level=2, active=True)
        make_entry(cls.zone, user_id=cls.user.pk, username="alice",
                   conquered=10, acquired=8, rank_conquered=1, rank_acquired=1)
        make_entry(cls.zone, user_id=999, username="bob",
                   conquered=5, acquired=3, rank_conquered=2, rank_acquired=2)

    def setUp(self):
        self.client.force_login(self.user)

    def test_entries_in_context(self):
        resp = self.client.get(reverse("zone_leaderboard", args=["FR"]))
        self.assertEqual(len(resp.context["entries"]), 2)

    def test_user_entry_in_context(self):
        resp = self.client.get(reverse("zone_leaderboard", args=["FR"]))
        self.assertIsNotNone(resp.context["user_entry"])
        self.assertEqual(resp.context["user_entry"]["rank"], 1)

    def test_type_acquired(self):
        url = reverse("zone_leaderboard", args=["FR"]) + "?type=acquired"
        resp = self.client.get(url)
        self.assertEqual(resp.context["lb_type"], "acquired")

    def test_invalid_type_falls_back(self):
        url = reverse("zone_leaderboard", args=["FR"]) + "?type=bad"
        resp = self.client.get(url)
        self.assertEqual(resp.context["lb_type"], "conquered")

    def test_zone_in_context(self):
        resp = self.client.get(reverse("zone_leaderboard", args=["FR"]))
        self.assertEqual(resp.context["zone"].code, "FR")

    def test_ajax_returns_json(self):
        resp = self.client.get(
            reverse("zone_leaderboard", args=["FR"]),
            HTTP_X_REQUESTED_WITH="XMLHttpRequest",
        )
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIn("entries", data)
        self.assertIn("has_more", data)

    def test_sidebar_only_active_countries(self):
        make_zone(code="DE", name="Germany", admin_level=2, active=False)
        make_zone(code="ES", name="Spain", admin_level=2, active=True)
        resp = self.client.get(reverse("zone_leaderboard", args=["FR"]))
        country_codes = [z.code for z in resp.context["zone_countries"]]
        self.assertIn("FR", country_codes)
        self.assertIn("ES", country_codes)
        self.assertNotIn("DE", country_codes)

    def test_sidebar_only_active_children(self):
        make_zone(code="IDF", admin_level=4, active=True, parent=self.zone)
        make_zone(code="BRE", admin_level=4, active=False, parent=self.zone)
        resp = self.client.get(reverse("zone_leaderboard", args=["FR"]))
        child_codes = [z.code for z in resp.context["zone_children"]]
        self.assertIn("IDF", child_codes)
        self.assertNotIn("BRE", child_codes)
