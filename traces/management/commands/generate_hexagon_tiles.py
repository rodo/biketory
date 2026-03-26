import shutil
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand
from django.db import connection
from PIL import Image, ImageDraw

from traces.tiles import (
    TILE_SIZE,
    lat_to_tile_y,
    lng_to_tile_x,
    lnglat_to_pixel,
    parse_wkt_polygon,
    tile_to_bbox,
)

_SQL_DIR = Path(__file__).resolve().parent.parent.parent / "sql"
_HEXAGONS_EXTENT_SQL = (_SQL_DIR / "hexagons_extent.sql").read_text()
_HEXAGONS_FOR_TILE_SQL = (_SQL_DIR / "hexagons_for_tile.sql").read_text()

# Color gradient by max_points (R, G, B, A)
COLORS = [
    (10, (74, 94, 76, 160)),   # >= 10 : #4a5e4c
    (5, (107, 125, 108, 160)),  # >= 5  : #6b7d6c
    (2, (138, 158, 139, 160)),  # >= 2  : #8a9e8b
    (0, (176, 191, 177, 160)),  # < 2   : #b0bfb1
]


def _get_color(max_points):
    for threshold, color in COLORS:
        if max_points >= threshold:
            return color
    return COLORS[-1][1]


class Command(BaseCommand):
    help = "Generate static PNG tiles for hexagons at low zoom levels"

    def add_arguments(self, parser):
        parser.add_argument(
            "--zoom-min", type=int, default=0,
            help="Minimum zoom level (default: 0)",
        )
        parser.add_argument(
            "--zoom-max", type=int, default=settings.HEXAGON_TILE_MAX_ZOOM,
            help="Maximum zoom level (default: HEXAGON_TILE_MAX_ZOOM)",
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
            self.stdout.write("Cleaned existing tiles.")

        # Get global extent
        with connection.cursor() as cursor:
            cursor.execute(_HEXAGONS_EXTENT_SQL)
            row = cursor.fetchone()

        if row is None or row[0] is None:
            self.stdout.write("No hexagons with scores found. Nothing to generate.")
            return

        xmin, ymin, xmax, ymax = row
        self.stdout.write(f"Extent: ({xmin:.4f}, {ymin:.4f}) — ({xmax:.4f}, {ymax:.4f})")

        total_tiles = 0

        for zoom in range(zoom_min, zoom_max + 1):
            # Clamp latitudes to avoid math domain errors near poles
            clamped_ymin = max(ymin, -85.05)
            clamped_ymax = min(ymax, 85.05)

            tx_min = lng_to_tile_x(xmin, zoom)
            tx_max = lng_to_tile_x(xmax, zoom)
            ty_min = lat_to_tile_y(clamped_ymax, zoom)  # note: y is inverted
            ty_max = lat_to_tile_y(clamped_ymin, zoom)

            zoom_count = 0

            for tx in range(tx_min, tx_max + 1):
                for ty in range(ty_min, ty_max + 1):
                    west, south, east, north = tile_to_bbox(tx, ty, zoom)

                    with connection.cursor() as cursor:
                        cursor.execute(_HEXAGONS_FOR_TILE_SQL, [west, south, east, north])
                        hexagons = cursor.fetchall()

                    if not hexagons:
                        continue

                    img = Image.new("RGBA", (TILE_SIZE, TILE_SIZE), (0, 0, 0, 0))
                    draw = ImageDraw.Draw(img)

                    for _hex_id, geom_wkt, max_points in hexagons:
                        coords = parse_wkt_polygon(geom_wkt)
                        pixels = [
                            lnglat_to_pixel(lng, lat, west, south, east, north)
                            for lng, lat in coords
                        ]
                        color = _get_color(max_points)
                        draw.polygon(pixels, fill=color, outline=color[:3] + (200,))

                    tile_path = tiles_dir / str(zoom) / str(tx) / f"{ty}.png"
                    tile_path.parent.mkdir(parents=True, exist_ok=True)
                    img.save(tile_path, "PNG")
                    zoom_count += 1

            total_tiles += zoom_count
            self.stdout.write(f"Zoom {zoom}: {zoom_count} tiles generated")

        self.stdout.write(self.style.SUCCESS(f"Done. {total_tiles} tiles generated."))
