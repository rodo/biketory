from datetime import timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone

from challenges.models import (
    Challenge,
    ChallengeHexagon,
    ChallengeLeaderboardEntry,
    ChallengeParticipant,
)
from challenges.tasks import _build_leaderboard
from traces.models import Hexagon, HexagonScore, UserProfile

user_model = get_user_model()


class BuildLeaderboardCaptureTest(TestCase):
    """Test leaderboard computation for capture_hexagon challenges."""

    def setUp(self):
        self.admin = user_model.objects.create_user(
            username="admin", password="test1234", email="admin@test.com"
        )
        self.player1 = user_model.objects.create_user(
            username="player1", password="test1234", email="p1@test.com"
        )
        self.player2 = user_model.objects.create_user(
            username="player2", password="test1234", email="p2@test.com"
        )
        UserProfile.objects.get_or_create(user=self.player1)
        UserProfile.objects.get_or_create(user=self.player2)

        self.now = timezone.now()
        self.challenge = Challenge.objects.create(
            title="Capture Challenge",
            challenge_type=Challenge.TYPE_CAPTURE_HEXAGON,
            capture_mode=Challenge.CAPTURE_ANY,
            start_date=self.now - timedelta(days=1),
            end_date=self.now + timedelta(days=6),
            created_by=self.admin,
        )

        # Create hexagons with geom — simple squares
        from django.contrib.gis.geos import Polygon

        self.hex1 = Hexagon.objects.create(
            geom=Polygon(((0, 0), (1, 0), (1, 1), (0, 1), (0, 0))),
            owner=self.player1,
        )
        self.hex2 = Hexagon.objects.create(
            geom=Polygon(((2, 2), (3, 2), (3, 3), (2, 3), (2, 2))),
            owner=self.player2,
        )
        self.hex3 = Hexagon.objects.create(
            geom=Polygon(((4, 4), (5, 4), (5, 5), (4, 5), (4, 4))),
            owner=self.player1,
        )

        ChallengeHexagon.objects.create(challenge=self.challenge, hexagon=self.hex1)
        ChallengeHexagon.objects.create(challenge=self.challenge, hexagon=self.hex2)
        ChallengeHexagon.objects.create(challenge=self.challenge, hexagon=self.hex3)

        ChallengeParticipant.objects.create(challenge=self.challenge, user=self.player1)
        ChallengeParticipant.objects.create(challenge=self.challenge, user=self.player2)

    def test_build_leaderboard(self):
        entries = _build_leaderboard(self.challenge)
        assert len(entries) == 2

        # player1 owns hex1 and hex3 → score 2
        p1 = ChallengeLeaderboardEntry.objects.get(
            challenge=self.challenge, user_id=self.player1.pk
        )
        assert p1.score == 2
        assert p1.rank == 1

        # player2 owns hex2 → score 1
        p2 = ChallengeLeaderboardEntry.objects.get(
            challenge=self.challenge, user_id=self.player2.pk
        )
        assert p2.score == 1
        assert p2.rank == 2

    def test_leaderboard_replaces_on_recompute(self):
        _build_leaderboard(self.challenge)
        assert ChallengeLeaderboardEntry.objects.filter(challenge=self.challenge).count() == 2

        _build_leaderboard(self.challenge)
        assert ChallengeLeaderboardEntry.objects.filter(challenge=self.challenge).count() == 2


class BuildLeaderboardPointsTest(TestCase):
    """Test leaderboard computation for max_points challenges."""

    def setUp(self):
        self.admin = user_model.objects.create_user(
            username="admin", password="test1234", email="admin@test.com"
        )
        self.player1 = user_model.objects.create_user(
            username="player1", password="test1234", email="p1@test.com"
        )
        self.player2 = user_model.objects.create_user(
            username="player2", password="test1234", email="p2@test.com"
        )
        UserProfile.objects.get_or_create(user=self.player1)
        UserProfile.objects.get_or_create(user=self.player2)

        self.now = timezone.now()
        self.challenge = Challenge.objects.create(
            title="Points Challenge",
            challenge_type=Challenge.TYPE_MAX_POINTS,
            start_date=self.now - timedelta(days=1),
            end_date=self.now + timedelta(days=6),
            created_by=self.admin,
        )

        from django.contrib.gis.geos import Polygon

        self.hex1 = Hexagon.objects.create(
            geom=Polygon(((10, 10), (11, 10), (11, 11), (10, 11), (10, 10))),
        )

        ChallengeHexagon.objects.create(challenge=self.challenge, hexagon=self.hex1)

        ChallengeParticipant.objects.create(challenge=self.challenge, user=self.player1)
        ChallengeParticipant.objects.create(challenge=self.challenge, user=self.player2)

        # player1 has 5 points earned during the challenge
        HexagonScore.objects.create(
            hexagon=self.hex1,
            user=self.player1,
            points=5,
            last_earned_at=self.now,
        )
        # player2 has 3 points earned during the challenge
        HexagonScore.objects.create(
            hexagon=self.hex1,
            user=self.player2,
            points=3,
            last_earned_at=self.now,
        )

    def test_build_leaderboard(self):
        _build_leaderboard(self.challenge)

        p1 = ChallengeLeaderboardEntry.objects.get(
            challenge=self.challenge, user_id=self.player1.pk
        )
        assert p1.score == 5
        assert p1.rank == 1

        p2 = ChallengeLeaderboardEntry.objects.get(
            challenge=self.challenge, user_id=self.player2.pk
        )
        assert p2.score == 3
        assert p2.rank == 2
