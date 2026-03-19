import json

from django.contrib.auth.decorators import login_required
from django.contrib.gis.db.models import Union
from django.shortcuts import get_object_or_404, render

from traces.models import Hexagon, HexagonScore, Trace

COLORS = [
    "#e74c3c", "#2980b9", "#27ae60", "#f39c12", "#8e44ad",
    "#16a085", "#d35400", "#2c3e50", "#c0392b", "#1abc9c",
]


@login_required
def trace_surfaces(request, pk):
    trace = get_object_or_404(Trace, pk=pk)
    surfaces = list(trace.closed_surfaces.order_by("segment_index"))

    features = []
    for i, surface in enumerate(surfaces):
        color = COLORS[i % len(COLORS)]
        features.append({
            "type": "Feature",
            "geometry": json.loads(surface.polygon.geojson),
            "properties": {
                "index": surface.segment_index,
                "color": color,
                "area": round(surface.polygon.area, 8),
            },
        })

    surfaces_geojson = json.dumps({"type": "FeatureCollection", "features": features})

    route_geojson = json.dumps({
        "type": "Feature",
        "geometry": json.loads(trace.route.geojson),
        "properties": {},
    }) if trace.route else "null"

    surface_union = trace.closed_surfaces.aggregate(u=Union("polygon"))["u"]
    hexagons = Hexagon.objects.filter(geom__within=surface_union) if surface_union else Hexagon.objects.none()

    scores = {
        s.hexagon_id: s.points
        for s in HexagonScore.objects.filter(hexagon__in=hexagons, user=trace.uploaded_by)
    }
    owner_username = trace.uploaded_by.username if trace.uploaded_by else ""

    hexagons_geojson = json.dumps({
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "geometry": json.loads(h.geom.geojson),
                "properties": {"points": scores.get(h.pk, 0), "username": owner_username},
            }
            for h in hexagons
        ],
    })

    return render(request, "traces/trace_surfaces.html", {
        "trace": trace,
        "surfaces": surfaces,
        "colors": [COLORS[i % len(COLORS)] for i in range(len(surfaces))],
        "surfaces_geojson": surfaces_geojson,
        "route_geojson": route_geojson,
        "hexagons_geojson": hexagons_geojson,
    })
