import json

from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.gis.geos import Polygon
from django.db import connection
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods

from traces.models import Hexagon
from traces.trace_processing import _HEX_SIDE_M, _INSERT_HEXAGONS_SQL

MIN_ZOOM_FOR_GENERATION = 14


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
        zoom = int(request.GET.get("zoom", 0))
        if zoom < MIN_ZOOM_FOR_GENERATION:
            return JsonResponse(
                {"error": f"Zoom must be >= {MIN_ZOOM_FOR_GENERATION}"},
                status=400,
            )
        with connection.cursor() as cursor:
            cursor.execute(_INSERT_HEXAGONS_SQL, [_HEX_SIDE_M, bbox_geom.wkt])

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
