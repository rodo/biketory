import logging

from procrastinate.contrib.django import app

from traces.badge_award import award_badges
from traces.models import Trace

logger = logging.getLogger(__name__)


@app.task(queue="default", queueing_lock="analyze_trace")
def analyze_trace(trace_id: int):
    """Award badges for a trace and mark it as analyzed."""
    try:
        trace = Trace.objects.select_related("uploaded_by").get(pk=trace_id)
    except Trace.DoesNotExist:
        logger.warning("Trace %d does not exist, skipping.", trace_id)
        return

    if trace.status == Trace.STATUS_ANALYZED:
        logger.info("Trace %d already analyzed, skipping.", trace_id)
        return

    if trace.uploaded_by is None:
        logger.warning("Trace %d has no owner, skipping.", trace_id)
        Trace.objects.filter(pk=trace_id).update(status=Trace.STATUS_ANALYZED)
        return

    logger.info("Analyzing trace %d for user %s", trace_id, trace.uploaded_by.username)
    award_badges(trace.uploaded_by, trace)
    Trace.objects.filter(pk=trace_id).update(status=Trace.STATUS_ANALYZED)
    logger.info("Trace %d analyzed.", trace_id)
