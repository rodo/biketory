import json
from pathlib import Path

from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.gis.geos import Polygon
from django.db import connection
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods

from traces.models import Hexagon

_SQL_DIR = Path(__file__).resolve().parent.parent.parent / "traces" / "sql"
_INSERT_HEXAGONS_SQL = (_SQL_DIR / "insert_hexagons.sql").read_text()

# Hexagon edge size in meters (same as trace processing)
_HEX_EDGE = 200.0


@staff_member_required
@require_http_methods(["GET", "POST"])
def api_challenge_hexagons(request):
    """GET: list hexagons in bbox. POST: generate missing then list."""
    bbox_raw = request.GET.get("bbox", "")
    if not bbox_raw:
        return JsonResponse({"error": "bbox parameter required"}, status=400)

    try:
        west, south, east, north = [float(x) for x in bbox_raw.split(",")]
    except (ValueError, TypeError):
        return JsonResponse({"error": "Invalid bbox format"}, status=400)

    bbox_geom = Polygon.from_bbox((west, south, east, north))
    bbox_geom.srid = 4326

    if request.method == "POST":
        with connection.cursor() as cursor:
            cursor.execute(_INSERT_HEXAGONS_SQL, [_HEX_EDGE, bbox_geom.ewkt])

    hexagons = Hexagon.objects.filter(geom__intersects=bbox_geom).values_list(
        "pk", "geom", "owner_id"
    )

    features = []
    for pk, geom, owner_id in hexagons:
        features.append({
            "type": "Feature",
            "geometry": json.loads(geom.geojson),
            "properties": {"id": pk, "owner_id": owner_id},
        })

    return JsonResponse({
        "type": "FeatureCollection",
        "features": features,
    })
