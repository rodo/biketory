from datetime import date

from django.http import JsonResponse
from django.utils.translation import gettext as _

from statistics.models import MonthlyStats


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


def api_stats_monthly(request):
    return JsonResponse(_build_monthly_data())


def api_stats_traces(request):
    return JsonResponse(_build_traces_data())
