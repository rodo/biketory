import logging
import time
from datetime import date
from pathlib import Path

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.db import connection, transaction
from django.utils import timezone

from geozones.models import GeoZone, MonthlyZoneRanking, ZoneLeaderboardEntry

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
        parser.add_argument(
            "--snapshot-month",
            type=str,
            default=None,
            help="Save a monthly snapshot (format: YYYY-MM). Only premium users are saved.",
        )

    def _parse_snapshot_month(self, raw):
        try:
            year, month = raw.split("-")
            return date(int(year), int(month), 1)
        except (ValueError, AttributeError) as err:
            raise CommandError(
                f"Invalid --snapshot-month format: '{raw}'. Expected YYYY-MM."
            ) from err

    def _compute_zone_data(self, zone):
        with connection.cursor() as cursor:
            cursor.execute(_CONQUERED_SQL, [zone.pk])
            conquered_rows = cursor.fetchall()

            cursor.execute(_ACQUIRED_SQL, [zone.pk])
            acquired_rows = cursor.fetchall()

        data = {}
        for user_id, conquered in conquered_rows:
            data[user_id] = {"conquered": conquered, "acquired": 0}
        for user_id, acquired in acquired_rows:
            data.setdefault(user_id, {"conquered": 0, "acquired": 0})
            data[user_id]["acquired"] = acquired
        return data

    def _compute_ranks(self, data):
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

        return rank_conquered, rank_acquired

    def handle(self, *args, **options):
        t0 = time.monotonic()
        zone_code = options["zone_code"]
        snapshot_month = options["snapshot_month"]
        period = self._parse_snapshot_month(snapshot_month) if snapshot_month else None

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
            data = self._compute_zone_data(zone)

            if not data:
                if not period:
                    with transaction.atomic():
                        ZoneLeaderboardEntry.objects.filter(zone=zone).delete()
                continue

            usernames = dict(
                user_model.objects.filter(pk__in=data.keys())
                .values_list("pk", "username")
            )

            rank_conquered, rank_acquired = self._compute_ranks(data)

            now = timezone.now()

            if period:
                # Monthly snapshot — premium users only
                snapshot_entries = 0
                for user_id, vals in data.items():
                    if user_id not in premium_user_ids:
                        continue
                    MonthlyZoneRanking.objects.update_or_create(
                        zone=zone,
                        period=period,
                        user_id=user_id,
                        defaults={
                            "username": usernames.get(user_id, f"user_{user_id}"),
                            "is_premium": True,
                            "hexagons_conquered": vals["conquered"],
                            "hexagons_acquired": vals["acquired"],
                            "rank_conquered": rank_conquered[user_id],
                            "rank_acquired": rank_acquired[user_id],
                            "computed_at": now,
                        },
                    )
                    snapshot_entries += 1
                total_entries += snapshot_entries
            else:
                # Live leaderboard
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
        label = f"snapshot {snapshot_month}" if period else "live"
        logger.info(
            "Zone leaderboard computed (%s): %d entries across %d zones in %.1f s",
            label, total_entries, zones.count(), elapsed,
        )
