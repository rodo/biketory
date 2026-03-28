import datetime
import logging
from pathlib import Path

from django.core.management.base import BaseCommand
from django.db import connection

logger = logging.getLogger(__name__)

_SQL_DIR = Path(__file__).resolve().parent.parent.parent / "sql"
_CREATE_PARTITIONS_SQL = (_SQL_DIR / "create_daily_stats_partitions.sql").read_text()


class Command(BaseCommand):
    help = (
        "Create missing monthly sub-partitions for statistics_userdailystats "
        "for the current month and the next 3 months."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--months-ahead",
            type=int,
            default=3,
            help="Number of months ahead to provision (default: 3).",
        )

    def handle(self, *args, **options):
        today = datetime.date.today()
        months_ahead = options["months_ahead"]

        start = today.replace(day=1)
        end = start
        for _ in range(months_ahead):
            if end.month == 12:
                end = end.replace(year=end.year + 1, month=1)
            else:
                end = end.replace(month=end.month + 1)

        logger.info(
            "Creating partitions from %s to %s", start.isoformat(), end.isoformat()
        )

        with connection.cursor() as cursor:
            cursor.execute(_CREATE_PARTITIONS_SQL, [start, end])

        logger.info("Done.")
