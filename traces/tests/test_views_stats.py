import json
from datetime import date
from unittest.mock import patch

from django.test import TestCase
from django.urls import reverse

from statistics.models import MonthlyStats


class StatsViewTest(TestCase):

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
        self.assertEqual(data["datasets"][0]["label"], "Hexagons acquired")
        self.assertEqual(data["datasets"][0]["data"], [10, 0, 20])
        self.assertEqual(data["datasets"][1]["label"], "New hexagons")
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

    @patch("traces.views.api_stats.date")
    def test_spans_year_boundary(self, mock_date):
        mock_date.today.return_value = date(2026, 2, 1)
        mock_date.side_effect = lambda *a, **kw: date(*a, **kw)

        MonthlyStats.objects.create(
            period=date(2025, 11, 1), hexagons_acquired=3, new_hexagons_acquired=1,
        )
        MonthlyStats.objects.create(
            period=date(2026, 2, 1), hexagons_acquired=7, new_hexagons_acquired=4,
        )

        resp = self.client.get(reverse("api_stats_monthly"))
        data = json.loads(resp.content)

        self.assertEqual(
            data["labels"],
            ["2025-11", "2025-12", "2026-01", "2026-02"],
        )
        self.assertEqual(data["datasets"][0]["data"], [3, 0, 0, 7])
        self.assertEqual(data["datasets"][1]["data"], [1, 0, 0, 4])

    @patch("traces.views.api_stats.date")
    def test_single_month(self, mock_date):
        mock_date.today.return_value = date(2025, 6, 1)
        mock_date.side_effect = lambda *a, **kw: date(*a, **kw)

        MonthlyStats.objects.create(
            period=date(2025, 6, 1), hexagons_acquired=42, new_hexagons_acquired=10,
        )

        resp = self.client.get(reverse("api_stats_monthly"))
        data = json.loads(resp.content)

        self.assertEqual(data["labels"], ["2025-06"])
        self.assertEqual(data["datasets"][0]["data"], [42])
        self.assertEqual(data["datasets"][1]["data"], [10])


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

    @patch("traces.views.api_stats.date")
    def test_traces_fills_gaps_with_zeros(self, mock_date):
        mock_date.today.return_value = date(2025, 4, 1)
        mock_date.side_effect = lambda *a, **kw: date(*a, **kw)

        MonthlyStats.objects.create(period=date(2025, 1, 1), traces_uploaded=10)
        MonthlyStats.objects.create(period=date(2025, 4, 1), traces_uploaded=20)

        resp = self.client.get(reverse("api_stats_traces"))
        data = json.loads(resp.content)

        self.assertEqual(
            data["labels"], ["2025-01", "2025-02", "2025-03", "2025-04"],
        )
        self.assertEqual(data["datasets"][0]["data"], [10, 0, 0, 20])


