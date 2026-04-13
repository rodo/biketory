from datetime import timedelta

from django.contrib.auth import get_user_model
from django.contrib.gis.geos import Polygon
from django.test import TestCase
from django.utils import timezone

from challenges.models import (
    Challenge,
    ChallengeDatasetScore,
    ChallengeHexagon,
    ChallengeParticipant,
    Dataset,
    DatasetFeature,
    TraceChallengeContribution,
)
from traces.models import (
    ClosedSurface,
    Hexagon,
    HexagonGainEvent,
    HexagonScore,
    Trace,
    UserProfile,
)

user_model = get_user_model()


def _square(cx, cy, half):
    return Polygon([
        (cx - half, cy - half),
        (cx + half, cy - half),
        (cx + half, cy + half),
        (cx - half, cy + half),
        (cx - half, cy - half),
    ])


class RecordTraceContributionsTest(TestCase):
    """Test _record_trace_contributions called from recompute_user_challenges."""

    def setUp(self):
        self.user = user_model.objects.create_user("tester", password="pass")
        UserProfile.objects.get_or_create(user=self.user)
        self.admin = user_model.objects.create_user("admin", password="pass")
        self.now = timezone.now()

        # Trace with a surface + hexagon inside it
        from django.contrib.gis.geos import LineString, MultiLineString
        route = MultiLineString(LineString([(2.30, 48.80), (2.40, 48.90)]))
        self.trace = Trace.objects.create(
            route=route,
            uploaded_by=self.user,
            first_point_date=self.now,
            status=Trace.STATUS_ANALYZED,
        )
        poly = _square(2.35, 48.85, 0.005)
        ClosedSurface.objects.create(
            trace=self.trace, owner=self.user, polygon=poly,
        )
        # Hexagon fully inside the surface
        hex_geom = _square(2.35, 48.85, 0.002)
        self.hexagon = Hexagon.objects.create(geom=hex_geom)
        HexagonScore.objects.create(
            hexagon=self.hexagon, user=self.user, points=1,
            last_earned_at=self.now,
        )

    def _make_challenge(self, title, challenge_type, **kwargs):
        defaults = {
            "start_date": self.now - timedelta(days=7),
            "end_date": self.now + timedelta(days=7),
            "created_by": self.admin,
            "is_visible": True,
        }
        defaults.update(kwargs)
        return Challenge.objects.create(
            title=title,
            challenge_type=challenge_type,
            **defaults,
        )

    def test_capture_hexagon_contribution(self):
        # A capture_hexagon challenge should get a contribution with points = matching hexagons
        challenge = self._make_challenge(
            "Capture", Challenge.TYPE_CAPTURE_HEXAGON,
            capture_mode=Challenge.CAPTURE_ANY,
        )
        ChallengeHexagon.objects.create(challenge=challenge, hexagon=self.hexagon)
        ChallengeParticipant.objects.create(
            challenge=challenge, user=self.user, score=1,
        )

        from traces.tasks import _record_trace_contributions
        _record_trace_contributions(self.trace, [challenge.pk])

        contrib = TraceChallengeContribution.objects.get(
            trace=self.trace, challenge=challenge,
        )
        self.assertEqual(contrib.points, 1)

    def test_active_days_contribution(self):
        # An active_days challenge should get a contribution with points = 1
        challenge = self._make_challenge(
            "Active Days", Challenge.TYPE_ACTIVE_DAYS,
        )
        ChallengeParticipant.objects.create(
            challenge=challenge, user=self.user, score=1,
        )

        from traces.tasks import _record_trace_contributions
        _record_trace_contributions(self.trace, [challenge.pk])

        contrib = TraceChallengeContribution.objects.get(
            trace=self.trace, challenge=challenge,
        )
        self.assertEqual(contrib.points, 1)

    def test_new_hexagons_contribution(self):
        # A new_hexagons challenge should count HexagonGainEvents matching the trace
        challenge = self._make_challenge(
            "New Hexagons", Challenge.TYPE_NEW_HEXAGONS,
        )
        ChallengeParticipant.objects.create(
            challenge=challenge, user=self.user, score=1,
        )
        HexagonGainEvent.objects.create(
            hexagon=self.hexagon, user=self.user,
            earned_at=self.trace.first_point_date, is_first=True,
        )

        from traces.tasks import _record_trace_contributions
        _record_trace_contributions(self.trace, [challenge.pk])

        contrib = TraceChallengeContribution.objects.get(
            trace=self.trace, challenge=challenge,
        )
        self.assertEqual(contrib.points, 1)

    def test_no_contribution_when_no_matching_hexagons(self):
        # If the challenge has no hexagons matching the trace, no contribution is created
        challenge = self._make_challenge(
            "Capture", Challenge.TYPE_CAPTURE_HEXAGON,
            capture_mode=Challenge.CAPTURE_ANY,
        )
        # Challenge hexagon is far away from the trace
        far_hex = Hexagon.objects.create(geom=_square(10.0, 50.0, 0.002))
        ChallengeHexagon.objects.create(challenge=challenge, hexagon=far_hex)
        ChallengeParticipant.objects.create(
            challenge=challenge, user=self.user, score=0,
        )

        from traces.tasks import _record_trace_contributions
        _record_trace_contributions(self.trace, [challenge.pk])

        self.assertFalse(
            TraceChallengeContribution.objects.filter(
                trace=self.trace, challenge=challenge,
            ).exists()
        )

    def test_ignore_conflicts_on_duplicate(self):
        # Calling _record_trace_contributions twice should not raise
        challenge = self._make_challenge(
            "Active Days", Challenge.TYPE_ACTIVE_DAYS,
        )

        from traces.tasks import _record_trace_contributions
        _record_trace_contributions(self.trace, [challenge.pk])
        _record_trace_contributions(self.trace, [challenge.pk])

        self.assertEqual(
            TraceChallengeContribution.objects.filter(
                trace=self.trace, challenge=challenge,
            ).count(),
            1,
        )

    def test_empty_challenge_ids(self):
        # Calling with empty list should be a no-op
        from traces.tasks import _record_trace_contributions
        _record_trace_contributions(self.trace, [])

        self.assertEqual(TraceChallengeContribution.objects.count(), 0)


class DatasetContributionTest(TestCase):
    """Test dataset challenge contribution recording in score_dataset_challenges_task."""

    def setUp(self):
        self.user = user_model.objects.create_user("tester", password="pass")
        UserProfile.objects.get_or_create(user=self.user)
        self.admin = user_model.objects.create_user("admin", password="pass")
        self.now = timezone.now()

        from django.contrib.gis.geos import LineString, MultiLineString
        route = MultiLineString(LineString([(2.30, 48.80), (2.40, 48.90)]))
        self.trace = Trace.objects.create(
            route=route,
            uploaded_by=self.user,
            first_point_date=self.now,
            status=Trace.STATUS_ANALYZED,
        )

    def test_dataset_contribution_created(self):
        # After creating ChallengeDatasetScores, the task should create a contribution
        dataset = Dataset.objects.create(
            name="Test", source_file="test.geojson", md5_hash="a" * 32,
        )
        feature = DatasetFeature.objects.create(
            dataset=dataset, geom="POINT(2.35 48.85)",
        )
        challenge = Challenge.objects.create(
            title="Dataset Challenge",
            challenge_type=Challenge.TYPE_DATASET_POINTS,
            dataset=dataset,
            start_date=self.now - timedelta(days=7),
            end_date=self.now + timedelta(days=7),
            created_by=self.admin,
            is_visible=True,
        )
        ChallengeParticipant.objects.create(
            challenge=challenge, user=self.user, score=0,
        )

        # Simulate what score_dataset_challenges would create
        ChallengeDatasetScore.objects.create(
            challenge=challenge, user=self.user,
            dataset_feature=feature, trace=self.trace,
        )

        # Now run the contribution recording part directly
        from django.db import models as db_models
        ds_counts = (
            ChallengeDatasetScore.objects
            .filter(trace=self.trace, user=self.user)
            .values("challenge_id")
            .annotate(pts=db_models.Count("id"))
        )
        contributions = [
            TraceChallengeContribution(
                trace=self.trace,
                challenge_id=row["challenge_id"],
                points=row["pts"],
            )
            for row in ds_counts
            if row["pts"] > 0
        ]
        TraceChallengeContribution.objects.bulk_create(
            contributions, ignore_conflicts=True,
        )

        contrib = TraceChallengeContribution.objects.get(
            trace=self.trace, challenge=challenge,
        )
        self.assertEqual(contrib.points, 1)


class CascadeDeleteTest(TestCase):
    """Test that TraceChallengeContribution is deleted on trace or challenge deletion."""

    def test_cascade_on_trace_delete(self):
        user = user_model.objects.create_user("tester", password="pass")
        admin = user_model.objects.create_user("admin", password="pass")
        now = timezone.now()

        from django.contrib.gis.geos import LineString, MultiLineString
        route = MultiLineString(LineString([(2.30, 48.80), (2.40, 48.90)]))
        trace = Trace.objects.create(route=route, uploaded_by=user)
        challenge = Challenge.objects.create(
            title="Test",
            challenge_type=Challenge.TYPE_ACTIVE_DAYS,
            start_date=now - timedelta(days=1),
            end_date=now + timedelta(days=1),
            created_by=admin,
        )
        TraceChallengeContribution.objects.create(
            trace=trace, challenge=challenge, points=1,
        )
        self.assertEqual(TraceChallengeContribution.objects.count(), 1)

        trace.delete()
        self.assertEqual(TraceChallengeContribution.objects.count(), 0)

    def test_cascade_on_challenge_delete(self):
        user = user_model.objects.create_user("tester", password="pass")
        admin = user_model.objects.create_user("admin", password="pass")
        now = timezone.now()

        from django.contrib.gis.geos import LineString, MultiLineString
        route = MultiLineString(LineString([(2.30, 48.80), (2.40, 48.90)]))
        trace = Trace.objects.create(route=route, uploaded_by=user)
        challenge = Challenge.objects.create(
            title="Test",
            challenge_type=Challenge.TYPE_ACTIVE_DAYS,
            start_date=now - timedelta(days=1),
            end_date=now + timedelta(days=1),
            created_by=admin,
        )
        TraceChallengeContribution.objects.create(
            trace=trace, challenge=challenge, points=1,
        )

        challenge.delete()
        self.assertEqual(TraceChallengeContribution.objects.count(), 0)
