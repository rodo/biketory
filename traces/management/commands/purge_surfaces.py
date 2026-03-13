from django.core.management.base import BaseCommand

from traces.models import ClosedSurface, Trace, UserSurfaceStats


class Command(BaseCommand):
    help = "Delete all closed surfaces, reset extraction flags on traces, and clear user surface stats"

    def add_arguments(self, parser):
        parser.add_argument(
            "--yes", action="store_true", help="Skip confirmation prompt"
        )

    def handle(self, *args, **options):
        surfaces_count = ClosedSurface.objects.count()
        traces_count = Trace.objects.filter(extracted=True).count()
        stats_count = UserSurfaceStats.objects.count()

        if not options["yes"]:
            self.stdout.write(
                self.style.WARNING(
                    f"This will delete {surfaces_count} closed surface(s), "
                    f"reset {traces_count} trace(s), "
                    f"and clear {stats_count} user stat(s)."
                )
            )
            confirm = input("Proceed? [y/N] ").strip().lower()
            if confirm != "y":
                self.stdout.write("Aborted.")
                return

        ClosedSurface.objects.all().delete()
        Trace.objects.filter(extracted=True).update(extracted=False)
        UserSurfaceStats.objects.all().delete()

        self.stdout.write(self.style.SUCCESS(
            f"Purged {surfaces_count} surface(s), "
            f"reset {traces_count} trace(s), "
            f"deleted {stats_count} user stat(s)."
        ))
