from django.core.management.base import BaseCommand

from challenges.tasks import compute_challenge_leaderboards


class Command(BaseCommand):
    help = "Defer the compute_challenge_leaderboards procrastinate task."

    def handle(self, *args, **options):
        compute_challenge_leaderboards.defer()
        self.stdout.write(self.style.SUCCESS("Task deferred."))
