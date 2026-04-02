import logging

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import connection

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Delete all procrastinate jobs and events. Only works with DEBUG=True."

    def add_arguments(self, parser):
        parser.add_argument(
            "--yes", action="store_true", help="Skip confirmation prompt"
        )

    def handle(self, *args, **options):
        if not settings.DEBUG:
            raise CommandError("This command is disabled when DEBUG=False.")

        with connection.cursor() as cursor:
            cursor.execute("SELECT count(*) FROM procrastinate_events")
            events_count = cursor.fetchone()[0]
            cursor.execute("SELECT count(*) FROM procrastinate_jobs")
            jobs_count = cursor.fetchone()[0]

        if not options["yes"]:
            self.stdout.write(
                self.style.WARNING(
                    f"This will permanently delete:\n"
                    f"  - {events_count} events\n"
                    f"  - {jobs_count} jobs"
                )
            )
            confirm = input("Proceed? [y/N] ").strip().lower()
            if confirm != "y":
                self.stdout.write("Aborted.")
                return

        with connection.cursor() as cursor:
            cursor.execute("DELETE FROM procrastinate_events")
            cursor.execute("DELETE FROM procrastinate_jobs")

        logger.info("Purged %d events, %d jobs.", events_count, jobs_count)
