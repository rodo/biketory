import datetime
from pathlib import Path

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.db import connection

from statistics.models import DailyStats, MonthlyStats, WeeklyStats, YearlyStats

_SQL_DIR = Path(__file__).resolve().parent.parent.parent / "sql"
_COMPUTE_STATS_SQL = (_SQL_DIR / "compute_stats.sql").read_text()

GRANULARITY_MAP = {
    "day": ("day", DailyStats),
    "week": ("week", WeeklyStats),
    "month": ("month", MonthlyStats),
    "year": ("year", YearlyStats),
}


class Command(BaseCommand):
    help = "Compute aggregated statistics for day/week/month/year granularities."

    def add_arguments(self, parser):
        parser.add_argument(
            "granularity",
            choices=["day", "week", "month", "year", "all"],
            help="Granularity to compute: day, week, month, year, or all.",
        )
        parser.add_argument(
            "--from",
            dest="date_from",
            type=datetime.date.fromisoformat,
            default=None,
            help="Start date (YYYY-MM-DD). Default: earliest user sign-up.",
        )
        parser.add_argument(
            "--to",
            dest="date_to",
            type=datetime.date.fromisoformat,
            default=None,
            help="End date (YYYY-MM-DD). Default: today.",
        )

    def handle(self, *args, **options):
        date_from = options["date_from"]
        date_to = options["date_to"] or datetime.date.today()

        if date_from is None:
            User = get_user_model()
            earliest = User.objects.order_by("date_joined").values_list(
                "date_joined", flat=True
            ).first()
            if earliest is None:
                self.stdout.write("No users found, nothing to compute.")
                return
            date_from = earliest.date()

        granularity = options["granularity"]
        if granularity == "all":
            granularities = list(GRANULARITY_MAP.keys())
        else:
            granularities = [granularity]

        for gran in granularities:
            trunc, model = GRANULARITY_MAP[gran]
            self._compute(trunc, model, date_from, date_to)

    def _compute(self, trunc, model, date_from, date_to):
        interval = trunc
        params = [date_from, date_to, interval, trunc, trunc, trunc, trunc]

        with connection.cursor() as cursor:
            cursor.execute(_COMPUTE_STATS_SQL, params)
            rows = cursor.fetchall()

        count = 0
        for row in rows:
            period, new_users, traces_uploaded, total_distance_km, surfaces_detected, hexagons_earned = row
            model.objects.update_or_create(
                period=period,
                defaults={
                    "new_users": new_users,
                    "traces_uploaded": traces_uploaded,
                    "total_distance_km": total_distance_km,
                    "surfaces_detected": surfaces_detected,
                    "hexagons_earned": hexagons_earned,
                },
            )
            count += 1

        self.stdout.write(
            self.style.SUCCESS(f"{model.__name__}: {count} periods updated.")
        )
