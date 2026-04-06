from django.contrib.gis.geos import MultiPolygon, Polygon
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from statistics.models import ClusterLeaderboardEntry

from ._helpers import make_user


def _make_cluster_entry(user_id, username, hex_count, area_m2, rank,
                        is_premium=False, geom=None):
    return ClusterLeaderboardEntry.objects.create(
        user_id=user_id,
        username=username,
        is_premium=is_premium,
        largest_cluster_hex_count=hex_count,
        largest_cluster_area_m2=area_m2,
        largest_cluster_geom=geom,
        rank=rank,
        computed_at=timezone.now(),
    )


def _small_geom():
    poly = Polygon([
        (2.30, 48.80), (2.31, 48.80), (2.31, 48.81),
        (2.30, 48.81), (2.30, 48.80),
    ])
    return MultiPolygon(poly, srid=4326)


class ClusterLeaderboardAuthTest(TestCase):

    def test_requires_login(self):
        resp = self.client.get(reverse("cluster_leaderboard"))
        self.assertEqual(resp.status_code, 302)

    def test_logged_in_returns_200(self):
        self.client.force_login(make_user())
        resp = self.client.get(reverse("cluster_leaderboard"))
        self.assertEqual(resp.status_code, 200)


class ClusterLeaderboardEntriesTest(TestCase):

    @classmethod
    def setUpTestData(cls):
        cls.user = make_user()
        _make_cluster_entry(cls.user.pk, "alice", 50, 500_000, 1,
                            geom=_small_geom())
        _make_cluster_entry(999, "bob", 30, 300_000, 2)

    def setUp(self):
        self.client.force_login(self.user)

    def test_entries_in_context(self):
        resp = self.client.get(reverse("cluster_leaderboard"))
        self.assertEqual(len(resp.context["entries"]), 2)

    def test_current_user_flagged(self):
        resp = self.client.get(reverse("cluster_leaderboard"))
        alice = next(e for e in resp.context["entries"] if e["username"] == "alice")
        bob = next(e for e in resp.context["entries"] if e["username"] == "bob")
        self.assertTrue(alice["is_current_user"])
        self.assertFalse(bob["is_current_user"])

    def test_user_entry_in_context(self):
        resp = self.client.get(reverse("cluster_leaderboard"))
        ue = resp.context["user_entry"]
        self.assertIsNotNone(ue)
        self.assertEqual(ue["rank"], 1)
        self.assertEqual(ue["hex_count"], 50)

    def test_area_in_km2(self):
        resp = self.client.get(reverse("cluster_leaderboard"))
        ue = resp.context["user_entry"]
        self.assertAlmostEqual(ue["area_km2"], 0.5)

    def test_computed_at_in_context(self):
        resp = self.client.get(reverse("cluster_leaderboard"))
        self.assertIsNotNone(resp.context["computed_at"])

    def test_entry_fields(self):
        resp = self.client.get(reverse("cluster_leaderboard"))
        entry = resp.context["entries"][0]
        self.assertIn("rank", entry)
        self.assertIn("username", entry)
        self.assertIn("hex_count", entry)
        self.assertIn("area_km2", entry)
        self.assertIn("is_premium", entry)
        self.assertIn("is_current_user", entry)


class ClusterLeaderboardEmptyTest(TestCase):

    @classmethod
    def setUpTestData(cls):
        cls.user = make_user()

    def setUp(self):
        self.client.force_login(self.user)

    def test_no_entries(self):
        resp = self.client.get(reverse("cluster_leaderboard"))
        self.assertEqual(resp.context["entries"], [])
        self.assertIsNone(resp.context["user_entry"])
        self.assertIsNone(resp.context["computed_at"])


class ClusterLeaderboardTopEntriesTest(TestCase):

    @classmethod
    def setUpTestData(cls):
        cls.user = make_user()
        cls.geom = _small_geom()
        _make_cluster_entry(cls.user.pk, "alice", 50, 500_000, 1,
                            geom=cls.geom)
        _make_cluster_entry(998, "bob", 30, 300_000, 2, geom=cls.geom)
        _make_cluster_entry(999, "charlie", 20, 200_000, 3, geom=cls.geom)
        _make_cluster_entry(1000, "dave", 10, 100_000, 4)

    def setUp(self):
        self.client.force_login(self.user)

    def test_top_entries_has_3(self):
        resp = self.client.get(reverse("cluster_leaderboard"))
        self.assertEqual(len(resp.context["top_entries"]), 3)

    def test_top_entries_have_geojson(self):
        resp = self.client.get(reverse("cluster_leaderboard"))
        for t in resp.context["top_entries"]:
            self.assertIn("geojson", t)
            self.assertIn("username", t)
            self.assertIn("rank", t)

    def test_top_entries_without_geom(self):
        """Entry without geometry should have null geojson."""
        ClusterLeaderboardEntry.objects.filter(rank__lte=3).delete()
        _make_cluster_entry(2000, "eve", 60, 600_000, 1)
        resp = self.client.get(reverse("cluster_leaderboard"))
        top = resp.context["top_entries"]
        self.assertEqual(len(top), 1)
        self.assertEqual(top[0]["geojson"], "null")


class ClusterLeaderboardUserNotInTopTest(TestCase):

    @classmethod
    def setUpTestData(cls):
        cls.user = make_user()
        for i in range(21):
            _make_cluster_entry(
                user_id=1000 + i,
                username=f"user{i:03d}",
                hex_count=100 - i,
                area_m2=(100 - i) * 10_000,
                rank=i + 1,
            )
        _make_cluster_entry(cls.user.pk, "alice", 5, 50_000, 25)

    def setUp(self):
        self.client.force_login(self.user)

    def test_has_more_true(self):
        resp = self.client.get(reverse("cluster_leaderboard"))
        self.assertTrue(resp.context["has_more"])

    def test_user_neighborhood_present(self):
        resp = self.client.get(reverse("cluster_leaderboard"))
        self.assertIsNotNone(resp.context["user_neighborhood"])

    def test_user_in_neighborhood(self):
        resp = self.client.get(reverse("cluster_leaderboard"))
        neighborhood = resp.context["user_neighborhood"]
        self.assertTrue(any(e["is_current_user"] for e in neighborhood))


class ClusterLeaderboardUserInTopTest(TestCase):

    @classmethod
    def setUpTestData(cls):
        cls.user = make_user()
        _make_cluster_entry(cls.user.pk, "alice", 50, 500_000, 1)

    def setUp(self):
        self.client.force_login(self.user)

    def test_user_neighborhood_none(self):
        resp = self.client.get(reverse("cluster_leaderboard"))
        self.assertIsNone(resp.context["user_neighborhood"])


class ClusterLeaderboardAjaxTest(TestCase):

    @classmethod
    def setUpTestData(cls):
        cls.user = make_user()
        _make_cluster_entry(cls.user.pk, "alice", 50, 500_000, 1)

    def setUp(self):
        self.client.force_login(self.user)

    def test_ajax_returns_json(self):
        resp = self.client.get(
            reverse("cluster_leaderboard"),
            headers={"x-requested-with": "XMLHttpRequest"},
        )
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIn("entries", data)
        self.assertIn("has_more", data)
        self.assertIn("user_entry", data)
        self.assertIn("user_neighborhood", data)

    def test_ajax_with_offset(self):
        resp = self.client.get(
            reverse("cluster_leaderboard") + "?offset=1",
            headers={"x-requested-with": "XMLHttpRequest"},
        )
        data = resp.json()
        self.assertEqual(len(data["entries"]), 0)
        self.assertFalse(data["has_more"])

    def test_ajax_entry_fields(self):
        resp = self.client.get(
            reverse("cluster_leaderboard"),
            headers={"x-requested-with": "XMLHttpRequest"},
        )
        entry = resp.json()["entries"][0]
        self.assertIn("hex_count", entry)
        self.assertIn("area_km2", entry)


class ClusterLeaderboardPaginationTest(TestCase):

    @classmethod
    def setUpTestData(cls):
        cls.user = make_user()
        for i in range(25):
            _make_cluster_entry(
                user_id=1000 + i,
                username=f"user{i:03d}",
                hex_count=100 - i,
                area_m2=(100 - i) * 10_000,
                rank=i + 1,
            )

    def setUp(self):
        self.client.force_login(self.user)

    def test_first_page_has_20(self):
        resp = self.client.get(reverse("cluster_leaderboard"))
        self.assertEqual(len(resp.context["entries"]), 20)
        self.assertTrue(resp.context["has_more"])

    def test_second_page(self):
        resp = self.client.get(
            reverse("cluster_leaderboard") + "?offset=20",
            headers={"x-requested-with": "XMLHttpRequest"},
        )
        data = resp.json()
        self.assertEqual(len(data["entries"]), 5)
        self.assertFalse(data["has_more"])
