from collections import defaultdict
from datetime import date

from django.db.models import Count
from django.db.models.functions import TruncMonth
from django.http import JsonResponse

from statistics.models import MonthlyStats
from traces.models import HexagonGainEvent

_COLORS = [
    "#2980b9", "#27ae60", "#e74c3c", "#f39c12", "#8e44ad",
    "#16a085", "#d35400", "#e84393", "#2c3e50", "#1abc9c",
]


def _all_months(first: date, last: date) -> list[str]:
    months = []
    y, m = first.year, first.month
    while (y, m) <= (last.year, last.month):
        months.append(f"{y:04d}-{m:02d}")
        m += 1
        if m > 12:
            m = 1
            y += 1
    return months


def _build_monthly_data() -> dict:
    rows = MonthlyStats.objects.order_by("period").values_list(
        "period", "hexagons_acquired", "new_hexagons_acquired",
    )

    if not rows:
        return {"labels": [], "datasets": []}

    first_month = rows[0][0]
    today = date.today().replace(day=1)
    all_months = _all_months(first_month, today)

    acquired_by_month = {r[0].strftime("%Y-%m"): r[1] for r in rows}
    new_by_month = {r[0].strftime("%Y-%m"): r[2] for r in rows}

    datasets = [
        {
            "label": "Hexagons acquis",
            "data": [acquired_by_month.get(m, 0) for m in all_months],
            "backgroundColor": "#2980b9",
        },
        {
            "label": "Nouveaux hexagons",
            "data": [new_by_month.get(m, 0) for m in all_months],
            "backgroundColor": "#27ae60",
        },
    ]

    return {"labels": all_months, "datasets": datasets}


def _build_traces_data() -> dict:
    rows = MonthlyStats.objects.order_by("period").values_list(
        "period", "traces_uploaded",
    )

    if not rows:
        return {"labels": [], "datasets": []}

    first_month = rows[0][0]
    today = date.today().replace(day=1)
    all_months = _all_months(first_month, today)

    by_month = {r[0].strftime("%Y-%m"): r[1] for r in rows}

    datasets = [{
        "label": "Traces",
        "data": [by_month.get(m, 0) for m in all_months],
        "backgroundColor": "#e74c3c",
    }]

    return {"labels": all_months, "datasets": datasets}


def _build_per_user_data() -> dict:
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

    return {"labels": months, "datasets": datasets}


def api_stats_monthly(request):
    return JsonResponse(_build_monthly_data())


def api_stats_traces(request):
    return JsonResponse(_build_traces_data())


def api_stats(request):
    return JsonResponse(_build_per_user_data())
