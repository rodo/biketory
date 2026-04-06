import logging
import time
from pathlib import Path

from django.contrib.auth import get_user_model
from django.contrib.gis.geos import GEOSGeometry, MultiPolygon
from django.core.management.base import BaseCommand
from django.db import connection, transaction
from django.utils import timezone

from statistics.models import ClusterLeaderboardEntry

logger = logging.getLogger(__name__)

_SQL_DIR = Path(__file__).resolve().parent.parent.parent / "sql"
_CLUSTER_SQL = (_SQL_DIR / "leaderboard_largest_cluster.sql").read_text()


class Command(BaseCommand):
    help = "Compute the largest contiguous cluster leaderboard."

    def handle(self, *args, **options):
        t0 = time.monotonic()

        with connection.cursor() as cursor:
            cursor.execute(_CLUSTER_SQL)
            rows = cursor.fetchall()

        if not rows:
            logger.info("No hexagon owners found, nothing to compute.")
            return

        user_ids = [r[0] for r in rows]

        user_model = get_user_model()
        usernames = dict(
            user_model.objects.filter(pk__in=user_ids).values_list("pk", "username")
        )

        from traces.models import Subscription

        today = timezone.now().date()
        premium_user_ids = set(
            Subscription.objects.filter(
                start_date__lte=today, end_date__gte=today
            ).values_list("user_id", flat=True)
        )

        # Dense rank on hex_count
        ranked = []
        current_rank = 0
        prev_count = None
        for user_id, hex_count, area_m2, cluster_geom_wkb in rows:
            if hex_count != prev_count:
                current_rank += 1
                prev_count = hex_count
            ranked.append((user_id, hex_count, area_m2, cluster_geom_wkb, current_rank))

        now = timezone.now()
        entries = []
        for user_id, hex_count, area_m2, cluster_geom_wkb, rank in ranked:
            geom = None
            if cluster_geom_wkb:
                geom = GEOSGeometry(cluster_geom_wkb)
                if geom.geom_type == "Polygon":
                    geom = MultiPolygon(geom, srid=geom.srid)
            entries.append(
                ClusterLeaderboardEntry(
                    user_id=user_id,
                    username=usernames.get(user_id, f"user_{user_id}"),
                    is_premium=user_id in premium_user_ids,
                    largest_cluster_hex_count=hex_count,
                    largest_cluster_area_m2=area_m2,
                    largest_cluster_geom=geom,
                    rank=rank,
                    computed_at=now,
                )
            )

        with transaction.atomic():
            ClusterLeaderboardEntry.objects.all().delete()
            ClusterLeaderboardEntry.objects.bulk_create(entries)

        elapsed = time.monotonic() - t0
        logger.info(
            "Cluster leaderboard computed: %d entries in %.1f s",
            len(entries),
            elapsed,
        )
