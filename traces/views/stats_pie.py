import json

from django.db.models import Count
from django.shortcuts import render

from traces.models import HexagonScore

_COLORS = [
    "#2980b9", "#27ae60", "#e74c3c", "#f39c12", "#8e44ad",
    "#16a085", "#d35400", "#e84393", "#2c3e50", "#1abc9c",
]


def stats_pie(request):
    qs = (
        HexagonScore.objects
        .values("user__username")
        .annotate(count=Count("hexagon"))
        .order_by("-count")
    )

    labels = [row["user__username"] for row in qs]
    data = [row["count"] for row in qs]
    colors = [_COLORS[i % len(_COLORS)] for i in range(len(labels))]

    return render(request, "traces/stats_pie.html", {
        "chart_data": json.dumps({
            "labels": labels,
            "datasets": [{"data": data, "backgroundColor": colors}],
        }),
    })
