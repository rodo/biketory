import json

from django.test import TestCase
from django.urls import reverse


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


class StatsApiTest(TestCase):

    def test_api_stats_monthly_returns_json(self):
        resp = self.client.get(reverse("api_stats_monthly"))
        self.assertEqual(resp.status_code, 200)
        data = json.loads(resp.content)
        self.assertIn("labels", data)
        self.assertIn("datasets", data)

    def test_api_stats_traces_returns_json(self):
        resp = self.client.get(reverse("api_stats_traces"))
        self.assertEqual(resp.status_code, 200)
        data = json.loads(resp.content)
        self.assertIn("labels", data)
        self.assertIn("datasets", data)

    def test_api_stats_users_returns_json(self):
        resp = self.client.get(reverse("api_stats"))
        self.assertEqual(resp.status_code, 200)
        data = json.loads(resp.content)
        self.assertIn("labels", data)
        self.assertIn("datasets", data)
