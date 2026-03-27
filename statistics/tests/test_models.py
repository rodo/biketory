import datetime

from django.db import IntegrityError
from django.test import TestCase

from statistics.models import DailyStats, MonthlyStats, WeeklyStats, YearlyStats


class BaseStatsFieldsTest(TestCase):
    """Verify default values and field behaviour shared by all concrete models."""

    def test_defaults(self):
        row = DailyStats.objects.create(period=datetime.date(2025, 1, 1))
        self.assertEqual(row.new_users, 0)
        self.assertEqual(row.traces_uploaded, 0)
        self.assertEqual(row.total_distance_km, 0.0)
        self.assertEqual(row.surfaces_detected, 0)
        self.assertEqual(row.hexagons_acquired, 0)
        self.assertEqual(row.new_hexagons_acquired, 0)
        self.assertIsNotNone(row.computed_at)

    def test_str(self):
        row = DailyStats.objects.create(period=datetime.date(2025, 6, 15))
        self.assertEqual(str(row), "DailyStats 2025-06-15")

    def test_computed_at_auto_updates(self):
        row = DailyStats.objects.create(period=datetime.date(2025, 1, 1))
        first_computed = row.computed_at
        row.new_users = 5
        row.save()
        row.refresh_from_db()
        self.assertGreaterEqual(row.computed_at, first_computed)


class PeriodUniquenessTest(TestCase):
    """Each concrete model enforces unique period."""

    def test_daily_unique_period(self):
        d = datetime.date(2025, 3, 1)
        DailyStats.objects.create(period=d)
        with self.assertRaises(IntegrityError):
            DailyStats.objects.create(period=d)

    def test_weekly_unique_period(self):
        d = datetime.date(2025, 3, 3)  # Monday
        WeeklyStats.objects.create(period=d)
        with self.assertRaises(IntegrityError):
            WeeklyStats.objects.create(period=d)

    def test_monthly_unique_period(self):
        d = datetime.date(2025, 3, 1)
        MonthlyStats.objects.create(period=d)
        with self.assertRaises(IntegrityError):
            MonthlyStats.objects.create(period=d)

    def test_yearly_unique_period(self):
        d = datetime.date(2025, 1, 1)
        YearlyStats.objects.create(period=d)
        with self.assertRaises(IntegrityError):
            YearlyStats.objects.create(period=d)

    def test_same_date_different_models(self):
        """The same period date can exist in different granularity tables."""
        DailyStats.objects.create(period=datetime.date(2025, 1, 6))
        WeeklyStats.objects.create(period=datetime.date(2025, 1, 6))  # Monday
        MonthlyStats.objects.create(period=datetime.date(2025, 1, 1))
        YearlyStats.objects.create(period=datetime.date(2025, 1, 1))
        self.assertEqual(DailyStats.objects.count(), 1)
        self.assertEqual(WeeklyStats.objects.count(), 1)
        self.assertEqual(MonthlyStats.objects.count(), 1)
        self.assertEqual(YearlyStats.objects.count(), 1)

    def test_weekly_rejects_non_monday(self):
        with self.assertRaises(IntegrityError):
            WeeklyStats.objects.create(period=datetime.date(2025, 1, 1))  # Wednesday

    def test_monthly_rejects_non_first(self):
        with self.assertRaises(IntegrityError):
            MonthlyStats.objects.create(period=datetime.date(2025, 1, 15))

    def test_yearly_rejects_non_jan_first(self):
        with self.assertRaises(IntegrityError):
            YearlyStats.objects.create(period=datetime.date(2025, 3, 1))


class OrderingTest(TestCase):
    def test_default_ordering_is_descending(self):
        DailyStats.objects.create(period=datetime.date(2025, 1, 1))
        DailyStats.objects.create(period=datetime.date(2025, 1, 3))
        DailyStats.objects.create(period=datetime.date(2025, 1, 2))
        periods = list(DailyStats.objects.values_list("period", flat=True))
        self.assertEqual(periods, [
            datetime.date(2025, 1, 3),
            datetime.date(2025, 1, 2),
            datetime.date(2025, 1, 1),
        ])
