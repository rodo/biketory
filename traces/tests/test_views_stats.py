from django.test import TestCase
from django.urls import reverse


class StatsViewTest(TestCase):

    def test_stats_returns_200(self):
        resp = self.client.get(reverse("stats"))
        self.assertEqual(resp.status_code, 200)

    def test_stats_chart_data_in_context(self):
        resp = self.client.get(reverse("stats"))
        self.assertIn("chart_data", resp.context)

    def test_stats_monthly_returns_200(self):
        resp = self.client.get(reverse("stats_monthly"))
        self.assertEqual(resp.status_code, 200)

    def test_stats_monthly_chart_data_in_context(self):
        resp = self.client.get(reverse("stats_monthly"))
        self.assertIn("chart_data", resp.context)

    def test_stats_traces_returns_200(self):
        resp = self.client.get(reverse("stats_traces"))
        self.assertEqual(resp.status_code, 200)

    def test_stats_traces_chart_data_in_context(self):
        resp = self.client.get(reverse("stats_traces"))
        self.assertIn("chart_data", resp.context)
