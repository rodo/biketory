import datetime

from django.contrib.auth.models import User
from django.core.management import call_command
from django.test import TestCase
from django.utils import timezone

from statistics.models import DailyStats, MonthlyStats, WeeklyStats, YearlyStats
from traces.models import ClosedSurface, Hexagon, HexagonGainEvent, Trace
from traces.tests._helpers import small_route, square_polygon


class ComputeStatsEmptyDbTest(TestCase):
    """Command handles an empty database gracefully."""

    def test_no_users(self):
        """No users → early exit, no rows created."""
        call_command("compute_stats", "all")
        self.assertEqual(DailyStats.objects.count(), 0)
        self.assertEqual(WeeklyStats.objects.count(), 0)
        self.assertEqual(MonthlyStats.objects.count(), 0)
        self.assertEqual(YearlyStats.objects.count(), 0)


class ComputeStatsSingleGranularityTest(TestCase):
    """Each granularity option produces rows only in the expected table."""

    def setUp(self):
        self.user = User.objects.create_user("alice", password="pass")

    def test_day_only(self):
        today = datetime.date.today()
        call_command("compute_stats", "day", "--from", today.isoformat(), "--to", today.isoformat())
        self.assertGreaterEqual(DailyStats.objects.count(), 1)
        self.assertEqual(WeeklyStats.objects.count(), 0)
        self.assertEqual(MonthlyStats.objects.count(), 0)
        self.assertEqual(YearlyStats.objects.count(), 0)

    def test_week_only(self):
        today = datetime.date.today()
        call_command("compute_stats", "week", "--from", today.isoformat(), "--to", today.isoformat())
        self.assertEqual(DailyStats.objects.count(), 0)
        self.assertGreaterEqual(WeeklyStats.objects.count(), 1)

    def test_month_only(self):
        today = datetime.date.today()
        call_command("compute_stats", "month", "--from", today.isoformat(), "--to", today.isoformat())
        self.assertEqual(DailyStats.objects.count(), 0)
        self.assertGreaterEqual(MonthlyStats.objects.count(), 1)

    def test_year_only(self):
        today = datetime.date.today()
        call_command("compute_stats", "year", "--from", today.isoformat(), "--to", today.isoformat())
        self.assertEqual(DailyStats.objects.count(), 0)
        self.assertGreaterEqual(YearlyStats.objects.count(), 1)

    def test_all_populates_four_tables(self):
        today = datetime.date.today()
        call_command("compute_stats", "all", "--from", today.isoformat(), "--to", today.isoformat())
        self.assertGreaterEqual(DailyStats.objects.count(), 1)
        self.assertGreaterEqual(WeeklyStats.objects.count(), 1)
        self.assertGreaterEqual(MonthlyStats.objects.count(), 1)
        self.assertGreaterEqual(YearlyStats.objects.count(), 1)


class ComputeStatsCountsTest(TestCase):
    """Verify that aggregated counts match the source data."""

    def setUp(self):
        self.today = datetime.date.today()
        now = timezone.now()

        self.alice = User.objects.create_user("alice", password="pass")
        self.bob = User.objects.create_user("bob", password="pass")

        self.trace1 = Trace.objects.create(
            route=small_route(),
            length_km=12.5,
            uploaded_by=self.alice,
            first_point_date=now,
        )
        self.trace2 = Trace.objects.create(
            route=small_route(),
            length_km=7.5,
            uploaded_by=self.bob,
            first_point_date=now - datetime.timedelta(hours=1),
        )

        self.surface = ClosedSurface.objects.create(
            trace=self.trace1,
            owner=self.alice,
            polygon=square_polygon(2.35, 48.85, 0.01),
        )

        hexagon = Hexagon.objects.create(geom=square_polygon(2.35, 48.85, 0.005))
        HexagonGainEvent.objects.create(hexagon=hexagon, user=self.alice, earned_at=now)
        HexagonGainEvent.objects.create(hexagon=hexagon, user=self.bob, earned_at=now)

    def test_daily_counts(self):
        call_command("compute_stats", "day", "--from", self.today.isoformat(), "--to", self.today.isoformat())
        row = DailyStats.objects.get(period=self.today)
        self.assertEqual(row.new_users, 2)
        self.assertEqual(row.traces_uploaded, 2)
        self.assertAlmostEqual(row.total_distance_km, 20.0)
        self.assertEqual(row.surfaces_detected, 1)
        self.assertEqual(row.hexagons_earned, 2)

    def test_monthly_counts(self):
        first_of_month = self.today.replace(day=1)
        call_command("compute_stats", "month", "--from", first_of_month.isoformat(), "--to", self.today.isoformat())
        row = MonthlyStats.objects.get(period=first_of_month)
        self.assertEqual(row.new_users, 2)
        self.assertEqual(row.traces_uploaded, 2)

    def test_yearly_counts(self):
        first_of_year = self.today.replace(month=1, day=1)
        call_command("compute_stats", "year", "--from", first_of_year.isoformat(), "--to", self.today.isoformat())
        row = YearlyStats.objects.get(period=first_of_year)
        self.assertEqual(row.new_users, 2)
        self.assertEqual(row.traces_uploaded, 2)


class ComputeStatsUpdateOrCreateTest(TestCase):
    """Running the command twice updates existing rows instead of duplicating."""

    def setUp(self):
        self.user = User.objects.create_user("alice", password="pass")
        self.today = datetime.date.today()

    def test_idempotent(self):
        call_command("compute_stats", "day", "--from", self.today.isoformat(), "--to", self.today.isoformat())
        count_before = DailyStats.objects.count()
        call_command("compute_stats", "day", "--from", self.today.isoformat(), "--to", self.today.isoformat())
        self.assertEqual(DailyStats.objects.count(), count_before)

    def test_values_updated_on_rerun(self):
        call_command("compute_stats", "day", "--from", self.today.isoformat(), "--to", self.today.isoformat())
        row = DailyStats.objects.get(period=self.today)
        self.assertEqual(row.new_users, 1)

        User.objects.create_user("bob", password="pass")
        call_command("compute_stats", "day", "--from", self.today.isoformat(), "--to", self.today.isoformat())
        row.refresh_from_db()
        self.assertEqual(row.new_users, 2)


class ComputeStatsAutoDateRangeTest(TestCase):
    """When --from is omitted, the command uses the earliest user sign-up."""

    def test_auto_from_date(self):
        User.objects.create_user("alice", password="pass")
        call_command("compute_stats", "day")
        self.assertGreaterEqual(DailyStats.objects.count(), 1)


class ComputeStatsMultiDayTest(TestCase):
    """Command generates one row per period in the range."""

    def test_three_day_range(self):
        User.objects.create_user("alice", password="pass")
        start = datetime.date(2025, 6, 1)
        end = datetime.date(2025, 6, 3)
        call_command("compute_stats", "day", "--from", start.isoformat(), "--to", end.isoformat())
        self.assertEqual(DailyStats.objects.count(), 3)
        periods = set(DailyStats.objects.values_list("period", flat=True))
        self.assertEqual(periods, {
            datetime.date(2025, 6, 1),
            datetime.date(2025, 6, 2),
            datetime.date(2025, 6, 3),
        })
