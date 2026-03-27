import datetime

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from statistics.models import DailyStats, MonthlyStats, WeeklyStats, YearlyStats


class StatsAdminTest(TestCase):
    """All four stats models are accessible in the Django admin."""

    def setUp(self):
        self.admin = User.objects.create_superuser("admin", "admin@test.com", "pass")
        self.client.login(username="admin", password="pass")
        for model in (DailyStats, WeeklyStats, MonthlyStats, YearlyStats):
            model.objects.create(period=datetime.date(2025, 1, 1))

    def test_dailystats_changelist(self):
        resp = self.client.get(reverse("admin:statistics_dailystats_changelist"))
        self.assertEqual(resp.status_code, 200)

    def test_weeklystats_changelist(self):
        resp = self.client.get(reverse("admin:statistics_weeklystats_changelist"))
        self.assertEqual(resp.status_code, 200)

    def test_monthlystats_changelist(self):
        resp = self.client.get(reverse("admin:statistics_monthlystats_changelist"))
        self.assertEqual(resp.status_code, 200)

    def test_yearlystats_changelist(self):
        resp = self.client.get(reverse("admin:statistics_yearlystats_changelist"))
        self.assertEqual(resp.status_code, 200)
