"""Reusable tile generation for hexagon PNG tiles."""

import logging
import time
from pathlib import Path

from django.conf import settings
from django.db import connection
from PIL import Image, ImageDraw, ImageFont

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

# Global tiles: coral, opacity varies by zoom
_GLOBAL_RGB = (232, 99, 111)

# User tiles: blue
_USER_RGB = (41, 128, 185)

# Opacity: two-slope piecewise linear interpolation with a knee at zoom 8.
# Steep slope from zoom_min to knee (200→140), gentle slope from knee to zoom_max (140→90).
_OPACITY_AT_MIN_ZOOM = 240
_OPACITY_AT_KNEE = 140
_OPACITY_AT_MAX_ZOOM = 90
_KNEE_ZOOM = 8
_OUTLINE_OPACITY = 240


def _get_opacity(zoom):
    zoom_min = settings.TILES_STATIC_MIN_ZOOM
    zoom_max = settings.TILES_STATIC_MAX_ZOOM
    if zoom_max == zoom_min:
        return _OPACITY_AT_MIN_ZOOM
    zoom = max(zoom_min, min(zoom_max, zoom))
    if zoom <= _KNEE_ZOOM:
        if _KNEE_ZOOM == zoom_min:
            return _OPACITY_AT_MIN_ZOOM
        t = (zoom - zoom_min) / (_KNEE_ZOOM - zoom_min)
        return int(_OPACITY_AT_MIN_ZOOM + t * (_OPACITY_AT_KNEE - _OPACITY_AT_MIN_ZOOM))
    t = (zoom - _KNEE_ZOOM) / (zoom_max - _KNEE_ZOOM)
    return int(_OPACITY_AT_KNEE + t * (_OPACITY_AT_MAX_ZOOM - _OPACITY_AT_KNEE))


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

            tile_path = tiles_dir / str(zoom) / str(tx) / f"{ty}.png"

            if not hexagons:
                tile_path.unlink(missing_ok=True)
                continue

            img = Image.new("RGBA", (TILE_SIZE, TILE_SIZE), (0, 0, 0, 0))
            draw = ImageDraw.Draw(img)

            opacity = _get_opacity(zoom)
            fill = _GLOBAL_RGB + (opacity,)
            outline = _GLOBAL_RGB + (_OUTLINE_OPACITY,)

            for _hex_id, geom_wkt, _max_points in hexagons:
                coords = parse_wkt_polygon(geom_wkt)
                pixels = [
                    lnglat_to_pixel(lng, lat, tile_west, tile_south, tile_east, tile_north)
                    for lng, lat in coords
                ]
                draw.polygon(pixels, fill=fill, outline=outline)

            tile_path.parent.mkdir(parents=True, exist_ok=True)
            img.save(tile_path, "PNG")
            count += 1

    return count


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

            tile_path = tiles_dir / str(zoom) / str(tx) / f"{ty}.png"

            if not hexagons:
                tile_path.unlink(missing_ok=True)
                continue

            img = Image.new("RGBA", (TILE_SIZE, TILE_SIZE), (0, 0, 0, 0))
            draw = ImageDraw.Draw(img)

            opacity = _get_opacity(zoom)
            fill = _USER_RGB + (opacity,)
            outline = _USER_RGB + (_OUTLINE_OPACITY,)

            for _hex_id, geom_wkt, _points in hexagons:
                coords = parse_wkt_polygon(geom_wkt)
                pixels = [
                    lnglat_to_pixel(lng, lat, tile_west, tile_south, tile_east, tile_north)
                    for lng, lat in coords
                ]
                draw.polygon(pixels, fill=fill, outline=outline)

            tile_path.parent.mkdir(parents=True, exist_ok=True)
            img.save(tile_path, "PNG")
            count += 1

    elapsed = time.monotonic() - start
    logger.info(
        "User %d (%s) zoom %d: %d tiles in %.2fs",
        user_id, hexagram, zoom, count, elapsed,
    )
    return count


# Score tiles: font size interpolated linearly from zoom 14→12px to zoom 18→20px
_SCORE_FONT_SIZE_MIN_ZOOM = 14
_SCORE_FONT_SIZE_MIN = 12
_SCORE_FONT_SIZE_MAX_ZOOM = 18
_SCORE_FONT_SIZE_MAX = 20
_SCORE_FONT_PATH = "/usr/share/fonts/truetype/noto/NotoSans-Bold.ttf"

# 8 directions for dark outline around text
_OUTLINE_OFFSETS = [
    (-1, -1), (-1, 0), (-1, 1),
    (0, -1),           (0, 1),
    (1, -1),  (1, 0),  (1, 1),
]


def _score_font(zoom):
    """Return a Noto Sans Bold font sized for the given zoom level."""
    if zoom <= _SCORE_FONT_SIZE_MIN_ZOOM:
        size = _SCORE_FONT_SIZE_MIN
    elif zoom >= _SCORE_FONT_SIZE_MAX_ZOOM:
        size = _SCORE_FONT_SIZE_MAX
    else:
        t = (zoom - _SCORE_FONT_SIZE_MIN_ZOOM) / (_SCORE_FONT_SIZE_MAX_ZOOM - _SCORE_FONT_SIZE_MIN_ZOOM)
        size = int(_SCORE_FONT_SIZE_MIN + t * (_SCORE_FONT_SIZE_MAX - _SCORE_FONT_SIZE_MIN))
    return ImageFont.truetype(_SCORE_FONT_PATH, size)


def generate_score_tiles_for_bbox(zoom, west, south, east, north):
    """Generate PNG tiles with score labels at hexagon centroids.

    Returns the number of tiles generated.
    """
    if zoom < settings.TILES_SCORE_MIN_ZOOM:
        return 0

    tiles_dir = Path(settings.MEDIA_ROOT) / "tiles" / "scores"

    clamped_south = max(south, -85.05)
    clamped_north = min(north, 85.05)

    tx_min = lng_to_tile_x(west, zoom)
    tx_max = lng_to_tile_x(east, zoom)
    ty_min = lat_to_tile_y(clamped_north, zoom)
    ty_max = lat_to_tile_y(clamped_south, zoom)

    font = _score_font(zoom)

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

            tile_path = tiles_dir / str(zoom) / str(tx) / f"{ty}.png"

            if not hexagons:
                tile_path.unlink(missing_ok=True)
                continue

            img = Image.new("RGBA", (TILE_SIZE, TILE_SIZE), (0, 0, 0, 0))
            draw = ImageDraw.Draw(img)

            for _hex_id, geom_wkt, max_points in hexagons:
                coords = parse_wkt_polygon(geom_wkt)
                pixels = [
                    lnglat_to_pixel(lng, lat, tile_west, tile_south, tile_east, tile_north)
                    for lng, lat in coords
                ]
                # Centroid: average of coords (skip last closing point)
                cx = sum(p[0] for p in pixels[:-1]) / (len(pixels) - 1)
                cy = sum(p[1] for p in pixels[:-1]) / (len(pixels) - 1)

                label = str(max_points)
                bbox = font.getbbox(label)
                tw = bbox[2] - bbox[0]
                th = bbox[3] - bbox[1]
                x = cx - tw / 2
                y = cy - th / 2

                # Dark outline (black in 8 directions)
                for dx, dy in _OUTLINE_OFFSETS:
                    draw.text((x + dx, y + dy), label, fill=(0, 0, 0, 255), font=font)
                # White text on top
                draw.text((x, y), label, fill=(255, 255, 255, 255), font=font)

            tile_path.parent.mkdir(parents=True, exist_ok=True)
            img.save(tile_path, "PNG")
            count += 1

    return count
