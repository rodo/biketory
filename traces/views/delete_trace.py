import logging
from pathlib import Path

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.db import connection
from django.shortcuts import get_object_or_404, redirect
from procrastinate.exceptions import AlreadyEnqueued

from challenges.models import TraceChallengeContribution
from traces.models import Trace

logger = logging.getLogger(__name__)

_SQL_DIR = Path(__file__).resolve().parent.parent / "sql"
_REVOKE_HEXAGON_POINTS_SQL = (_SQL_DIR / "revoke_hexagon_points.sql").read_text()
_REFRESH_HEXAGON_OWNERS_BBOX_SQL = (_SQL_DIR / "refresh_hexagon_owners_bbox.sql").read_text()

_CHALLENGES_SQL_DIR = Path(__file__).resolve().parent.parent.parent / "challenges" / "sql"
_REVOKE_DATASET_SCORES_SQL = (_CHALLENGES_SQL_DIR / "revoke_dataset_scores_for_trace.sql").read_text()


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

        with connection.cursor() as cursor:
            cursor.execute(_REVOKE_DATASET_SCORES_SQL, [trace.pk])

        # Collect impacted challenge IDs before cascade deletes contributions
        impacted_challenge_ids = list(
            TraceChallengeContribution.objects.filter(trace=trace)
            .values_list("challenge_id", flat=True)
        )

        trace.delete()

        if bbox:
            west, south, east, north = bbox.extent
            with connection.cursor() as cursor:
                cursor.execute(_REFRESH_HEXAGON_OWNERS_BBOX_SQL, [west, south, east, north])
            _defer_tile_regeneration(bbox, user)

        _defer_leaderboard_recomputation()
        if impacted_challenge_ids:
            _defer_challenge_recomputation(impacted_challenge_ids)

    return redirect("trace_list")


def _defer_leaderboard_recomputation():
    """Queue leaderboard recomputation after trace deletion."""
    from django.db import transaction

    from traces.tasks import recompute_leaderboard

    def _do_defer():
        try:
            recompute_leaderboard.defer()
        except AlreadyEnqueued:
            pass

    transaction.on_commit(_do_defer)


def _defer_challenge_recomputation(challenge_ids):
    """Queue leaderboard recomputation for challenges impacted by trace deletion."""
    from django.db import transaction

    from challenges.tasks import compute_single_challenge_leaderboard

    def _do_defer():
        for pk in challenge_ids:
            try:
                compute_single_challenge_leaderboard.configure(
                    queueing_lock=f"challenge_leaderboard_{pk}",
                ).defer(challenge_id=pk)
            except AlreadyEnqueued:
                pass

    transaction.on_commit(_do_defer)


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
