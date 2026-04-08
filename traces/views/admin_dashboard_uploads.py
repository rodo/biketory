import json
from itertools import accumulate
from pathlib import Path

from django.contrib.auth.decorators import user_passes_test
from django.db import connection
from django.shortcuts import render

_SQL_DIR = Path(__file__).resolve().parent.parent / "sql"
_UPLOADS_SQL = (_SQL_DIR / "admin_traces_uploaded.sql").read_text()

VALID_GRANULARITIES = {"day", "week", "month", "year"}


@user_passes_test(lambda u: u.is_superuser)
def admin_dashboard_uploads(request):
    granularity = request.GET.get("granularity", "month")
    if granularity not in VALID_GRANULARITIES:
        granularity = "month"

    with connection.cursor() as cursor:
        cursor.execute(_UPLOADS_SQL, [granularity])
        rows = cursor.fetchall()

    labels = [row[0].strftime("%Y-%m-%d") for row in rows]
    traces_uploaded = [row[1] for row in rows]
    cumulative = list(accumulate(traces_uploaded))

    chart_data = json.dumps(
        {
            "labels": labels,
            "traces_uploaded": traces_uploaded,
            "cumulative": cumulative,
        }
    )

    return render(
        request,
        "traces/admin_dashboard_uploads.html",
        {
            "chart_data": chart_data,
            "granularity": granularity,
        },
    )
