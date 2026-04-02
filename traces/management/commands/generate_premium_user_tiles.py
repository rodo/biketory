import logging
import shutil
from datetime import timedelta
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand
from django.db import connection
from django.utils import timezone

logger = logging.getLogger(__name__)

from traces.models import Subscription, Trace, UserProfile
from traces.tile_generation import (
    _USER_HEXAGONS_EXTENT_SQL,
    generate_user_tiles_for_bbox,
)


class Command(BaseCommand):
    help = "Generate static PNG tiles per premium user with recent uploads"

    def add_arguments(self, parser):
        parser.add_argument(
            "--zoom-min", type=int, default=settings.TILES_STATIC_MIN_ZOOM,
            help="Minimum zoom level (default: TILES_STATIC_MIN_ZOOM)",
        )
        parser.add_argument(
            "--zoom-max", type=int, default=settings.TILES_STATIC_MAX_ZOOM,
            help="Maximum zoom level (default: TILES_STATIC_MAX_ZOOM)",
        )
        parser.add_argument(
            "--clean", action="store_true",
            help="Remove existing user tiles before generation",
        )

    def handle(self, *args, **options):
        zoom_min = options["zoom_min"]
        zoom_max = options["zoom_max"]
        tiles_root = Path(settings.MEDIA_ROOT) / "tiles"

        today = timezone.now().date()
        recent = timezone.now() - timedelta(days=7)

        # Users who uploaded in the last 7 days
        recent_user_ids = (
            Trace.objects.filter(uploaded_at__gte=recent)
            .values_list("uploaded_by_id", flat=True)
            .distinct()
        )

        # Filter to premium users with active subscription
        premium_user_ids = list(
            Subscription.objects.filter(
                user_id__in=recent_user_ids,
                start_date__lte=today,
                end_date__gte=today,
            ).values_list("user_id", flat=True)
        )

        if not premium_user_ids:
            logger.info("No premium users with recent uploads. Nothing to generate.")
            return

        logger.info("Found %d premium user(s) with recent uploads.", len(premium_user_ids))

        hexagrams = dict(
            UserProfile.objects.filter(user_id__in=premium_user_ids)
            .values_list("user_id", "hexagram")
        )

        for user_id in premium_user_ids:
            hexagram = hexagrams.get(user_id)
            if not hexagram:
                logger.info("  User %d: no hexagram. Skipping.", user_id)
                continue

            user_tiles_dir = tiles_root / hexagram[0] / hexagram[1] / hexagram

            if options["clean"] and user_tiles_dir.exists():
                shutil.rmtree(user_tiles_dir)
                logger.info("  Cleaned tiles for user %d.", user_id)

            self._generate_user_tiles(user_id, hexagram, zoom_min, zoom_max)

    def _generate_user_tiles(self, user_id, hexagram, zoom_min, zoom_max):
        with connection.cursor() as cursor:
            cursor.execute(_USER_HEXAGONS_EXTENT_SQL, [user_id])
            row = cursor.fetchone()

        if row is None or row[0] is None:
            logger.info("  User %d: no hexagons. Skipping.", user_id)
            return

        xmin, ymin, xmax, ymax = row
        total_tiles = 0

        for zoom in range(zoom_min, zoom_max + 1):
            count = generate_user_tiles_for_bbox(user_id, hexagram, zoom, xmin, ymin, xmax, ymax)
            total_tiles += count

        logger.info("  User %d: %d tiles generated.", user_id, total_tiles)
