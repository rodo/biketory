import json
from collections import defaultdict

from django.db.models import Count
from django.db.models.functions import TruncMonth
from django.shortcuts import render

from traces.models import HexagonGainEvent

_COLORS = [
    "#2980b9", "#27ae60", "#e74c3c", "#f39c12", "#8e44ad",
    "#16a085", "#d35400", "#e84393", "#2c3e50", "#1abc9c",
]


def stats(request):
    qs = (
        HexagonGainEvent.objects
        .annotate(month=TruncMonth("earned_at"))
        .values("month", "user__username")
        .annotate(count=Count("id"))
        .order_by("month", "user__username")
    )

    months = []
    months_seen = set()
    users = []
    users_seen = set()

    for row in qs:
        m = row["month"].strftime("%Y-%m")
        u = row["user__username"]
        if m not in months_seen:
            months.append(m)
            months_seen.add(m)
        if u not in users_seen:
            users.append(u)
            users_seen.add(u)

    matrix = defaultdict(lambda: defaultdict(int))
    for row in qs:
        matrix[row["user__username"]][row["month"].strftime("%Y-%m")] = row["count"]

    datasets = [
        {
            "label": user,
            "data": [matrix[user][m] for m in months],
            "backgroundColor": _COLORS[i % len(_COLORS)],
        }
        for i, user in enumerate(users)
    ]

    return render(request, "traces/stats.html", {
        "chart_data": json.dumps({"labels": months, "datasets": datasets}),
    })
