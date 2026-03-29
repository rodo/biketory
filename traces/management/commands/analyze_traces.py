import logging

from django.core.management.base import BaseCommand

from traces.models import Trace
from traces.tasks import award_trace_badges, extract_surfaces

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Defer analysis jobs for traces that are not fully analyzed."

    def handle(self, *args, **options):
        not_analyzed = Trace.objects.filter(
            status=Trace.STATUS_NOT_ANALYZED,
        ).order_by("uploaded_at")

        count_extract = 0
        for trace in not_analyzed.iterator():
            extract_surfaces.defer(trace_id=trace.pk)
            award_trace_badges.defer(trace_id=trace.pk)
            count_extract += 1

        surface_extracted = Trace.objects.filter(
            status=Trace.STATUS_SURFACE_EXTRACTED,
        ).order_by("uploaded_at")

        count_badges = 0
        for trace in surface_extracted.iterator():
            award_trace_badges.defer(trace_id=trace.pk)
            count_badges += 1

        total = count_extract + count_badges
        logger.info(
            "Deferred %d job(s): %d extraction+badges, %d badges only.",
            total, count_extract, count_badges,
        )
        self.stdout.write(
            f"Deferred {total} job(s): {count_extract} extraction+badges, "
            f"{count_badges} badges only."
        )
