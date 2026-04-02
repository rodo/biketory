from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from statistics.models import LeaderboardEntry

from ._helpers import make_user


def _make_entry(user_id, username, conquered, acquired,
                rank_conquered, rank_acquired, is_premium=False,
                total_points=0, rank_points=1):
    return LeaderboardEntry.objects.create(
        user_id=user_id,
        username=username,
        is_premium=is_premium,
        hexagons_conquered=conquered,
        hexagons_acquired=acquired,
        total_points=total_points,
        rank_conquered=rank_conquered,
        rank_acquired=rank_acquired,
        rank_points=rank_points,
        computed_at=timezone.now(),
    )


class LeaderboardAuthTest(TestCase):

    def test_requires_login(self):
        resp = self.client.get(reverse("leaderboard"))
        self.assertEqual(resp.status_code, 302)

    def test_logged_in_returns_200(self):
        self.client.force_login(make_user())
        resp = self.client.get(reverse("leaderboard"))
        self.assertEqual(resp.status_code, 200)


class LeaderboardTypeTest(TestCase):

    @classmethod
    def setUpTestData(cls):
        cls.user = make_user()

    def setUp(self):
        self.client.force_login(self.user)

    def test_defaults_to_points(self):
        resp = self.client.get(reverse("leaderboard"))
        self.assertEqual(resp.context["lb_type"], "points")

    def test_type_conquered(self):
        resp = self.client.get(reverse("leaderboard") + "?type=conquered")
        self.assertEqual(resp.context["lb_type"], "conquered")

    def test_type_acquired(self):
        resp = self.client.get(reverse("leaderboard") + "?type=acquired")
        self.assertEqual(resp.context["lb_type"], "acquired")

    def test_invalid_type_falls_back(self):
        resp = self.client.get(reverse("leaderboard") + "?type=invalid")
        self.assertEqual(resp.context["lb_type"], "points")


class LeaderboardEntriesTest(TestCase):

    @classmethod
    def setUpTestData(cls):
        cls.user = make_user()
        _make_entry(cls.user.pk, "alice", 50, 40, 1, 1,
                    total_points=120, rank_points=1)
        _make_entry(999, "bob", 30, 20, 2, 2,
                    total_points=60, rank_points=2)

    def setUp(self):
        self.client.force_login(self.user)

    def test_entries_in_context(self):
        resp = self.client.get(reverse("leaderboard"))
        self.assertEqual(len(resp.context["entries"]), 2)

    def test_current_user_flagged(self):
        resp = self.client.get(reverse("leaderboard"))
        alice = next(e for e in resp.context["entries"] if e["username"] == "alice")
        bob = next(e for e in resp.context["entries"] if e["username"] == "bob")
        self.assertTrue(alice["is_current_user"])
        self.assertFalse(bob["is_current_user"])

    def test_user_entry_in_context(self):
        resp = self.client.get(reverse("leaderboard"))
        self.assertIsNotNone(resp.context["user_entry"])
        self.assertEqual(resp.context["user_entry"]["rank"], 1)
        self.assertEqual(resp.context["user_entry"]["count"], 120)

    def test_conquered_uses_conquered_fields(self):
        resp = self.client.get(reverse("leaderboard") + "?type=conquered")
        self.assertEqual(resp.context["user_entry"]["count"], 50)

    def test_acquired_uses_acquired_fields(self):
        resp = self.client.get(reverse("leaderboard") + "?type=acquired")
        self.assertEqual(resp.context["user_entry"]["count"], 40)

    def test_computed_at_in_context(self):
        resp = self.client.get(reverse("leaderboard"))
        self.assertIsNotNone(resp.context["computed_at"])


class LeaderboardEmptyTest(TestCase):

    @classmethod
    def setUpTestData(cls):
        cls.user = make_user()

    def setUp(self):
        self.client.force_login(self.user)

    def test_no_entries(self):
        resp = self.client.get(reverse("leaderboard"))
        self.assertEqual(resp.context["entries"], [])
        self.assertIsNone(resp.context["user_entry"])
        self.assertIsNone(resp.context["computed_at"])


class LeaderboardUserNotInTopTest(TestCase):
    """User exists in leaderboard but is not in the current page."""

    @classmethod
    def setUpTestData(cls):
        cls.user = make_user()
        # Create 21 entries ranked 1-21 so the first page has 20
        for i in range(21):
            _make_entry(
                user_id=1000 + i,
                username=f"user{i:03d}",
                conquered=100 - i,
                acquired=80 - i,
                rank_conquered=i + 1,
                rank_acquired=i + 1,
                total_points=200 - i,
                rank_points=i + 1,
            )
        # Current user at rank 25 (not in first page)
        _make_entry(
            cls.user.pk, "alice", 10, 5,
            rank_conquered=25, rank_acquired=25,
            total_points=20, rank_points=25,
        )

    def setUp(self):
        self.client.force_login(self.user)

    def test_has_more_true(self):
        resp = self.client.get(reverse("leaderboard"))
        self.assertTrue(resp.context["has_more"])

    def test_user_neighborhood_present(self):
        resp = self.client.get(reverse("leaderboard"))
        self.assertIsNotNone(resp.context["user_neighborhood"])

    def test_user_in_neighborhood(self):
        resp = self.client.get(reverse("leaderboard"))
        neighborhood = resp.context["user_neighborhood"]
        self.assertTrue(any(e["is_current_user"] for e in neighborhood))


class LeaderboardUserInTopTest(TestCase):
    """User is visible in the current page — no neighborhood needed."""

    @classmethod
    def setUpTestData(cls):
        cls.user = make_user()
        _make_entry(cls.user.pk, "alice", 50, 40, 1, 1,
                    total_points=120, rank_points=1)

    def setUp(self):
        self.client.force_login(self.user)

    def test_user_neighborhood_none(self):
        resp = self.client.get(reverse("leaderboard"))
        self.assertIsNone(resp.context["user_neighborhood"])


class LeaderboardAjaxTest(TestCase):

    @classmethod
    def setUpTestData(cls):
        cls.user = make_user()
        _make_entry(cls.user.pk, "alice", 50, 40, 1, 1,
                    total_points=120, rank_points=1)

    def setUp(self):
        self.client.force_login(self.user)

    def test_ajax_returns_json(self):
        resp = self.client.get(
            reverse("leaderboard"),
            headers={"x-requested-with": "XMLHttpRequest"}
        )
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIn("entries", data)
        self.assertIn("has_more", data)
        self.assertIn("user_entry", data)
        self.assertIn("user_neighborhood", data)

    def test_ajax_with_offset(self):
        resp = self.client.get(
            reverse("leaderboard") + "?offset=1",
            headers={"x-requested-with": "XMLHttpRequest"}
        )
        data = resp.json()
        self.assertEqual(len(data["entries"]), 0)
        self.assertFalse(data["has_more"])


class LeaderboardPaginationTest(TestCase):

    @classmethod
    def setUpTestData(cls):
        cls.user = make_user()
        for i in range(25):
            _make_entry(
                user_id=1000 + i,
                username=f"user{i:03d}",
                conquered=100 - i,
                acquired=80 - i,
                rank_conquered=i + 1,
                rank_acquired=i + 1,
                total_points=200 - i,
                rank_points=i + 1,
            )

    def setUp(self):
        self.client.force_login(self.user)

    def test_first_page_has_20(self):
        resp = self.client.get(reverse("leaderboard"))
        self.assertEqual(len(resp.context["entries"]), 20)
        self.assertTrue(resp.context["has_more"])

    def test_second_page(self):
        resp = self.client.get(
            reverse("leaderboard") + "?offset=20",
            headers={"x-requested-with": "XMLHttpRequest"}
        )
        data = resp.json()
        self.assertEqual(len(data["entries"]), 5)
        self.assertFalse(data["has_more"])


class LeaderboardZoneCountriesTest(TestCase):

    @classmethod
    def setUpTestData(cls):
        cls.user = make_user()

    def setUp(self):
        self.client.force_login(self.user)

    def test_zone_countries_in_context(self):
        resp = self.client.get(reverse("leaderboard"))
        self.assertIn("zone_countries", resp.context)

    def test_only_active_countries(self):
        from geozones.tests._helpers import make_zone
        make_zone(code="FR", admin_level=2, active=True)
        make_zone(code="DE", admin_level=2, active=False)
        resp = self.client.get(reverse("leaderboard"))
        codes = [z.code for z in resp.context["zone_countries"]]
        self.assertIn("FR", codes)
        self.assertNotIn("DE", codes)
