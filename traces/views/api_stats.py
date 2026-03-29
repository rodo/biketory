from collections import defaultdict
from datetime import date

from django.http import JsonResponse
from django.utils.translation import gettext as _

from statistics.models import MonthlyStats, UserMonthlyStats

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
            "label": _("Hexagons acquired"),
            "data": [acquired_by_month.get(m, 0) for m in all_months],
            "backgroundColor": "#2980b9",
        },
        {
            "label": _("New hexagons"),
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
        "label": _("Traces"),
        "data": [by_month.get(m, 0) for m in all_months],
        "backgroundColor": "#e74c3c",
    }]

    return {"labels": all_months, "datasets": datasets}


def _build_per_user_data() -> dict:
    qs = UserMonthlyStats.objects.order_by("period", "user_id").values_list(
        "period", "user_id", "hexagons_acquired",
    )

    months = []
    months_seen = set()
    user_ids = []
    user_ids_seen = set()

    for period, user_id, _ in qs:
        m = period.strftime("%Y-%m")
        if m not in months_seen:
            months.append(m)
            months_seen.add(m)
        if user_id not in user_ids_seen:
            user_ids.append(user_id)
            user_ids_seen.add(user_id)

    matrix = defaultdict(lambda: defaultdict(int))
    for period, user_id, count in qs:
        matrix[user_id][period.strftime("%Y-%m")] = count

    from django.contrib.auth import get_user_model
    User = get_user_model()
    usernames = dict(
        User.objects.filter(id__in=user_ids).values_list("id", "username")
    )

    datasets = [
        {
            "label": usernames.get(uid, str(uid)),
            "data": [matrix[uid][m] for m in months],
            "backgroundColor": _COLORS[i % len(_COLORS)],
        }
        for i, uid in enumerate(user_ids)
    ]

    return {"labels": months, "datasets": datasets}


def api_stats_monthly(request):
    return JsonResponse(_build_monthly_data())


def api_stats_traces(request):
    return JsonResponse(_build_traces_data())


def api_stats(request):
    return JsonResponse(_build_per_user_data())
