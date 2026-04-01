"""Reusable tile generation for hexagon PNG tiles."""

import logging
import time
from pathlib import Path

from django.conf import settings
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

logger = logging.getLogger(__name__)

_SQL_DIR = Path(__file__).resolve().parent / "sql"
_HEXAGONS_FOR_TILE_SQL = (_SQL_DIR / "hexagons_for_tile.sql").read_text()
_USER_HEXAGONS_EXTENT_SQL = (_SQL_DIR / "user_hexagons_extent.sql").read_text()
_USER_HEXAGONS_FOR_TILE_SQL = (_SQL_DIR / "user_hexagons_for_tile.sql").read_text()

# Color gradient by max_points (R, G, B, A)
COLORS = [
    (10, (180, 90, 0, 160)),    # >= 10 : #b45a00
    (5, (210, 120, 20, 160)),   # >= 5  : #d27814
    (2, (230, 155, 50, 160)),   # >= 2  : #e69b32
    (0, (245, 190, 90, 160)),   # < 2   : #f5be5a
]


def _get_color(max_points):
    for threshold, color in COLORS:
        if max_points >= threshold:
            return color
    return COLORS[-1][1]


def generate_tiles_for_bbox(zoom, west, south, east, north):
    """Generate PNG tiles for a single zoom level within a bounding box.

    Returns the number of tiles generated.
    """
    tiles_dir = Path(settings.MEDIA_ROOT) / "tiles"

    clamped_south = max(south, -85.05)
    clamped_north = min(north, 85.05)

    tx_min = lng_to_tile_x(west, zoom)
    tx_max = lng_to_tile_x(east, zoom)
    ty_min = lat_to_tile_y(clamped_north, zoom)  # y is inverted
    ty_max = lat_to_tile_y(clamped_south, zoom)

    count = 0

    for tx in range(tx_min, tx_max + 1):
        for ty in range(ty_min, ty_max + 1):
            tile_west, tile_south, tile_east, tile_north = tile_to_bbox(tx, ty, zoom)

            with connection.cursor() as cursor:
                cursor.execute(
                    _HEXAGONS_FOR_TILE_SQL,
                    [tile_west, tile_south, tile_east, tile_north],
                )
                hexagons = cursor.fetchall()

            if not hexagons:
                continue

            img = Image.new("RGBA", (TILE_SIZE, TILE_SIZE), (0, 0, 0, 0))
            draw = ImageDraw.Draw(img)

            for _hex_id, geom_wkt, max_points in hexagons:
                coords = parse_wkt_polygon(geom_wkt)
                pixels = [
                    lnglat_to_pixel(lng, lat, tile_west, tile_south, tile_east, tile_north)
                    for lng, lat in coords
                ]
                color = _get_color(max_points)
                draw.polygon(pixels, fill=color, outline=color[:3] + (200,))

            tile_path = tiles_dir / str(zoom) / str(tx) / f"{ty}.png"
            tile_path.parent.mkdir(parents=True, exist_ok=True)
            img.save(tile_path, "PNG")
            count += 1

    return count


# User-specific tiles (blue, single color)
USER_FILL_COLOR = (41, 128, 185, 160)
USER_OUTLINE_COLOR = (41, 128, 185, 200)


def generate_user_tiles_for_bbox(user_id, hexagram, zoom, west, south, east, north):
    """Generate per-user PNG tiles for a single zoom level within a bounding box.

    Returns the number of tiles generated.
    """
    start = time.monotonic()
    tiles_dir = Path(settings.MEDIA_ROOT) / "tiles" / hexagram[0] / hexagram[1] / hexagram

    clamped_south = max(south, -85.05)
    clamped_north = min(north, 85.05)

    tx_min = lng_to_tile_x(west, zoom)
    tx_max = lng_to_tile_x(east, zoom)
    ty_min = lat_to_tile_y(clamped_north, zoom)
    ty_max = lat_to_tile_y(clamped_south, zoom)

    count = 0

    for tx in range(tx_min, tx_max + 1):
        for ty in range(ty_min, ty_max + 1):
            tile_west, tile_south, tile_east, tile_north = tile_to_bbox(tx, ty, zoom)

            with connection.cursor() as cursor:
                cursor.execute(
                    _USER_HEXAGONS_FOR_TILE_SQL,
                    [tile_west, tile_south, tile_east, tile_north, user_id],
                )
                hexagons = cursor.fetchall()

            if not hexagons:
                continue

            img = Image.new("RGBA", (TILE_SIZE, TILE_SIZE), (0, 0, 0, 0))
            draw = ImageDraw.Draw(img)

            for _hex_id, geom_wkt, _points in hexagons:
                coords = parse_wkt_polygon(geom_wkt)
                pixels = [
                    lnglat_to_pixel(lng, lat, tile_west, tile_south, tile_east, tile_north)
                    for lng, lat in coords
                ]
                draw.polygon(pixels, fill=USER_FILL_COLOR, outline=USER_OUTLINE_COLOR)

            tile_path = tiles_dir / str(zoom) / str(tx) / f"{ty}.png"
            tile_path.parent.mkdir(parents=True, exist_ok=True)
            img.save(tile_path, "PNG")
            count += 1

    elapsed = time.monotonic() - start
    logger.info(
        "User %d (%s) zoom %d: %d tiles in %.2fs",
        user_id, hexagram, zoom, count, elapsed,
    )
    return count
