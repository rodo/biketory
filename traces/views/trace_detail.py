import json

from django.contrib.auth.decorators import login_required
from django.contrib.gis.db.models import Union
from django.shortcuts import get_object_or_404, render

from traces.models import Hexagon, HexagonScore, Trace


@login_required
def trace_detail(request, pk):
    trace = get_object_or_404(Trace, pk=pk)
    surfaces = trace.closed_surfaces.all()

    surface_union = surfaces.aggregate(u=Union("polygon"))["u"]
    hexagons = Hexagon.objects.filter(geom__within=surface_union) if surface_union else Hexagon.objects.none()

    route_geojson = json.dumps({
        "type": "Feature",
        "geometry": json.loads(trace.route.geojson),
        "properties": {},
    }) if trace.route else "null"

    surfaces_geojson = json.dumps({
        "type": "FeatureCollection",
        "features": [
            {"type": "Feature", "geometry": json.loads(s.polygon.geojson), "properties": {}}
            for s in surfaces
        ],
    })

    owner_username = trace.uploaded_by.username if trace.uploaded_by else ""

    scores = {
        s.hexagon_id: s.points
        for s in HexagonScore.objects.filter(hexagon__in=hexagons, user=trace.uploaded_by)
    }

    hexagons_geojson = json.dumps({
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "geometry": json.loads(h.geom.geojson),
                "properties": {"username": owner_username, "points": scores.get(h.pk, 0)},
            }
            for h in hexagons
        ],
    })

    prev_trace = Trace.objects.filter(uploaded_at__lt=trace.uploaded_at).order_by("-uploaded_at").first()
    next_trace = Trace.objects.filter(uploaded_at__gt=trace.uploaded_at).order_by("uploaded_at").first()

    return render(request, "traces/trace_detail.html", {
        "trace": trace,
        "route_geojson": route_geojson,
        "surfaces_geojson": surfaces_geojson,
        "hexagons_geojson": hexagons_geojson,
        "owner_username": owner_username,
        "surfaces_count": surfaces.count(),
        "hexagons_count": hexagons.count(),
        "prev_trace": prev_trace,
        "next_trace": next_trace,
    })
