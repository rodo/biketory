from pathlib import Path

from django.contrib.auth.decorators import login_required
from django.db import connection
from django.shortcuts import get_object_or_404, redirect

from traces.models import Trace

_SQL_DIR = Path(__file__).resolve().parent.parent / "sql"
_REVOKE_HEXAGON_POINTS_SQL = (_SQL_DIR / "revoke_hexagon_points.sql").read_text()


@login_required
def delete_trace(request, pk):
    trace = get_object_or_404(Trace, pk=pk)
    if request.method == "POST":
        user = trace.uploaded_by
        if user:
            for surface in trace.closed_surfaces.all():
                with connection.cursor() as cursor:
                    cursor.execute(_REVOKE_HEXAGON_POINTS_SQL, (surface.polygon.wkt, user.pk))
        trace.delete()
    return redirect("trace_list")
