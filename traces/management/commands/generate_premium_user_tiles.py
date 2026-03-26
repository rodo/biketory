import shutil
from datetime import timedelta
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand
from django.db import connection
from django.utils import timezone
from PIL import Image, ImageDraw

from traces.models import Subscription, Trace
from traces.tiles import (
    TILE_SIZE,
    lat_to_tile_y,
    lng_to_tile_x,
    lnglat_to_pixel,
    parse_wkt_polygon,
    tile_to_bbox,
)

_SQL_DIR = Path(__file__).resolve().parent.parent.parent / "sql"
_USER_HEXAGONS_EXTENT_SQL = (_SQL_DIR / "user_hexagons_extent.sql").read_text()
_USER_HEXAGONS_FOR_TILE_SQL = (_SQL_DIR / "user_hexagons_for_tile.sql").read_text()

FILL_COLOR = (41, 128, 185, 160)
OUTLINE_COLOR = (41, 128, 185, 200)


class Command(BaseCommand):
    help = "Generate static PNG tiles per premium user with recent uploads"

    def add_arguments(self, parser):
        parser.add_argument(
            "--zoom-min", type=int, default=5,
            help="Minimum zoom level (default: 5)",
        )
        parser.add_argument(
            "--zoom-max", type=int, default=10,
            help="Maximum zoom level (default: 10)",
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
            self.stdout.write("No premium users with recent uploads. Nothing to generate.")
            return

        self.stdout.write(f"Found {len(premium_user_ids)} premium user(s) with recent uploads.")

        for user_id in premium_user_ids:
            user_tiles_dir = tiles_root / str(user_id)

            if options["clean"] and user_tiles_dir.exists():
                shutil.rmtree(user_tiles_dir)
                self.stdout.write(f"  Cleaned tiles for user {user_id}.")

            self._generate_user_tiles(user_id, user_tiles_dir, zoom_min, zoom_max)

    def _generate_user_tiles(self, user_id, tiles_dir, zoom_min, zoom_max):
        with connection.cursor() as cursor:
            cursor.execute(_USER_HEXAGONS_EXTENT_SQL, [user_id])
            row = cursor.fetchone()

        if row is None or row[0] is None:
            self.stdout.write(f"  User {user_id}: no hexagons. Skipping.")
            return

        xmin, ymin, xmax, ymax = row
        total_tiles = 0

        for zoom in range(zoom_min, zoom_max + 1):
            clamped_ymin = max(ymin, -85.05)
            clamped_ymax = min(ymax, 85.05)

            tx_min = lng_to_tile_x(xmin, zoom)
            tx_max = lng_to_tile_x(xmax, zoom)
            ty_min = lat_to_tile_y(clamped_ymax, zoom)
            ty_max = lat_to_tile_y(clamped_ymin, zoom)

            zoom_count = 0

            for tx in range(tx_min, tx_max + 1):
                for ty in range(ty_min, ty_max + 1):
                    west, south, east, north = tile_to_bbox(tx, ty, zoom)

                    with connection.cursor() as cursor:
                        cursor.execute(
                            _USER_HEXAGONS_FOR_TILE_SQL,
                            [west, south, east, north, user_id],
                        )
                        hexagons = cursor.fetchall()

                    if not hexagons:
                        continue

                    img = Image.new("RGBA", (TILE_SIZE, TILE_SIZE), (0, 0, 0, 0))
                    draw = ImageDraw.Draw(img)

                    for _hex_id, geom_wkt, _points in hexagons:
                        coords = parse_wkt_polygon(geom_wkt)
                        pixels = [
                            lnglat_to_pixel(lng, lat, west, south, east, north)
                            for lng, lat in coords
                        ]
                        draw.polygon(pixels, fill=FILL_COLOR, outline=OUTLINE_COLOR)

                    tile_path = tiles_dir / str(zoom) / str(tx) / f"{ty}.png"
                    tile_path.parent.mkdir(parents=True, exist_ok=True)
                    img.save(tile_path, "PNG")
                    zoom_count += 1

            total_tiles += zoom_count

        self.stdout.write(f"  User {user_id}: {total_tiles} tiles generated.")
