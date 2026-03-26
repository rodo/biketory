import json
from pathlib import Path

from django.db import connection
from django.http import Http404
from django.shortcuts import render

from traces.base62 import base62_to_uuid
from traces.models import Hexagon, HexagonScore, UserSurfaceStats

_SQL_DIR = Path(__file__).resolve().parent.parent / "sql"
_SHARE_USER_STATS_SQL = (_SQL_DIR / "share_user_stats.sql").read_text()


def shared_profile(request, code):
    try:
        secret = base62_to_uuid(code)
    except (ValueError, OverflowError) as exc:
        raise Http404 from exc

    try:
        stats = UserSurfaceStats.objects.select_related("user").get(secret_uuid=secret)
    except UserSurfaceStats.DoesNotExist as exc:
        raise Http404 from exc

    user = stats.user

    with connection.cursor() as cursor:
        cursor.execute(_SHARE_USER_STATS_SQL, [user.id])
        row = cursor.fetchone()

    username = row[0]
    traces_count = row[1]
    hexagons_count = row[2]
    total_points = row[3]

    hexagon_ids = HexagonScore.objects.filter(user=user).values_list("hexagon_id", flat=True)
    hexagons = Hexagon.objects.filter(pk__in=hexagon_ids)

    score_map = {
        s.hexagon_id: s.points
        for s in HexagonScore.objects.filter(user=user)
    }

    hexagons_geojson = json.dumps({
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "geometry": json.loads(h.geom.geojson),
                "properties": {"points": score_map.get(h.pk, 0)},
            }
            for h in hexagons
        ],
    })

    return render(request, "traces/share.html", {
        "username": username,
        "traces_count": traces_count,
        "hexagons_count": hexagons_count,
        "total_points": total_points,
        "hexagons_geojson": hexagons_geojson,
    })
