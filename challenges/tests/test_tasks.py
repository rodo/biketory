import tempfile
from datetime import timedelta
from pathlib import Path

from django.contrib.auth import get_user_model
from django.contrib.gis.geos import MultiPolygon, Polygon
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.utils import timezone

from challenges.models import (
    Challenge,
    ChallengeHexagon,
    ChallengeLeaderboardEntry,
    ChallengeParticipant,
)
from challenges.tasks import _build_leaderboard
from geozones.models import GeoZone
from traces.models import Hexagon, HexagonScore, Trace, UserProfile
from traces.trace_processing import _create_trace_hexagons, _extract_surfaces, _parse_route

user_model = get_user_model()

_GPX_FIXTURE = (
    Path(__file__).resolve().parent.parent.parent
    / "trace_samples"
    / "closed_surface_1_hexagon_20.gpx"
)


def _upload_trace(gpx_path, user, first_point_date):
    """Parse GPX and run the full trace pipeline (hexagons + surface extraction)."""
    with gpx_path.open("rb") as f:
        route, _, length_km = _parse_route(f)
    gpx_file = SimpleUploadedFile(
        gpx_path.name,
        gpx_path.read_bytes(),
        content_type="application/gpx+xml",
    )
    trace = Trace.objects.create(
        gpx_file=gpx_file,
        route=route,
        length_km=length_km,
        first_point_date=first_point_date,
        uploaded_by=user,
    )
    _create_trace_hexagons(route)
    _extract_surfaces(trace)
    return trace


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


@override_settings(MEDIA_ROOT=tempfile.mkdtemp())
class BuildLeaderboardActiveDaysTest(TestCase):
    """Test leaderboard computation for active_days challenges.

    Player1 uploads traces on 3 distinct days, player2 on 1 day.
    Score = number of distinct upload days during the challenge period.
    """

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
            title="Active Days Challenge",
            challenge_type=Challenge.TYPE_ACTIVE_DAYS,
            start_date=self.now - timedelta(days=7),
            end_date=self.now + timedelta(days=7),
            created_by=self.admin,
        )
        ChallengeParticipant.objects.create(challenge=self.challenge, user=self.player1)
        ChallengeParticipant.objects.create(challenge=self.challenge, user=self.player2)

        # Player1: upload on 3 distinct days (full pipeline each time)
        for day_offset in range(3):
            _upload_trace(
                _GPX_FIXTURE, self.player1, self.now - timedelta(days=day_offset)
            )

        # Player2: upload on 1 day
        _upload_trace(_GPX_FIXTURE, self.player2, self.now)

    def test_build_leaderboard(self):
        entries = _build_leaderboard(self.challenge)
        assert len(entries) == 2

        p1 = ChallengeLeaderboardEntry.objects.get(
            challenge=self.challenge, user_id=self.player1.pk
        )
        assert p1.score == 3
        assert p1.rank == 1

        p2 = ChallengeLeaderboardEntry.objects.get(
            challenge=self.challenge, user_id=self.player2.pk
        )
        assert p2.score == 1
        assert p2.rank == 2


@override_settings(MEDIA_ROOT=tempfile.mkdtemp())
class BuildLeaderboardNewHexagonsTest(TestCase):
    """Test leaderboard computation for new_hexagons challenges.

    Player1 uploads a trace and acquires new hexagons.
    Player2 participates but does not upload — score stays 0.
    Score = number of hexagons acquired for the first time during the period.
    """

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
            title="New Hexagons Challenge",
            challenge_type=Challenge.TYPE_NEW_HEXAGONS,
            start_date=self.now - timedelta(days=1),
            end_date=self.now + timedelta(days=6),
            created_by=self.admin,
        )
        ChallengeParticipant.objects.create(challenge=self.challenge, user=self.player1)
        ChallengeParticipant.objects.create(challenge=self.challenge, user=self.player2)

        # Player1 uploads → acquires new hexagons via the full pipeline
        _upload_trace(_GPX_FIXTURE, self.player1, self.now)

    def test_build_leaderboard(self):
        entries = _build_leaderboard(self.challenge)
        assert len(entries) == 2

        p1 = ChallengeLeaderboardEntry.objects.get(
            challenge=self.challenge, user_id=self.player1.pk
        )
        assert p1.score == 20
        assert p1.rank == 1

        p2 = ChallengeLeaderboardEntry.objects.get(
            challenge=self.challenge, user_id=self.player2.pk
        )
        assert p2.score == 0
        assert p2.rank == 2


@override_settings(MEDIA_ROOT=tempfile.mkdtemp())
class BuildLeaderboardVisitHexagonsTest(TestCase):
    """Test leaderboard computation for visit_hexagons challenges.

    Player1 uploads the same trace twice → score = 40 (20 hex × 2 uploads).
    Player2 participates but does not upload → score = 0.
    Score = total hexagons traversed (duplicates count).
    goal_threshold = 30 → player1 meets goal, player2 does not.
    """

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
            title="Visit Hexagons Challenge",
            challenge_type=Challenge.TYPE_VISIT_HEXAGONS,
            goal_threshold=30,
            start_date=self.now - timedelta(days=1),
            end_date=self.now + timedelta(days=6),
            created_by=self.admin,
        )
        ChallengeParticipant.objects.create(challenge=self.challenge, user=self.player1)
        ChallengeParticipant.objects.create(challenge=self.challenge, user=self.player2)

        # Player1 uploads the same trace twice on different days
        _upload_trace(_GPX_FIXTURE, self.player1, self.now)
        _upload_trace(_GPX_FIXTURE, self.player1, self.now - timedelta(hours=12))

    def test_build_leaderboard(self):
        entries = _build_leaderboard(self.challenge)
        assert len(entries) == 2

        # Player1: 20 hexagons × 2 uploads = 40
        p1 = ChallengeLeaderboardEntry.objects.get(
            challenge=self.challenge, user_id=self.player1.pk
        )
        assert p1.score == 40
        assert p1.rank == 1
        # 40 >= goal_threshold 30 → goal met
        assert p1.goal_met is True

        # Player2: no uploads → score 0
        p2 = ChallengeLeaderboardEntry.objects.get(
            challenge=self.challenge, user_id=self.player2.pk
        )
        assert p2.score == 0
        assert p2.rank == 2
        # 0 < goal_threshold 30 → goal not met
        assert p2.goal_met is False


@override_settings(MEDIA_ROOT=tempfile.mkdtemp())
class BuildLeaderboardDistinctZonesTest(TestCase):
    """Test leaderboard computation for distinct_zones challenges.

    Player1 uploads a trace inside a GeoZone → acquires hexagons → score = 1 zone.
    Player2 participates but does not upload → score = 0.
    Score = number of zones where the participant acquired >= hexagons_per_zone
    new hexagons during the challenge period.
    """

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

        # GeoZone large enough to contain all hexagons from the fixture
        zone_geom = MultiPolygon(Polygon.from_bbox((-10, 40, 15, 55)))
        self.zone = GeoZone.objects.create(
            code="TEST-ZONE",
            name="Test Zone",
            admin_level=8,
            active=True,
            geom=zone_geom,
        )

        self.now = timezone.now()
        self.challenge = Challenge.objects.create(
            title="Distinct Zones Challenge",
            challenge_type=Challenge.TYPE_DISTINCT_ZONES,
            zone_admin_level=8,
            hexagons_per_zone=1,
            start_date=self.now - timedelta(days=1),
            end_date=self.now + timedelta(days=6),
            created_by=self.admin,
        )
        ChallengeParticipant.objects.create(challenge=self.challenge, user=self.player1)
        ChallengeParticipant.objects.create(challenge=self.challenge, user=self.player2)

        # Player1 uploads → acquires hexagons inside the zone
        _upload_trace(_GPX_FIXTURE, self.player1, self.now)

    def test_build_leaderboard(self):
        entries = _build_leaderboard(self.challenge)
        assert len(entries) == 2

        p1 = ChallengeLeaderboardEntry.objects.get(
            challenge=self.challenge, user_id=self.player1.pk
        )
        assert p1.score == 1
        assert p1.rank == 1

        p2 = ChallengeLeaderboardEntry.objects.get(
            challenge=self.challenge, user_id=self.player2.pk
        )
        assert p2.score == 0
        assert p2.rank == 2
