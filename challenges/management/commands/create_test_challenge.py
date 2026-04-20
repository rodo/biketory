from datetime import timedelta

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.utils import timezone

from challenges.models import Challenge


class Command(BaseCommand):
    help = "Create a superuser and a visit_hexagons challenge for Gatling tests."

    def add_arguments(self, parser):
        parser.add_argument("--email", required=True, help="Superuser email")
        parser.add_argument("--password", required=True, help="Superuser password")

    def handle(self, *args, **options):
        user_model = get_user_model()
        email = options["email"]
        password = options["password"]

        # Create or retrieve superuser
        user, created = user_model.objects.get_or_create(
            email=email,
            defaults={"is_staff": True, "is_superuser": True},
        )
        if created:
            user.set_password(password)
            user.save()
            self.stdout.write(self.style.SUCCESS(f"Superuser created: {email}"))
        else:
            self.stdout.write(f"Superuser already exists: {email}")

        # Create or retrieve the test challenge
        now = timezone.now()
        title = "Gatling Test Challenge"

        challenge = Challenge.objects.filter(
            title=title,
            end_date__gte=now,
        ).first()

        if challenge:
            self.stdout.write(f"Reusing existing challenge pk={challenge.pk}")
        else:
            challenge = Challenge.objects.create(
                title=title,
                description="Automated challenge for Gatling performance tests.",
                challenge_type=Challenge.TYPE_VISIT_HEXAGONS,
                start_date=now - timedelta(days=1),
                end_date=now + timedelta(days=30),
                goal_threshold=5,
                is_visible=True,
                created_by=user,
            )
            self.stdout.write(
                self.style.SUCCESS(f"Challenge created pk={challenge.pk}")
            )

        self.stdout.write(f"challenge_pk={challenge.pk}")
