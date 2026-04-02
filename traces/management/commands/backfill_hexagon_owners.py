import logging
from pathlib import Path

from django.core.management.base import BaseCommand
from django.db import connection

logger = logging.getLogger(__name__)

_SQL_DIR = Path(__file__).resolve().parent.parent.parent / "sql"
_BACKFILL_SQL = (_SQL_DIR / "backfill_hexagon_owners.sql").read_text()


class Command(BaseCommand):
    help = "Backfill Hexagon.owner from HexagonScore (highest points, latest earned_at)"

    def handle(self, *args, **options):
        with connection.cursor() as cursor:
            cursor.execute(_BACKFILL_SQL)
            updated = cursor.rowcount

        logger.info("Backfilled owner on %d hexagon(s).", updated)
        self.stdout.write(self.style.SUCCESS(f"Updated {updated} hexagon(s)."))
