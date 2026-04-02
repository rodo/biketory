import logging
import shutil
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand
from django.db import connection

from traces.tile_generation import generate_tiles_for_bbox

logger = logging.getLogger(__name__)

_SQL_DIR = Path(__file__).resolve().parent.parent.parent / "sql"
_HEXAGONS_EXTENT_SQL = (_SQL_DIR / "hexagons_extent.sql").read_text()


class Command(BaseCommand):
    help = "Generate static PNG tiles for hexagons at low zoom levels"

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
            help="Remove existing tiles before generation",
        )

    def handle(self, *args, **options):
        zoom_min = options["zoom_min"]
        zoom_max = options["zoom_max"]
        tiles_dir = Path(settings.MEDIA_ROOT) / "tiles"

        if options["clean"] and tiles_dir.exists():
            shutil.rmtree(tiles_dir)
            logger.info("Cleaned existing tiles.")

        # Get global extent
        with connection.cursor() as cursor:
            cursor.execute(_HEXAGONS_EXTENT_SQL)
            row = cursor.fetchone()

        if row is None or row[0] is None:
            logger.info("No hexagons with scores found. Nothing to generate.")
            return

        xmin, ymin, xmax, ymax = row
        logger.info("Extent: (%.4f, %.4f) — (%.4f, %.4f)", xmin, ymin, xmax, ymax)

        total_tiles = 0

        for zoom in range(zoom_min, zoom_max + 1):
            count = generate_tiles_for_bbox(zoom, xmin, ymin, xmax, ymax)
            total_tiles += count
            logger.info("Zoom %d: %d tiles generated", zoom, count)

        logger.info("Done. %d tiles generated.", total_tiles)
