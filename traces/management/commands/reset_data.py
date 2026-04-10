import logging

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from challenges.models import (
    ChallengeDatasetScore,
    ChallengeLeaderboardEntry,
    ChallengeParticipant,
)
from notifs.models import Notification
from referrals.models import Referral
from traces.models import (
    ClosedSurface,
    Hexagon,
    HexagonScore,
    Trace,
    UserBadge,
    UserSurfaceStats,
)

logger = logging.getLogger(__name__)

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
            "referrals": Referral.objects.count(),
            "notifs": Notification.objects.count(),
            "challenge_dataset_scores": ChallengeDatasetScore.objects.count(),
            "challenge_leaderboard": ChallengeLeaderboardEntry.objects.count(),
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

        self.stdout.write("Deleting challenge dataset scores...")
        ChallengeDatasetScore.objects.all().delete()

        self.stdout.write("Deleting challenge leaderboard entries...")
        ChallengeLeaderboardEntry.objects.all().delete()

        self.stdout.write("Resetting challenge participant scores...")
        ChallengeParticipant.objects.filter(score__gt=0).update(score=0)

        self.stdout.write("Deleting notifications...")
        Notification.objects.all().delete()

        self.stdout.write("Deleting referrals...")
        Referral.objects.all().delete()

        self.stdout.write("Deleting closed surfaces...")
        ClosedSurface.objects.all().delete()

        self.stdout.write("Deleting hexagon scores...")
        HexagonScore.objects.all().delete()

        self.stdout.write("Deleting badges...")
        UserBadge.objects.all().delete()

        self.stdout.write("Deleting user surface stats...")
        UserSurfaceStats.objects.all().delete()

        self.stdout.write("Deleting traces...")
        Trace.objects.all().delete()

        self.stdout.write("Deleting hexagons...")
        Hexagon.objects.all().delete()

        self.stdout.write(self.style.SUCCESS(
            "Done: " + ", ".join(f"{v} {k}" for k, v in counts.items()),
        ))
