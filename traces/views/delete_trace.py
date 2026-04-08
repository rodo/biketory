import logging
from pathlib import Path

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.db import connection
from django.shortcuts import get_object_or_404, redirect
from procrastinate.exceptions import AlreadyEnqueued

from traces.models import Trace

logger = logging.getLogger(__name__)

_SQL_DIR = Path(__file__).resolve().parent.parent / "sql"
_REVOKE_HEXAGON_POINTS_SQL = (_SQL_DIR / "revoke_hexagon_points.sql").read_text()


@login_required
def delete_trace(request, pk):
    trace = get_object_or_404(Trace, pk=pk)
    if request.method == "POST":
        user = trace.uploaded_by
        bbox = trace.bbox

        if user:
            for surface in trace.closed_surfaces.all():
                with connection.cursor() as cursor:
                    cursor.execute(_REVOKE_HEXAGON_POINTS_SQL, (surface.polygon.wkt, user.pk))

        trace.delete()

        if bbox:
            _defer_tile_regeneration(bbox, user)

    return redirect("trace_list")


def _defer_tile_regeneration(bbox, user):
    """Queue tile regeneration tasks for the deleted trace's bounding box."""
    from traces.tasks import (
        regenerate_score_tiles_for_bbox,
        regenerate_tiles_for_bbox,
        regenerate_user_tiles_for_bbox,
    )

    west, south, east, north = bbox.extent

    for zoom in range(settings.TILES_STATIC_MIN_ZOOM, settings.TILES_STATIC_MAX_ZOOM + 1):
        try:
            regenerate_tiles_for_bbox.configure(
                queueing_lock=f"regen_tiles_{west}_{south}_{zoom}",
            ).defer(west=west, south=south, east=east, north=north, zoom=zoom)
        except AlreadyEnqueued:
            pass

    for zoom in range(settings.TILES_SCORE_MIN_ZOOM, settings.MAP_ZOOM_MAX + 1):
        try:
            regenerate_score_tiles_for_bbox.configure(
                queueing_lock=f"regen_score_tiles_{west}_{south}_{zoom}",
            ).defer(west=west, south=south, east=east, north=north, zoom=zoom)
        except AlreadyEnqueued:
            pass

    if user and hasattr(user, "profile") and user.profile.is_premium:
        for zoom in range(settings.TILES_STATIC_MIN_ZOOM, settings.TILES_STATIC_MAX_ZOOM + 1):
            try:
                regenerate_user_tiles_for_bbox.configure(
                    queueing_lock=f"regen_user_tiles_{user.pk}_{west}_{south}_{zoom}",
                ).defer(user_id=user.pk, west=west, south=south, east=east, north=north, zoom=zoom)
            except AlreadyEnqueued:
                pass
