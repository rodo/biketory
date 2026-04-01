import logging
import time
from pathlib import Path

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.db import connection, transaction
from django.utils import timezone

from statistics.models import LeaderboardEntry

logger = logging.getLogger(__name__)

_SQL_DIR = Path(__file__).resolve().parent.parent.parent / "sql"
_CONQUERED_SQL = (_SQL_DIR / "leaderboard_conquered.sql").read_text()
_ACQUIRED_SQL = (_SQL_DIR / "leaderboard_acquired.sql").read_text()


class Command(BaseCommand):
    help = "Compute the leaderboard (hexagons conquered & acquired)."

    def handle(self, *args, **options):
        t0 = time.monotonic()

        with connection.cursor() as cursor:
            cursor.execute(_CONQUERED_SQL)
            conquered_rows = cursor.fetchall()

            cursor.execute(_ACQUIRED_SQL)
            acquired_rows = cursor.fetchall()

        # Merge results by user_id
        data = {}
        for user_id, conquered in conquered_rows:
            data[user_id] = {"conquered": conquered, "acquired": 0}
        for user_id, acquired in acquired_rows:
            data.setdefault(user_id, {"conquered": 0, "acquired": 0})
            data[user_id]["acquired"] = acquired

        # Fetch usernames and premium status in batch
        user_model = get_user_model()
        usernames = dict(
            user_model.objects.filter(pk__in=data.keys())
            .values_list("pk", "username")
        )

        from traces.models import Subscription
        today = timezone.now().date()
        premium_user_ids = set(
            Subscription.objects.filter(
                start_date__lte=today, end_date__gte=today
            ).values_list("user_id", flat=True)
        )

        # Compute dense ranks
        by_conquered = sorted(data.items(), key=lambda x: x[1]["conquered"], reverse=True)
        by_acquired = sorted(data.items(), key=lambda x: x[1]["acquired"], reverse=True)

        rank_conquered = {}
        current_rank = 0
        prev_val = None
        for user_id, vals in by_conquered:
            if vals["conquered"] != prev_val:
                current_rank += 1
                prev_val = vals["conquered"]
            rank_conquered[user_id] = current_rank

        rank_acquired = {}
        current_rank = 0
        prev_val = None
        for user_id, vals in by_acquired:
            if vals["acquired"] != prev_val:
                current_rank += 1
                prev_val = vals["acquired"]
            rank_acquired[user_id] = current_rank

        # Build entries
        now = timezone.now()
        entries = [
            LeaderboardEntry(
                user_id=user_id,
                username=usernames.get(user_id, f"user_{user_id}"),
                is_premium=user_id in premium_user_ids,
                hexagons_conquered=vals["conquered"],
                hexagons_acquired=vals["acquired"],
                rank_conquered=rank_conquered[user_id],
                rank_acquired=rank_acquired[user_id],
                computed_at=now,
            )
            for user_id, vals in data.items()
        ]

        with transaction.atomic():
            LeaderboardEntry.objects.all().delete()
            LeaderboardEntry.objects.bulk_create(entries)

        elapsed = time.monotonic() - t0
        logger.info("Leaderboard computed: %d entries in %.1f s", len(entries), elapsed)
        self.stdout.write(f"Leaderboard computed: {len(entries)} entries in {elapsed:.1f} s")
