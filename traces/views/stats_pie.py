import json
from datetime import date

from django.shortcuts import render

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


def stats_traces(request):
    rows = MonthlyStats.objects.order_by("period").values_list(
        "period", "traces_uploaded",
    )

    if not rows:
        return render(request, "traces/stats_traces.html", {
            "chart_data": json.dumps({"labels": [], "datasets": []}),
        })

    first_month = rows[0][0]
    today = date.today().replace(day=1)
    all_months = _all_months(first_month, today)

    by_month = {r[0].strftime("%Y-%m"): r[1] for r in rows}

    datasets = [{
        "label": "Traces",
        "data": [by_month.get(m, 0) for m in all_months],
        "backgroundColor": "#e74c3c",
    }]

    return render(request, "traces/stats_traces.html", {
        "chart_data": json.dumps({"labels": all_months, "datasets": datasets}),
    })
