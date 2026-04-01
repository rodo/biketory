import logging
import time
from pathlib import Path

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.db import connection, transaction
from django.utils import timezone

from geozones.models import GeoZone, ZoneLeaderboardEntry

logger = logging.getLogger(__name__)

_SQL_DIR = Path(__file__).resolve().parent.parent.parent / "sql"
_CONQUERED_SQL = (_SQL_DIR / "zone_leaderboard_conquered.sql").read_text()
_ACQUIRED_SQL = (_SQL_DIR / "zone_leaderboard_acquired.sql").read_text()


class Command(BaseCommand):
    help = "Compute leaderboard per geographic zone (hexagons conquered & acquired)."

    def add_arguments(self, parser):
        parser.add_argument(
            "--zone-code",
            type=str,
            default=None,
            help="Compute for a single zone code only.",
        )

    def handle(self, *args, **options):
        t0 = time.monotonic()
        zone_code = options["zone_code"]

        zones = GeoZone.objects.filter(active=True)
        if zone_code:
            zones = zones.filter(code=zone_code)

        if not zones.exists():
            self.stderr.write("No zones found.")
            return

        user_model = get_user_model()
        total_entries = 0

        from traces.models import Subscription

        today = timezone.now().date()
        premium_user_ids = set(
            Subscription.objects.filter(
                start_date__lte=today, end_date__gte=today
            ).values_list("user_id", flat=True)
        )

        for zone in zones:
            with connection.cursor() as cursor:
                cursor.execute(_CONQUERED_SQL, [zone.pk])
                conquered_rows = cursor.fetchall()

                cursor.execute(_ACQUIRED_SQL, [zone.pk])
                acquired_rows = cursor.fetchall()

            # Merge results by user_id
            data = {}
            for user_id, conquered in conquered_rows:
                data[user_id] = {"conquered": conquered, "acquired": 0}
            for user_id, acquired in acquired_rows:
                data.setdefault(user_id, {"conquered": 0, "acquired": 0})
                data[user_id]["acquired"] = acquired

            if not data:
                with transaction.atomic():
                    ZoneLeaderboardEntry.objects.filter(zone=zone).delete()
                continue

            # Fetch usernames
            usernames = dict(
                user_model.objects.filter(pk__in=data.keys())
                .values_list("pk", "username")
            )

            # Dense ranks
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
                ZoneLeaderboardEntry(
                    zone=zone,
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
                ZoneLeaderboardEntry.objects.filter(zone=zone).delete()
                ZoneLeaderboardEntry.objects.bulk_create(entries)

            total_entries += len(entries)

        elapsed = time.monotonic() - t0
        logger.info(
            "Zone leaderboard computed: %d entries across %d zones in %.1f s",
            total_entries, zones.count(), elapsed,
        )
        self.stdout.write(
            f"Zone leaderboard computed: {total_entries} entries "
            f"across {zones.count()} zones in {elapsed:.1f} s"
        )
