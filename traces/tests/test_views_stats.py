import json
from datetime import date
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from statistics.models import MonthlyStats, UserMonthlyStats

User = get_user_model()


class StatsViewTest(TestCase):

    def test_stats_returns_200(self):
        resp = self.client.get(reverse("stats"))
        self.assertEqual(resp.status_code, 200)

    def test_stats_monthly_returns_200(self):
        resp = self.client.get(reverse("stats_monthly"))
        self.assertEqual(resp.status_code, 200)

    def test_stats_traces_returns_200(self):
        resp = self.client.get(reverse("stats_traces"))
        self.assertEqual(resp.status_code, 200)


class StatsApiEmptyTest(TestCase):
    """API endpoints return empty structure when no data exists."""

    def test_api_stats_monthly_empty(self):
        resp = self.client.get(reverse("api_stats_monthly"))
        self.assertEqual(resp.status_code, 200)
        data = json.loads(resp.content)
        self.assertEqual(data, {"labels": [], "datasets": []})

    def test_api_stats_traces_empty(self):
        resp = self.client.get(reverse("api_stats_traces"))
        self.assertEqual(resp.status_code, 200)
        data = json.loads(resp.content)
        self.assertEqual(data, {"labels": [], "datasets": []})

    def test_api_stats_users_empty(self):
        resp = self.client.get(reverse("api_stats"))
        self.assertEqual(resp.status_code, 200)
        data = json.loads(resp.content)
        self.assertEqual(data, {"labels": [], "datasets": []})


class StatsApiMonthlyTest(TestCase):
    """Tests for /api/stats/monthly/ with MonthlyStats data."""

    @patch("traces.views.api_stats.date")
    def test_returns_hexagon_datasets(self, mock_date):
        mock_date.today.return_value = date(2025, 3, 1)
        mock_date.side_effect = lambda *a, **kw: date(*a, **kw)

        MonthlyStats.objects.create(
            period=date(2025, 1, 1), hexagons_acquired=10, new_hexagons_acquired=5,
        )
        MonthlyStats.objects.create(
            period=date(2025, 3, 1), hexagons_acquired=20, new_hexagons_acquired=8,
        )

        resp = self.client.get(reverse("api_stats_monthly"))
        data = json.loads(resp.content)

        self.assertEqual(data["labels"], ["2025-01", "2025-02", "2025-03"])
        self.assertEqual(len(data["datasets"]), 2)
        self.assertEqual(data["datasets"][0]["label"], "Hexagons acquis")
        self.assertEqual(data["datasets"][0]["data"], [10, 0, 20])
        self.assertEqual(data["datasets"][1]["label"], "Nouveaux hexagons")
        self.assertEqual(data["datasets"][1]["data"], [5, 0, 8])

    @patch("traces.views.api_stats.date")
    def test_fills_gaps_with_zeros(self, mock_date):
        mock_date.today.return_value = date(2025, 4, 1)
        mock_date.side_effect = lambda *a, **kw: date(*a, **kw)

        MonthlyStats.objects.create(
            period=date(2025, 1, 1), hexagons_acquired=5, new_hexagons_acquired=3,
        )
        MonthlyStats.objects.create(
            period=date(2025, 4, 1), hexagons_acquired=7, new_hexagons_acquired=2,
        )

        resp = self.client.get(reverse("api_stats_monthly"))
        data = json.loads(resp.content)

        self.assertEqual(
            data["labels"], ["2025-01", "2025-02", "2025-03", "2025-04"],
        )
        self.assertEqual(data["datasets"][0]["data"], [5, 0, 0, 7])
        self.assertEqual(data["datasets"][1]["data"], [3, 0, 0, 2])


class StatsApiTracesTest(TestCase):
    """Tests for /api/stats/traces/ with MonthlyStats data."""

    @patch("traces.views.api_stats.date")
    def test_returns_traces_dataset(self, mock_date):
        mock_date.today.return_value = date(2025, 2, 1)
        mock_date.side_effect = lambda *a, **kw: date(*a, **kw)

        MonthlyStats.objects.create(period=date(2025, 1, 1), traces_uploaded=15)
        MonthlyStats.objects.create(period=date(2025, 2, 1), traces_uploaded=22)

        resp = self.client.get(reverse("api_stats_traces"))
        data = json.loads(resp.content)

        self.assertEqual(data["labels"], ["2025-01", "2025-02"])
        self.assertEqual(len(data["datasets"]), 1)
        self.assertEqual(data["datasets"][0]["label"], "Traces")
        self.assertEqual(data["datasets"][0]["data"], [15, 22])


class StatsApiPerUserTest(TestCase):
    """Tests for /api/stats/users/ with UserMonthlyStats data."""

    @classmethod
    def setUpTestData(cls):
        cls.alice = User.objects.create_user(username="alice", password="test")
        cls.bob = User.objects.create_user(username="bob", password="test")

    def test_returns_per_user_datasets(self):
        UserMonthlyStats.objects.create(
            period=date(2025, 1, 1), user_id=self.alice.id, hexagons_acquired=1,
        )
        UserMonthlyStats.objects.create(
            period=date(2025, 2, 1), user_id=self.alice.id, hexagons_acquired=1,
        )
        UserMonthlyStats.objects.create(
            period=date(2025, 1, 1), user_id=self.bob.id, hexagons_acquired=1,
        )

        resp = self.client.get(reverse("api_stats"))
        data = json.loads(resp.content)

        self.assertEqual(data["labels"], ["2025-01", "2025-02"])
        self.assertEqual(len(data["datasets"]), 2)

        alice_ds = next(d for d in data["datasets"] if d["label"] == "alice")
        bob_ds = next(d for d in data["datasets"] if d["label"] == "bob")

        self.assertEqual(alice_ds["data"], [1, 1])
        self.assertEqual(bob_ds["data"], [1, 0])

    def test_each_user_gets_distinct_color(self):
        UserMonthlyStats.objects.create(
            period=date(2025, 1, 1), user_id=self.alice.id, hexagons_acquired=1,
        )
        UserMonthlyStats.objects.create(
            period=date(2025, 1, 1), user_id=self.bob.id, hexagons_acquired=1,
        )

        resp = self.client.get(reverse("api_stats"))
        data = json.loads(resp.content)

        colors = [d["backgroundColor"] for d in data["datasets"]]
        self.assertEqual(len(colors), 2)
        self.assertNotEqual(colors[0], colors[1])
