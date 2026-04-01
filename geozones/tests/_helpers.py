from django.contrib.auth.models import User
from django.contrib.gis.geos import MultiPolygon, Polygon
from django.utils import timezone

from geozones.models import GeoZone, ZoneLeaderboardEntry

_counter = 0


def _next_code():
    global _counter
    _counter += 1
    return f"Z{_counter:04d}"


def square_multipolygon(cx=2.3, cy=48.8, half=0.5):
    """Small square MultiPolygon for tests."""
    poly = Polygon([
        (cx - half, cy - half),
        (cx + half, cy - half),
        (cx + half, cy + half),
        (cx - half, cy + half),
        (cx - half, cy - half),
    ])
    return MultiPolygon(poly)


def make_zone(code=None, name=None, admin_level=2, parent=None, active=False, geom=None):
    if code is None:
        code = _next_code()
    if name is None:
        name = f"Zone {code}"
    if geom is None:
        geom = square_multipolygon()
    return GeoZone.objects.create(
        code=code,
        name=name,
        admin_level=admin_level,
        parent=parent,
        active=active,
        geom=geom,
    )


def make_entry(zone, user_id=1, username="user1", conquered=5, acquired=3,
               rank_conquered=1, rank_acquired=1, is_premium=False):
    return ZoneLeaderboardEntry.objects.create(
        zone=zone,
        user_id=user_id,
        username=username,
        is_premium=is_premium,
        hexagons_conquered=conquered,
        hexagons_acquired=acquired,
        rank_conquered=rank_conquered,
        rank_acquired=rank_acquired,
        computed_at=timezone.now(),
    )


def make_user(username="alice", password="pass"):
    user = User.objects.create_user(username=username, password=password)
    user.refresh_from_db()
    return user


def make_superuser(username="admin", password="pass"):
    user = User.objects.create_superuser(username=username, password=password)
    user.refresh_from_db()
    return user
