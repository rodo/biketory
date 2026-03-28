import datetime
import logging
import time
from pathlib import Path

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.db import connection

from statistics.models import (
    DailyStats,
    MonthlyStats,
    UserDailyStats,
    UserMonthlyStats,
    UserWeeklyStats,
    UserYearlyStats,
    WeeklyStats,
    YearlyStats,
)

logger = logging.getLogger(__name__)

_SQL_DIR = Path(__file__).resolve().parent.parent.parent / "sql"
_NEW_USERS_SQL = (_SQL_DIR / "new_users.sql").read_text()
_TRACES_SQL = (_SQL_DIR / "traces.sql").read_text()
_SURFACES_SQL = (_SQL_DIR / "surfaces.sql").read_text()
_HEXAGONS_ACQUIRED_SQL = (_SQL_DIR / "hexagons_acquired.sql").read_text()
_NEW_HEXAGONS_ACQUIRED_SQL = (_SQL_DIR / "new_hexagons_acquired.sql").read_text()
_USER_HEXAGONS_ACQUIRED_SQL = (_SQL_DIR / "user_hexagons_acquired.sql").read_text()

GRANULARITY_MAP = {
    "day": ("day", DailyStats, UserDailyStats),
    "week": ("week", WeeklyStats, UserWeeklyStats),
    "month": ("month", MonthlyStats, UserMonthlyStats),
    "year": ("year", YearlyStats, UserYearlyStats),
}


def _generate_periods(trunc, date_from, date_to):
    """Generate all period start dates between date_from and date_to."""
    periods = []
    if trunc == "day":
        d = date_from
        while d <= date_to:
            periods.append(d)
            d += datetime.timedelta(days=1)
    elif trunc == "week":
        d = date_from - datetime.timedelta(days=date_from.weekday())
        while d <= date_to:
            periods.append(d)
            d += datetime.timedelta(weeks=1)
    elif trunc == "month":
        d = date_from.replace(day=1)
        while d <= date_to:
            periods.append(d)
            if d.month == 12:
                d = d.replace(year=d.year + 1, month=1)
            else:
                d = d.replace(month=d.month + 1)
    elif trunc == "year":
        d = date_from.replace(month=1, day=1)
        while d <= date_to:
            periods.append(d)
            d = d.replace(year=d.year + 1)
    return periods


def _execute_query(label, sql, params):
    """Execute a single SQL query and return {period: {col: value}} dict."""
    t0 = time.monotonic()
    with connection.cursor() as cursor:
        cursor.execute(sql, params)
        columns = [col.name for col in cursor.description]
        rows = cursor.fetchall()
    elapsed_ms = (time.monotonic() - t0) * 1000
    logger.info("%s: %.1f ms (%d rows)", label, elapsed_ms, len(rows))

    result = {}
    for row in rows:
        period = row[0]
        result[period] = dict(zip(columns[1:], row[1:], strict=True))
    return result


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
                logger.info("No users found, nothing to compute.")
                return
            date_from = earliest.date()

        granularity = options["granularity"]
        if granularity == "all":
            granularities = list(GRANULARITY_MAP.keys())
        else:
            granularities = [granularity]

        logger.info("Computing stats from %s to %s for: %s", date_from, date_to, ", ".join(granularities))

        for gran in granularities:
            trunc, model, user_model = GRANULARITY_MAP[gran]
            self._compute(trunc, model, date_from, date_to)
            self._compute_user_stats(trunc, user_model, date_from, date_to)

    def _compute(self, trunc, model, date_from, date_to):
        params = [trunc, date_from, date_to]

        users_data = _execute_query("new_users", _NEW_USERS_SQL, params)
        traces_data = _execute_query("traces", _TRACES_SQL, params)
        surfaces_data = _execute_query("surfaces", _SURFACES_SQL, params)
        hexagons_data = _execute_query("hexagons_acquired", _HEXAGONS_ACQUIRED_SQL, params)
        new_hexagons_data = _execute_query("new_hexagons_acquired", _NEW_HEXAGONS_ACQUIRED_SQL, params)

        periods = _generate_periods(trunc, date_from, date_to)

        defaults_template = {
            "new_users": 0,
            "traces_uploaded": 0,
            "total_distance_km": 0.0,
            "surfaces_detected": 0,
            "hexagons_acquired": 0,
            "new_hexagons_acquired": 0,
        }

        count = 0
        for period in periods:
            merged = dict(defaults_template)
            merged.update(users_data.get(period, {}))
            merged.update(traces_data.get(period, {}))
            merged.update(surfaces_data.get(period, {}))
            merged.update(hexagons_data.get(period, {}))
            merged.update(new_hexagons_data.get(period, {}))

            model.objects.update_or_create(
                period=period,
                defaults=merged,
            )
            count += 1

        logger.info("%s: %d periods updated.", model.__name__, count)

    def _compute_user_stats(self, trunc, user_model, date_from, date_to):
        params = [trunc, date_from, date_to]
        t0 = time.monotonic()
        with connection.cursor() as cursor:
            cursor.execute(_USER_HEXAGONS_ACQUIRED_SQL, params)
            rows = cursor.fetchall()
        elapsed_ms = (time.monotonic() - t0) * 1000
        logger.info("user_hexagons_acquired (%s): %.1f ms (%d rows)", trunc, elapsed_ms, len(rows))

        count = 0
        for period, user_id, hexagons_acquired in rows:
            user_model.objects.update_or_create(
                period=period,
                user_id=user_id,
                defaults={"hexagons_acquired": hexagons_acquired},
            )
            count += 1

        logger.info("%s: %d rows updated.", user_model.__name__, count)
