from datetime import timedelta

from dateutil.relativedelta import relativedelta
from django.contrib.auth import get_user_model
from django.contrib.gis.geos import Polygon
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from challenges.models import (
    Challenge,
    ChallengeHexagon,
    ChallengeReward,
    ChallengeSponsor,
)
from traces.models import Hexagon

user_model = get_user_model()


class AdminChallengeDuplicateTest(TestCase):

    def setUp(self):
        self.admin = user_model.objects.create_user(
            username="admin", password="test1234", email="admin@test.com",
            is_staff=True,
        )
        self.client.force_login(self.admin)
        now = timezone.now()
        self.challenge = Challenge.objects.create(
            title="Spring Challenge",
            description="Collect hexagons!",
            challenge_type=Challenge.TYPE_CAPTURE_HEXAGON,
            capture_mode=Challenge.CAPTURE_ANY,
            premium_only=True,
            is_visible=True,
            goal_threshold=10,
            start_date=now - timedelta(days=7),
            end_date=now - timedelta(days=1),
            created_by=self.admin,
        )

    def test_duplicate_creates_new_challenge_with_next_month_dates(self):
        # The duplicate should have start_date = 1st of next month, end_date = last day of next month
        resp = self.client.post(
            reverse("admin_challenge_duplicate", args=[self.challenge.pk]),
        )
        self.assertEqual(resp.status_code, 302)

        clone = Challenge.objects.exclude(pk=self.challenge.pk).get()

        today = timezone.now().date()
        expected_start = (today.replace(day=1) + relativedelta(months=1))
        expected_end = expected_start + relativedelta(months=1, days=-1)

        self.assertEqual(clone.start_date.date(), expected_start)
        self.assertEqual(clone.end_date.date(), expected_end)

    def test_duplicate_copies_fields(self):
        # Core fields should be copied from the source challenge
        self.client.post(
            reverse("admin_challenge_duplicate", args=[self.challenge.pk]),
        )
        clone = Challenge.objects.exclude(pk=self.challenge.pk).get()

        self.assertEqual(clone.title, "Spring Challenge")
        self.assertEqual(clone.description, "Collect hexagons!")
        self.assertEqual(clone.challenge_type, Challenge.TYPE_CAPTURE_HEXAGON)
        self.assertEqual(clone.capture_mode, Challenge.CAPTURE_ANY)
        self.assertTrue(clone.premium_only)
        self.assertEqual(clone.goal_threshold, 10)

    def test_duplicate_is_not_visible(self):
        # The clone should default to is_visible=False so admin can review before publishing
        self.client.post(
            reverse("admin_challenge_duplicate", args=[self.challenge.pk]),
        )
        clone = Challenge.objects.exclude(pk=self.challenge.pk).get()
        self.assertFalse(clone.is_visible)

    def test_duplicate_copies_rewards(self):
        # Rewards should be duplicated to the new challenge
        ChallengeReward.objects.create(
            challenge=self.challenge,
            rank_threshold=3,
            reward_type=ChallengeReward.REWARD_BADGE,
            badge_id="spring_badge",
        )
        ChallengeReward.objects.create(
            challenge=self.challenge,
            rank_threshold=1,
            reward_type=ChallengeReward.REWARD_SUB_3M,
        )

        self.client.post(
            reverse("admin_challenge_duplicate", args=[self.challenge.pk]),
        )
        clone = Challenge.objects.exclude(pk=self.challenge.pk).get()
        self.assertEqual(clone.rewards.count(), 2)

    def test_duplicate_copies_hexagons(self):
        # ChallengeHexagons should be duplicated to the new challenge
        hex_geom = Polygon([
            (2.30, 48.80), (2.31, 48.80), (2.31, 48.81),
            (2.30, 48.81), (2.30, 48.80),
        ])
        hexagon = Hexagon.objects.create(geom=hex_geom)
        ChallengeHexagon.objects.create(challenge=self.challenge, hexagon=hexagon)

        self.client.post(
            reverse("admin_challenge_duplicate", args=[self.challenge.pk]),
        )
        clone = Challenge.objects.exclude(pk=self.challenge.pk).get()
        self.assertEqual(clone.challenge_hexagons.count(), 1)

    def test_duplicate_copies_sponsors(self):
        # Sponsors should be duplicated to the new challenge
        ChallengeSponsor.objects.create(
            challenge=self.challenge,
            name="ACME Corp",
            url="https://acme.example.com",
        )

        self.client.post(
            reverse("admin_challenge_duplicate", args=[self.challenge.pk]),
        )
        clone = Challenge.objects.exclude(pk=self.challenge.pk).get()
        self.assertEqual(clone.sponsors.count(), 1)
        self.assertEqual(clone.sponsors.first().name, "ACME Corp")

    def test_duplicate_requires_staff(self):
        # Non-staff users should be redirected to login
        self.client.logout()
        regular = user_model.objects.create_user(
            username="regular", password="test1234", email="regular@test.com",
        )
        self.client.force_login(regular)

        resp = self.client.post(
            reverse("admin_challenge_duplicate", args=[self.challenge.pk]),
        )
        self.assertEqual(resp.status_code, 302)
        # No clone created
        self.assertEqual(Challenge.objects.count(), 1)

    def test_duplicate_redirects_to_clone_detail(self):
        # After duplication, the user should be redirected to the new challenge's detail page
        resp = self.client.post(
            reverse("admin_challenge_duplicate", args=[self.challenge.pk]),
        )
        clone = Challenge.objects.exclude(pk=self.challenge.pk).get()
        self.assertRedirects(
            resp,
            reverse("admin_challenge_detail", args=[clone.pk]),
            fetch_redirect_response=False,
        )
