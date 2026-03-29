import logging

from django.core.management.base import BaseCommand

from traces.models import Trace
from traces.tasks import analyze_trace

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Defer analysis jobs for all traces with status 'not_analyzed'."

    def handle(self, *args, **options):
        traces = Trace.objects.filter(
            status=Trace.STATUS_NOT_ANALYZED,
        ).order_by("uploaded_at")

        count = 0
        for trace in traces.iterator():
            analyze_trace.defer(trace_id=trace.pk)
            count += 1

        logger.info("Deferred %d analysis job(s).", count)
        self.stdout.write(f"Deferred {count} analysis job(s).")
