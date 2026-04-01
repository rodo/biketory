from django.test import TestCase
from django.urls import reverse

from ._helpers import make_entry, make_user, make_zone


class ZoneLeadersAuthTest(TestCase):

    def test_requires_login(self):
        resp = self.client.get(reverse("zone_leaders"))
        self.assertEqual(resp.status_code, 302)

    def test_logged_in_returns_200(self):
        self.client.force_login(make_user())
        resp = self.client.get(reverse("zone_leaders"))
        self.assertEqual(resp.status_code, 200)


class ZoneLeadersContentTest(TestCase):

    @classmethod
    def setUpTestData(cls):
        cls.user = make_user()
        cls.zone_active = make_zone(code="FR", name="France", active=True)
        cls.zone_inactive = make_zone(code="DE", name="Germany", active=False)
        make_entry(cls.zone_active, user_id=cls.user.pk, username="alice",
                   conquered=10, acquired=8, rank_conquered=1, rank_acquired=1)

    def setUp(self):
        self.client.force_login(self.user)

    def test_only_active_zones_shown(self):
        resp = self.client.get(reverse("zone_leaders"))
        zone_data = resp.context["zone_data"]
        zone_codes = [item["zone"].code for item in zone_data]
        self.assertIn("FR", zone_codes)
        self.assertNotIn("DE", zone_codes)

    def test_leaders_populated(self):
        resp = self.client.get(reverse("zone_leaders"))
        zone_data = resp.context["zone_data"]
        fr_item = next(item for item in zone_data if item["zone"].code == "FR")
        self.assertEqual(len(fr_item["leaders"]), 1)
        self.assertEqual(fr_item["leaders"][0]["username"], "alice")

    def test_user_rank_present(self):
        resp = self.client.get(reverse("zone_leaders"))
        zone_data = resp.context["zone_data"]
        fr_item = next(item for item in zone_data if item["zone"].code == "FR")
        self.assertIsNotNone(fr_item["user_rank"])
        self.assertEqual(fr_item["user_rank"]["rank"], 1)

    def test_type_acquired(self):
        resp = self.client.get(reverse("zone_leaders") + "?type=acquired")
        self.assertEqual(resp.context["lb_type"], "acquired")

    def test_type_defaults_to_conquered(self):
        resp = self.client.get(reverse("zone_leaders"))
        self.assertEqual(resp.context["lb_type"], "conquered")

    def test_invalid_type_falls_back(self):
        resp = self.client.get(reverse("zone_leaders") + "?type=invalid")
        self.assertEqual(resp.context["lb_type"], "conquered")

    def test_top_n_limit(self):
        """Only top 3 leaders per zone."""
        zone = make_zone(code="ES", name="Spain", active=True)
        for i in range(5):
            make_entry(zone, user_id=100 + i, username=f"user{i}",
                       conquered=50 - i, acquired=40 - i,
                       rank_conquered=i + 1, rank_acquired=i + 1)
        resp = self.client.get(reverse("zone_leaders"))
        zone_data = resp.context["zone_data"]
        es_item = next(item for item in zone_data if item["zone"].code == "ES")
        self.assertEqual(len(es_item["leaders"]), 3)
