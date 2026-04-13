from datetime import timedelta

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from challenges.models import (
    Challenge,
    ChallengeLeaderboardEntry,
    ChallengeParticipant,
    TraceChallengeContribution,
)
from traces.models import ClosedSurface, Hexagon, Trace

from ._helpers import make_user, small_route, square_polygon


class TraceDetailChallengesTest(TestCase):
    """The trace detail page should show all challenges the trace contributes to."""

    def setUp(self):
        self.user = make_user()
        self.client.force_login(self.user)
        self.now = timezone.now()
        self.admin = make_user("admin")

        # Create a trace with a closed surface and a hexagon inside it
        self.trace = Trace.objects.create(
            route=small_route(),
            uploaded_by=self.user,
            first_point_date=self.now,
        )
        poly = square_polygon(2.35, 48.85, 0.005)
        self.surface = ClosedSurface.objects.create(
            trace=self.trace, owner=self.user, polygon=poly,
        )
        # Hexagon fully inside the surface
        hex_geom = square_polygon(2.35, 48.85, 0.002)
        self.hexagon = Hexagon.objects.create(geom=hex_geom)

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

    # ── capture_hexagon / max_points (via TraceChallengeContribution) ──

    def test_capture_hexagon_challenge_shown(self):
        # A capture_hexagon challenge should appear when a contribution exists
        challenge = self._make_challenge(
            "Hex Challenge", Challenge.TYPE_CAPTURE_HEXAGON,
            capture_mode=Challenge.CAPTURE_ANY,
        )
        ChallengeParticipant.objects.create(
            challenge=challenge, user=self.user, score=1,
        )
        TraceChallengeContribution.objects.create(
            trace=self.trace, challenge=challenge, points=1,
        )

        resp = self.client.get(reverse("trace_detail", args=[self.trace.uuid]))
        challenge_ids = [c.pk for c in resp.context["active_challenges"]]
        self.assertIn(challenge.pk, challenge_ids)

    def test_hexagon_challenge_trace_points(self):
        # trace_points should reflect the contribution's points value
        challenge = self._make_challenge(
            "Hex Challenge", Challenge.TYPE_CAPTURE_HEXAGON,
            capture_mode=Challenge.CAPTURE_ANY,
        )
        ChallengeParticipant.objects.create(
            challenge=challenge, user=self.user, score=1,
        )
        TraceChallengeContribution.objects.create(
            trace=self.trace, challenge=challenge, points=3,
        )

        resp = self.client.get(reverse("trace_detail", args=[self.trace.uuid]))
        c = next(c for c in resp.context["active_challenges"] if c.pk == challenge.pk)
        self.assertEqual(c.trace_points, 3)

    # ── dataset_points (via TraceChallengeContribution) ──

    def test_dataset_challenge_shown(self):
        # A dataset_points challenge should appear when a contribution exists
        challenge = self._make_challenge(
            "Dataset Challenge", Challenge.TYPE_DATASET_POINTS,
        )
        ChallengeParticipant.objects.create(
            challenge=challenge, user=self.user, score=1,
        )
        TraceChallengeContribution.objects.create(
            trace=self.trace, challenge=challenge, points=1,
        )

        resp = self.client.get(reverse("trace_detail", args=[self.trace.uuid]))
        challenge_ids = [c.pk for c in resp.context["active_challenges"]]
        self.assertIn(challenge.pk, challenge_ids)

    # ── active_days ──

    def test_active_days_challenge_shown(self):
        # An active_days challenge should appear when a contribution exists
        challenge = self._make_challenge(
            "Active Days", Challenge.TYPE_ACTIVE_DAYS,
        )
        ChallengeParticipant.objects.create(
            challenge=challenge, user=self.user, score=1,
        )
        TraceChallengeContribution.objects.create(
            trace=self.trace, challenge=challenge, points=1,
        )

        resp = self.client.get(reverse("trace_detail", args=[self.trace.uuid]))
        challenge_ids = [c.pk for c in resp.context["active_challenges"]]
        self.assertIn(challenge.pk, challenge_ids)

    def test_active_days_not_shown_when_no_contribution(self):
        # Without a contribution row, the challenge should NOT appear
        challenge = self._make_challenge(
            "Active Days", Challenge.TYPE_ACTIVE_DAYS,
        )
        ChallengeParticipant.objects.create(
            challenge=challenge, user=self.user, score=0,
        )

        resp = self.client.get(reverse("trace_detail", args=[self.trace.uuid]))
        challenge_ids = [c.pk for c in resp.context["active_challenges"]]
        self.assertNotIn(challenge.pk, challenge_ids)

    # ── new_hexagons (via TraceChallengeContribution) ──

    def test_new_hexagons_challenge_shown(self):
        # A new_hexagons challenge should appear when a contribution exists
        challenge = self._make_challenge(
            "New Hexagons", Challenge.TYPE_NEW_HEXAGONS,
        )
        ChallengeParticipant.objects.create(
            challenge=challenge, user=self.user, score=1,
        )
        TraceChallengeContribution.objects.create(
            trace=self.trace, challenge=challenge, points=1,
        )

        resp = self.client.get(reverse("trace_detail", args=[self.trace.uuid]))
        challenge_ids = [c.pk for c in resp.context["active_challenges"]]
        self.assertIn(challenge.pk, challenge_ids)

    # ── visit_hexagons (via TraceChallengeContribution) ──

    def test_visit_hexagons_challenge_shown(self):
        # A visit_hexagons challenge should appear when a contribution exists
        challenge = self._make_challenge(
            "Visit Hexagons", Challenge.TYPE_VISIT_HEXAGONS,
        )
        ChallengeParticipant.objects.create(
            challenge=challenge, user=self.user, score=1,
        )
        TraceChallengeContribution.objects.create(
            trace=self.trace, challenge=challenge, points=1,
        )

        resp = self.client.get(reverse("trace_detail", args=[self.trace.uuid]))
        challenge_ids = [c.pk for c in resp.context["active_challenges"]]
        self.assertIn(challenge.pk, challenge_ids)

    # ── Negative cases ──

    def test_challenge_not_shown_without_contribution(self):
        # If no TraceChallengeContribution exists, the challenge should not appear
        challenge = self._make_challenge(
            "Hex Challenge", Challenge.TYPE_CAPTURE_HEXAGON,
            capture_mode=Challenge.CAPTURE_ANY,
        )
        ChallengeParticipant.objects.create(
            challenge=challenge, user=self.user, score=1,
        )

        resp = self.client.get(reverse("trace_detail", args=[self.trace.uuid]))
        challenge_ids = [c.pk for c in resp.context["active_challenges"]]
        self.assertNotIn(challenge.pk, challenge_ids)

    def test_no_challenges_when_trace_has_no_surfaces(self):
        # A trace without surfaces should not show any challenges
        empty_trace = Trace.objects.create(
            route=small_route(),
            uploaded_by=self.user,
        )
        resp = self.client.get(reverse("trace_detail", args=[empty_trace.uuid]))
        self.assertEqual(resp.context["active_challenges"], [])

    def test_user_score_from_leaderboard(self):
        # user_score should come from ChallengeLeaderboardEntry, not ChallengeParticipant
        challenge = self._make_challenge(
            "Hex Challenge", Challenge.TYPE_CAPTURE_HEXAGON,
            capture_mode=Challenge.CAPTURE_ANY,
        )
        # Participant score is 0 (not updated for non-dataset types)
        ChallengeParticipant.objects.create(
            challenge=challenge, user=self.user, score=0,
        )
        # Leaderboard entry has the real score
        ChallengeLeaderboardEntry.objects.create(
            challenge=challenge, user_id=self.user.pk,
            username=self.user.username, score=42, rank=1,
            computed_at=self.now,
        )
        TraceChallengeContribution.objects.create(
            trace=self.trace, challenge=challenge, points=1,
        )

        resp = self.client.get(reverse("trace_detail", args=[self.trace.uuid]))
        c = next(c for c in resp.context["active_challenges"] if c.pk == challenge.pk)
        # Score should be 42 from leaderboard, not 0 from participant
        self.assertEqual(c.user_score, 42)

    def test_user_score_fallback_to_participant(self):
        # When no leaderboard entry exists yet, fall back to ChallengeParticipant.score
        challenge = self._make_challenge(
            "Dataset", Challenge.TYPE_DATASET_POINTS,
        )
        ChallengeParticipant.objects.create(
            challenge=challenge, user=self.user, score=5,
        )
        TraceChallengeContribution.objects.create(
            trace=self.trace, challenge=challenge, points=2,
        )

        resp = self.client.get(reverse("trace_detail", args=[self.trace.uuid]))
        c = next(c for c in resp.context["active_challenges"] if c.pk == challenge.pk)
        # No leaderboard entry → fallback to participant score
        self.assertEqual(c.user_score, 5)

    def test_contribution_cascade_on_trace_delete(self):
        # Deleting a trace should cascade-delete its contributions
        challenge = self._make_challenge(
            "Hex Challenge", Challenge.TYPE_CAPTURE_HEXAGON,
        )
        TraceChallengeContribution.objects.create(
            trace=self.trace, challenge=challenge, points=1,
        )
        self.assertEqual(TraceChallengeContribution.objects.count(), 1)

        self.trace.delete()
        self.assertEqual(TraceChallengeContribution.objects.count(), 0)
