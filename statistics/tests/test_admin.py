import datetime

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from statistics.models import DailyStats, MonthlyStats, WeeklyStats, YearlyStats

user_model = get_user_model()


class StatsAdminTest(TestCase):
    """All four stats models are accessible in the Django admin."""

    def setUp(self):
        self.admin = user_model.objects.create_superuser("admin", "admin@test.com", "pass")
        self.admin.refresh_from_db()
        self.client.force_login(self.admin)
        DailyStats.objects.create(period=datetime.date(2025, 1, 1))
        WeeklyStats.objects.create(period=datetime.date(2025, 1, 6))  # Monday
        MonthlyStats.objects.create(period=datetime.date(2025, 1, 1))
        YearlyStats.objects.create(period=datetime.date(2025, 1, 1))

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
