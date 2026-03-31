import logging

from procrastinate.contrib.django import app
from procrastinate.exceptions import AlreadyEnqueued

from traces.badge_award import award_badges
from traces.models import Trace
from traces.tile_generation import generate_tiles_for_bbox
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

    from notifs.helpers import notify
    from notifs.models import Notification

    notify(
        trace.uploaded_by,
        Notification.TRACE_ANALYZED,
        "Your trace has been analyzed",
        f"/traces/{trace.uuid}/",
    )
    logger.info("Trace %d analyzed.", trace_id)


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
