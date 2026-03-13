from django.core.management.base import BaseCommand

from traces.models import ClosedSurface, Trace, UserSurfaceStats


class Command(BaseCommand):
    help = "Delete all traces, closed surfaces, and user surface stats"

    def add_arguments(self, parser):
        parser.add_argument(
            "--yes", action="store_true", help="Skip confirmation prompt"
        )

    def handle(self, *args, **options):
        traces_count = Trace.objects.count()
        surfaces_count = ClosedSurface.objects.count()
        stats_count = UserSurfaceStats.objects.count()

        if not options["yes"]:
            self.stdout.write(
                self.style.WARNING(
                    f"This will permanently delete:\n"
                    f"  - {traces_count} trace(s)\n"
                    f"  - {surfaces_count} closed surface(s)\n"
                    f"  - {stats_count} user stat(s)"
                )
            )
            confirm = input("Proceed? [y/N] ").strip().lower()
            if confirm != "y":
                self.stdout.write("Aborted.")
                return

        # Surfaces and stats are deleted by cascade from Trace,
        # but we delete them explicitly for a clear count report.
        ClosedSurface.objects.all().delete()
        UserSurfaceStats.objects.all().delete()
        Trace.objects.all().delete()

        self.stdout.write(self.style.SUCCESS(
            f"Purged {traces_count} trace(s), "
            f"{surfaces_count} surface(s), "
            f"{stats_count} user stat(s)."
        ))
