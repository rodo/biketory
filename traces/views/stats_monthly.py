import json
from datetime import date, timedelta

from django.db import connection
from django.shortcuts import render
from django.utils import timezone

from traces.models import MonthlyStatsRefresh


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


def _ensure_fresh():
    now = timezone.now()
    record = MonthlyStatsRefresh.objects.first()
    if record is None or (now - record.refreshed_at) > timedelta(hours=24):
        with connection.cursor() as cursor:
            cursor.execute("REFRESH MATERIALIZED VIEW hexagon_monthly_stats")
        if record:
            record.refreshed_at = now
            record.save(update_fields=["refreshed_at"])
        else:
            MonthlyStatsRefresh.objects.create(refreshed_at=now)


def stats_monthly(request):
    _ensure_fresh()

    with connection.cursor() as cursor:
        cursor.execute("SELECT month, count FROM hexagon_monthly_stats ORDER BY month")
        rows = cursor.fetchall()

    if not rows:
        return render(request, "traces/stats_monthly.html", {
            "chart_data": json.dumps({"labels": [], "datasets": []}),
        })

    first_month = rows[0][0]
    today = date.today().replace(day=1)
    all_months = _all_months(first_month, today)

    by_month = {r[0].strftime("%Y-%m"): r[1] for r in rows}

    datasets = [{
        "label": "Hexagons",
        "data": [by_month.get(m, 0) for m in all_months],
        "backgroundColor": "#2980b9",
    }]

    return render(request, "traces/stats_monthly.html", {
        "chart_data": json.dumps({"labels": all_months, "datasets": datasets}),
    })
