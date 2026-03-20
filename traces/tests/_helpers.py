from django.contrib.auth.models import User
from django.contrib.gis.geos import LineString, MultiLineString, Polygon


def make_user(username="alice", password="pass"):
    return User.objects.create_user(username=username, password=password)


def small_route():
    """A short two-point route near Paris (lon 2.3-2.4, lat 48.8-48.9)."""
    return MultiLineString(LineString([(2.30, 48.80), (2.40, 48.90)]))


def square_polygon(cx, cy, half):
    """Axis-aligned square polygon centred at (cx, cy)."""
    return Polygon([
        (cx - half, cy - half),
        (cx + half, cy - half),
        (cx + half, cy + half),
        (cx - half, cy + half),
        (cx - half, cy - half),
    ])
