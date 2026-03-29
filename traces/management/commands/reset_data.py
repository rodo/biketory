from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from traces.models import (
    ClosedSurface,
    Hexagon,
    HexagonScore,
    Trace,
    UserBadge,
    UserSurfaceStats,
)


class Command(BaseCommand):
    help = "Delete all traces, badges, hexagons, and related data. Only works with DEBUG=True."

    def add_arguments(self, parser):
        parser.add_argument(
            "--yes", action="store_true", help="Skip confirmation prompt"
        )

    def handle(self, *args, **options):
        if not settings.DEBUG:
            raise CommandError("This command is disabled when DEBUG=False.")

        counts = {
            "traces": Trace.objects.count(),
            "surfaces": ClosedSurface.objects.count(),
            "hexagon_scores": HexagonScore.objects.count(),
            "hexagons": Hexagon.objects.count(),
            "badges": UserBadge.objects.count(),
            "user_stats": UserSurfaceStats.objects.count(),
        }

        if not options["yes"]:
            self.stdout.write(
                self.style.WARNING(
                    "This will permanently delete:\n"
                    + "\n".join(f"  - {v} {k}" for k, v in counts.items())
                )
            )
            confirm = input("Proceed? [y/N] ").strip().lower()
            if confirm != "y":
                self.stdout.write("Aborted.")
                return

        ClosedSurface.objects.all().delete()
        HexagonScore.objects.all().delete()
        UserBadge.objects.all().delete()
        UserSurfaceStats.objects.all().delete()
        Trace.objects.all().delete()
        Hexagon.objects.all().delete()

        self.stdout.write(
            self.style.SUCCESS(
                "Purged: "
                + ", ".join(f"{v} {k}" for k, v in counts.items())
                + "."
            )
        )
