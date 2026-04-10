import logging

from procrastinate.contrib.django import app
from procrastinate.exceptions import AlreadyEnqueued

from traces.badge_award import award_badges
from traces.models import Trace
from traces.tile_generation import (
    generate_score_tiles_for_bbox,
    generate_tiles_for_bbox,
    generate_user_tiles_for_bbox,
)
from traces.trace_processing import _extract_surfaces

logger = logging.getLogger(__name__)


@app.task(queue="surface_extraction")
def extract_surfaces(trace_id: int):
    """Extract closed surfaces from a trace and mark it as surface_extracted."""
    try:
        trace = Trace.objects.select_related("uploaded_by").get(pk=trace_id)
    except Trace.DoesNotExist:
        logger.warning("Trace %d does not exist, skipping.", trace_id)
        return

    if trace.status != Trace.STATUS_NOT_ANALYZED:
        logger.info("Trace %d already past extraction (status=%s), skipping.", trace_id, trace.status)
        return

    logger.info("Extracting surfaces for trace %d", trace_id)
    _extract_surfaces(trace)
    Trace.objects.filter(pk=trace_id).update(status=Trace.STATUS_SURFACE_EXTRACTED)
    logger.info("Trace %d surfaces extracted.", trace_id)


@app.task(queue="badges")
def award_trace_badges(trace_id: int):
    """Award badges for a trace and mark it as analyzed."""
    try:
        trace = Trace.objects.select_related("uploaded_by").get(pk=trace_id)
    except Trace.DoesNotExist:
        logger.warning("Trace %d does not exist, skipping.", trace_id)
        return

    if trace.status == Trace.STATUS_ANALYZED:
        logger.info("Trace %d already analyzed, skipping.", trace_id)
        return

    if trace.status != Trace.STATUS_SURFACE_EXTRACTED:
        logger.info(
            "Trace %d not ready for badges (status=%s), rescheduling.",
            trace_id, trace.status,
        )
        try:
            award_trace_badges.configure(
                queueing_lock=f"award_badges_{trace_id}",
                schedule_in={"seconds": 5},
            ).defer(trace_id=trace_id)
        except AlreadyEnqueued:
            pass
        return

    if trace.uploaded_by is None:
        logger.warning("Trace %d has no owner, skipping badges.", trace_id)
        Trace.objects.filter(pk=trace_id).update(status=Trace.STATUS_ANALYZED)
        return

    logger.info("Awarding badges for trace %d (user %s)", trace_id, trace.uploaded_by.username)
    award_badges(trace.uploaded_by, trace)
    Trace.objects.filter(pk=trace_id).update(status=Trace.STATUS_ANALYZED)

    # from notifs.helpers import notify
    # from notifs.models import Notification

    # notify(
    #     trace.uploaded_by,
    #     Notification.TRACE_ANALYZED,
    #     "Your trace has been analyzed",
    #     f"/traces/{trace.uuid}/",
    # )
    logger.info("Trace %d analyzed.", trace_id)

    try:
        score_dataset_challenges_task.configure(
            queueing_lock=f"score_dataset_{trace_id}",
        ).defer(trace_id=trace_id)
    except AlreadyEnqueued:
        pass

    try:
        recompute_leaderboard.defer()
    except AlreadyEnqueued:
        pass


@app.task(queue="challenges")
def score_dataset_challenges_task(trace_id: int):
    """Score dataset_points challenges after trace analysis."""
    try:
        trace = Trace.objects.select_related("uploaded_by").get(pk=trace_id)
    except Trace.DoesNotExist:
        logger.warning("Trace %d does not exist, skipping dataset scoring.", trace_id)
        return

    if trace.status != Trace.STATUS_ANALYZED:
        logger.info(
            "Trace %d not yet analyzed (status=%s), rescheduling dataset scoring.",
            trace_id, trace.status,
        )
        try:
            score_dataset_challenges_task.configure(
                queueing_lock=f"score_dataset_{trace_id}",
                schedule_in={"seconds": 5},
            ).defer(trace_id=trace_id)
        except AlreadyEnqueued:
            pass
        return

    if trace.uploaded_by is None:
        logger.warning("Trace %d has no owner, skipping dataset scoring.", trace_id)
        return

    from challenges.scoring import score_dataset_challenges
    score_dataset_challenges(trace, trace.uploaded_by)


@app.task(queue="tiles", queueing_lock="recompute_leaderboard")
def recompute_leaderboard():
    """Recompute the leaderboard after trace analysis."""
    from django.core.management import call_command
    call_command("compute_leaderboard")

    try:
        recompute_zone_leaderboard.defer()
    except AlreadyEnqueued:
        pass

    from challenges.tasks import compute_challenge_leaderboards
    try:
        compute_challenge_leaderboards.defer()
    except AlreadyEnqueued:
        pass


@app.task(queue="tiles", queueing_lock="recompute_zone_leaderboard")
def recompute_zone_leaderboard():
    """Recompute per-zone leaderboards."""
    from django.core.management import call_command
    call_command("compute_zone_leaderboard")


@app.task(queue="tiles")
def generate_tiles(trace_id: int, zoom: int):
    """Generate hexagon tiles for a trace's bounding box at a given zoom level."""
    try:
        trace = Trace.objects.get(pk=trace_id)
    except Trace.DoesNotExist:
        logger.warning("Trace %d does not exist, skipping tile generation.", trace_id)
        return

    if trace.status == Trace.STATUS_NOT_ANALYZED:
        logger.info(
            "Trace %d not ready for tiles (status=%s), rescheduling.",
            trace_id, trace.status,
        )
        try:
            generate_tiles.configure(
                queueing_lock=f"generate_tiles_{trace_id}_{zoom}",
                schedule_in={"seconds": 5},
            ).defer(trace_id=trace_id, zoom=zoom)
        except AlreadyEnqueued:
            pass
        return

    if not trace.bbox:
        logger.warning("Trace %d has no bbox, skipping tile generation.", trace_id)
        return

    west, south, east, north = trace.bbox.extent
    count = generate_tiles_for_bbox(zoom, west, south, east, north)
    logger.info("Trace %d zoom %d: %d tiles generated.", trace_id, zoom, count)


@app.task(queue="tiles")
def generate_score_tiles(trace_id: int, zoom: int):
    """Generate score label tiles for a trace's bounding box at a given zoom level."""
    try:
        trace = Trace.objects.get(pk=trace_id)
    except Trace.DoesNotExist:
        logger.warning("Trace %d does not exist, skipping score tile generation.", trace_id)
        return

    if trace.status == Trace.STATUS_NOT_ANALYZED:
        logger.info(
            "Trace %d not ready for score tiles (status=%s), rescheduling.",
            trace_id, trace.status,
        )
        try:
            generate_score_tiles.configure(
                queueing_lock=f"generate_score_tiles_{trace_id}_{zoom}",
                schedule_in={"seconds": 5},
            ).defer(trace_id=trace_id, zoom=zoom)
        except AlreadyEnqueued:
            pass
        return

    if not trace.bbox:
        logger.warning("Trace %d has no bbox, skipping score tile generation.", trace_id)
        return

    west, south, east, north = trace.bbox.extent
    count = generate_score_tiles_for_bbox(zoom, west, south, east, north)
    logger.info("Trace %d zoom %d: %d score tiles generated.", trace_id, zoom, count)


@app.task(queue="tiles")
def generate_user_tiles(trace_id: int, user_id: int, zoom: int):
    """Generate per-user hexagon tiles for a trace's bounding box at a given zoom level."""
    try:
        trace = Trace.objects.get(pk=trace_id)
    except Trace.DoesNotExist:
        logger.warning("Trace %d does not exist, skipping user tile generation.", trace_id)
        return

    if trace.status == Trace.STATUS_NOT_ANALYZED:
        logger.info(
            "Trace %d not ready for user tiles (status=%s), rescheduling.",
            trace_id, trace.status,
        )
        try:
            generate_user_tiles.configure(
                queueing_lock=f"generate_user_tiles_{user_id}_{trace_id}_{zoom}",
                schedule_in={"seconds": 5},
            ).defer(trace_id=trace_id, user_id=user_id, zoom=zoom)
        except AlreadyEnqueued:
            pass
        return

    if not trace.bbox:
        logger.warning("Trace %d has no bbox, skipping user tile generation.", trace_id)
        return

    from traces.models import UserProfile
    try:
        hexagram = UserProfile.objects.values_list("hexagram", flat=True).get(user_id=user_id)
    except UserProfile.DoesNotExist:
        logger.warning("User %d has no profile, skipping user tile generation.", user_id)
        return

    west, south, east, north = trace.bbox.extent
    count = generate_user_tiles_for_bbox(user_id, hexagram, zoom, west, south, east, north)
    logger.info("Trace %d user %d zoom %d: %d user tiles generated.", trace_id, user_id, zoom, count)


@app.task(queue="tiles")
def regenerate_tiles_for_bbox(west: float, south: float, east: float, north: float, zoom: int):
    """Regenerate hexagon tiles for a bounding box (used after trace deletion)."""
    count = generate_tiles_for_bbox(zoom, west, south, east, north)
    logger.info("Regenerated %d tiles at zoom %d for bbox.", count, zoom)


@app.task(queue="tiles")
def regenerate_score_tiles_for_bbox(west: float, south: float, east: float, north: float, zoom: int):
    """Regenerate score tiles for a bounding box (used after trace deletion)."""
    count = generate_score_tiles_for_bbox(zoom, west, south, east, north)
    logger.info("Regenerated %d score tiles at zoom %d for bbox.", count, zoom)


@app.task(queue="tiles")
def regenerate_user_tiles_for_bbox(user_id: int, west: float, south: float, east: float, north: float, zoom: int):
    """Regenerate per-user tiles for a bounding box (used after trace deletion)."""
    from traces.models import UserProfile
    try:
        hexagram = UserProfile.objects.values_list("hexagram", flat=True).get(user_id=user_id)
    except UserProfile.DoesNotExist:
        logger.warning("User %d has no profile, skipping user tile regeneration.", user_id)
        return

    count = generate_user_tiles_for_bbox(user_id, hexagram, zoom, west, south, east, north)
    logger.info("Regenerated %d user tiles at zoom %d for user %d.", count, zoom, user_id)
