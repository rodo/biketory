import json

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.contrib.gis.db.models import Union
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, render

from traces.badges import BADGE_CATALOGUE
from traces.models import Hexagon, HexagonScore, Trace, UserBadge


@login_required
def trace_detail(request, trace_uuid):
    trace = get_object_or_404(Trace, uuid=trace_uuid)
    surfaces = trace.closed_surfaces.all()

    surface_union = surfaces.aggregate(u=Union("polygon"))["u"]
    hexagons = Hexagon.objects.filter(geom__within=surface_union) if surface_union else Hexagon.objects.none()

    map_config = {
        "elementId": "map",
        "tileUrl": settings.TILE_SERVER_URL,
        "zoomMin": settings.MAP_ZOOM_MIN,
        "zoomMax": settings.MAP_ZOOM_MAX,
    }

    route_geojson = {
        "type": "Feature",
        "geometry": json.loads(trace.route.geojson),
        "properties": {},
    } if trace.route else None

    surfaces_geojson = {
        "type": "FeatureCollection",
        "features": [
            {"type": "Feature", "geometry": json.loads(s.polygon.geojson), "properties": {}}
            for s in surfaces
        ],
    }

    owner_username = trace.uploaded_by.username if trace.uploaded_by else ""

    scores = {
        s.hexagon_id: s.points
        for s in HexagonScore.objects.filter(hexagon__in=hexagons, user=trace.uploaded_by)
    }

    hexagons_geojson = {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "geometry": json.loads(h.geom.geojson),
                "properties": {"username": owner_username, "points": scores.get(h.pk, 0)},
            }
            for h in hexagons
        ],
    }

    prev_trace = Trace.objects.filter(uploaded_at__lt=trace.uploaded_at).order_by("-uploaded_at").first()
    next_trace = Trace.objects.filter(uploaded_at__gt=trace.uploaded_at).order_by("uploaded_at").first()

    # Badges earned on this trace
    badge_lookup = {}
    for cat in BADGE_CATALOGUE:
        for b in cat["badges"]:
            badge_lookup[b["id"]] = b
    earned_badges = [
        badge_lookup[ub.badge_id]
        for ub in UserBadge.objects.filter(trace=trace)
        if ub.badge_id in badge_lookup
    ]

    pending_before = 0
    if trace.status == Trace.STATUS_NOT_ANALYZED:
        pending_before = Trace.objects.filter(
            status=Trace.STATUS_NOT_ANALYZED,
            uploaded_at__lt=trace.uploaded_at,
        ).count()

    return render(request, "traces/trace_detail.html", {
        "trace": trace,
        "map_config": map_config,
        "route_geojson": route_geojson,
        "surfaces_geojson": surfaces_geojson,
        "hexagons_geojson": hexagons_geojson,
        "owner_username": owner_username,
        "surfaces_count": surfaces.count(),
        "hexagons_count": hexagons.count(),
        "prev_trace": prev_trace,
        "next_trace": next_trace,
        "earned_badges": earned_badges,
        "pending_before": pending_before,
    })


def api_trace_status(request, trace_uuid):
    status = Trace.objects.filter(uuid=trace_uuid).values_list("status", flat=True).first()
    if status is None:
        return JsonResponse({"error": "not found"}, status=404)
    return JsonResponse({"status": status})
