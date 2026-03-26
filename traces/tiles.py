"""Shared tile-generation utilities used by management commands."""

import math

TILE_SIZE = 256


def lng_to_tile_x(lng, zoom):
    """Convert longitude to tile X number."""
    n = 2 ** zoom
    return int((lng + 180.0) / 360.0 * n)


def lat_to_tile_y(lat, zoom):
    """Convert latitude to tile Y number (OSM standard)."""
    n = 2 ** zoom
    lat_rad = math.radians(lat)
    return int(
        (1.0 - math.log(math.tan(lat_rad) + 1.0 / math.cos(lat_rad)) / math.pi)
        / 2.0
        * n
    )


def tile_to_bbox(x, y, zoom):
    """Return (west, south, east, north) for a tile."""
    n = 2 ** zoom
    west = x / n * 360.0 - 180.0
    east = (x + 1) / n * 360.0 - 180.0
    north_rad = math.atan(math.sinh(math.pi * (1 - 2 * y / n)))
    south_rad = math.atan(math.sinh(math.pi * (1 - 2 * (y + 1) / n)))
    north = math.degrees(north_rad)
    south = math.degrees(south_rad)
    return west, south, east, north


def lnglat_to_pixel(lng, lat, west, south, east, north):
    """Convert WGS84 coords to pixel coords within a 256x256 tile."""
    px = (lng - west) / (east - west) * TILE_SIZE

    def _merc_y(lat_deg):
        lat_rad = math.radians(lat_deg)
        return math.log(math.tan(lat_rad) + 1.0 / math.cos(lat_rad))

    y_north = _merc_y(north)
    y_south = _merc_y(south)
    y_point = _merc_y(lat)
    py = (y_north - y_point) / (y_north - y_south) * TILE_SIZE
    return px, py


def parse_wkt_polygon(wkt):
    """Parse a WKT POLYGON into a list of (lng, lat) tuples."""
    inner = wkt.replace("POLYGON((", "").replace("))", "")
    coords = []
    for pair in inner.split(","):
        lng, lat = pair.strip().split()
        coords.append((float(lng), float(lat)))
    return coords
