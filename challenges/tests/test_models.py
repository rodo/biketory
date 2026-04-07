from datetime import timedelta

from django.contrib.auth import get_user_model
from django.db import IntegrityError
from django.test import TestCase
from django.utils import timezone

from challenges.models import (
    Challenge,
    ChallengeLeaderboardEntry,
    ChallengeParticipant,
    ChallengeReward,
    ChallengeSponsor,
)

user_model = get_user_model()


class ChallengeModelTest(TestCase):
    def setUp(self):
        self.admin = user_model.objects.create_user(
            username="admin", password="test1234", email="admin@test.com"
        )
        self.now = timezone.now()
        self.challenge = Challenge.objects.create(
            title="Test Challenge",
            challenge_type=Challenge.TYPE_CAPTURE_HEXAGON,
            capture_mode=Challenge.CAPTURE_ANY,
            start_date=self.now,
            end_date=self.now + timedelta(days=7),
            created_by=self.admin,
        )

    def test_str(self):
        assert str(self.challenge) == "Test Challenge"

    def test_challenge_types(self):
        assert self.challenge.challenge_type == "capture_hexagon"
        self.challenge.challenge_type = Challenge.TYPE_MAX_POINTS
        self.challenge.save()
        self.challenge.refresh_from_db()
        assert self.challenge.challenge_type == "max_points"


class ChallengeParticipantTest(TestCase):
    def setUp(self):
        self.admin = user_model.objects.create_user(
            username="admin", password="test1234", email="admin@test.com"
        )
        self.player = user_model.objects.create_user(
            username="player", password="test1234", email="player@test.com"
        )
        self.now = timezone.now()
        self.challenge = Challenge.objects.create(
            title="Test Challenge",
            challenge_type=Challenge.TYPE_CAPTURE_HEXAGON,
            start_date=self.now,
            end_date=self.now + timedelta(days=7),
            created_by=self.admin,
        )

    def test_join(self):
        cp = ChallengeParticipant.objects.create(
            challenge=self.challenge, user=self.player
        )
        assert cp.joined_at is not None
        assert str(cp) == f"Challenge #{self.challenge.pk} — User #{self.player.pk}"

    def test_unique_constraint(self):
        ChallengeParticipant.objects.create(
            challenge=self.challenge, user=self.player
        )
        with self.assertRaises(IntegrityError):
            ChallengeParticipant.objects.create(
                challenge=self.challenge, user=self.player
            )


class ChallengeLeaderboardEntryTest(TestCase):
    def setUp(self):
        self.admin = user_model.objects.create_user(
            username="admin", password="test1234", email="admin@test.com"
        )
        self.now = timezone.now()
        self.challenge = Challenge.objects.create(
            title="Test Challenge",
            challenge_type=Challenge.TYPE_CAPTURE_HEXAGON,
            start_date=self.now,
            end_date=self.now + timedelta(days=7),
            created_by=self.admin,
        )

    def test_create_entry(self):
        entry = ChallengeLeaderboardEntry.objects.create(
            challenge=self.challenge,
            user_id=self.admin.pk,
            username="admin",
            is_premium=False,
            score=42,
            rank=1,
            computed_at=self.now,
        )
        assert str(entry) == f"Challenge #{self.challenge.pk} — #1 admin"

    def test_unique_constraint(self):
        ChallengeLeaderboardEntry.objects.create(
            challenge=self.challenge,
            user_id=self.admin.pk,
            username="admin",
            score=10,
            rank=1,
            computed_at=self.now,
        )
        with self.assertRaises(IntegrityError):
            ChallengeLeaderboardEntry.objects.create(
                challenge=self.challenge,
                user_id=self.admin.pk,
                username="admin",
                score=20,
                rank=1,
                computed_at=self.now,
            )


class ChallengeRewardTest(TestCase):
    def setUp(self):
        self.admin = user_model.objects.create_user(
            username="admin", password="test1234", email="admin@test.com"
        )
        self.now = timezone.now()
        self.challenge = Challenge.objects.create(
            title="Test Challenge",
            challenge_type=Challenge.TYPE_CAPTURE_HEXAGON,
            start_date=self.now,
            end_date=self.now + timedelta(days=7),
            created_by=self.admin,
        )

    def test_create_reward(self):
        reward = ChallengeReward.objects.create(
            challenge=self.challenge,
            rank_threshold=1,
            reward_type=ChallengeReward.REWARD_BADGE,
            badge_id="test_badge",
        )
        assert "rank≤1" in str(reward)

    def test_unique_constraint(self):
        ChallengeReward.objects.create(
            challenge=self.challenge,
            rank_threshold=1,
            reward_type=ChallengeReward.REWARD_BADGE,
        )
        with self.assertRaises(IntegrityError):
            ChallengeReward.objects.create(
                challenge=self.challenge,
                rank_threshold=1,
                reward_type=ChallengeReward.REWARD_BADGE,
            )


class ChallengeSponsorTest(TestCase):
    def setUp(self):
        self.admin = user_model.objects.create_user(
            username="admin", password="test1234", email="admin@test.com"
        )
        self.now = timezone.now()
        self.challenge = Challenge.objects.create(
            title="Test Challenge",
            challenge_type=Challenge.TYPE_CAPTURE_HEXAGON,
            start_date=self.now,
            end_date=self.now + timedelta(days=7),
            created_by=self.admin,
        )

    def test_create_sponsor(self):
        sponsor = ChallengeSponsor.objects.create(
            challenge=self.challenge,
            name="ACME Corp",
            url="https://acme.example.com",
        )
        assert "ACME Corp" in str(sponsor)
