from datetime import timedelta

from django.contrib.gis.geos import Point
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from challenges.models import (
    Challenge,
    ChallengeDatasetScore,
    ChallengeParticipant,
    Dataset,
    DatasetFeature,
)
from traces.models import Trace

from ._helpers import make_user, small_route


class DeleteTraceTest(TestCase):

    def setUp(self):
        self.user = make_user()
        self.client.force_login(self.user)
        self.trace = Trace.objects.create(route=small_route(), uploaded_by=self.user)

    def test_get_redirects_to_trace_list(self):
        resp = self.client.get(reverse("delete_trace", args=[self.trace.pk]))
        self.assertRedirects(resp, reverse("trace_list"), fetch_redirect_response=False)

    def test_get_does_not_delete_trace(self):
        self.client.get(reverse("delete_trace", args=[self.trace.pk]))
        self.assertEqual(Trace.objects.count(), 1)

    def test_post_deletes_trace(self):
        self.client.post(reverse("delete_trace", args=[self.trace.pk]))
        self.assertEqual(Trace.objects.count(), 0)

    def test_post_redirects_to_trace_list(self):
        resp = self.client.post(reverse("delete_trace", args=[self.trace.pk]))
        self.assertRedirects(resp, reverse("trace_list"), fetch_redirect_response=False)

    def test_delete_unknown_returns_404(self):
        resp = self.client.post(reverse("delete_trace", args=[99999]))
        self.assertEqual(resp.status_code, 404)


class DeleteTraceRevokesDatasetScoresTest(TestCase):
    """Deleting a trace must decrement ChallengeParticipant.score
    and cascade-delete the related ChallengeDatasetScore rows."""

    def setUp(self):
        self.user = make_user()
        self.admin = make_user(username="admin")
        self.client.force_login(self.user)

        # Create two traces for the same user
        self.trace_a = Trace.objects.create(route=small_route(), uploaded_by=self.user)
        self.trace_b = Trace.objects.create(route=small_route(), uploaded_by=self.user)

        # Create a dataset_points challenge
        now = timezone.now()
        dataset = Dataset.objects.create(
            name="Test dataset", source_file="test.geojson", md5_hash="a" * 32,
        )
        self.challenge = Challenge.objects.create(
            title="Dataset challenge",
            challenge_type=Challenge.TYPE_DATASET_POINTS,
            dataset=dataset,
            start_date=now - timedelta(days=1),
            end_date=now + timedelta(days=6),
            created_by=self.admin,
        )

        # The user participates — score starts at 0 and will be
        # auto-incremented by the SQL trigger on each ChallengeDatasetScore INSERT.
        self.participant = ChallengeParticipant.objects.create(
            challenge=self.challenge, user=self.user,
        )

        # Create dataset features and link scores to traces
        feature_1 = DatasetFeature.objects.create(
            dataset=dataset, geom=Point(2.35, 48.85, srid=4326),
        )
        feature_2 = DatasetFeature.objects.create(
            dataset=dataset, geom=Point(2.36, 48.86, srid=4326),
        )
        feature_3 = DatasetFeature.objects.create(
            dataset=dataset, geom=Point(2.37, 48.87, srid=4326),
        )

        # 2 scores linked to trace_a, 1 score linked to trace_b
        ChallengeDatasetScore.objects.create(
            challenge=self.challenge, user=self.user,
            dataset_feature=feature_1, trace=self.trace_a,
        )
        ChallengeDatasetScore.objects.create(
            challenge=self.challenge, user=self.user,
            dataset_feature=feature_2, trace=self.trace_a,
        )
        ChallengeDatasetScore.objects.create(
            challenge=self.challenge, user=self.user,
            dataset_feature=feature_3, trace=self.trace_b,
        )

    def test_delete_trace_decrements_participant_score(self):
        # Participant starts with score=3. Deleting trace_a (which has 2
        # linked ChallengeDatasetScore rows) should decrement score to 1.
        self.client.post(reverse("delete_trace", args=[self.trace_a.pk]))

        self.participant.refresh_from_db()
        self.assertEqual(self.participant.score, 1)

    def test_delete_trace_removes_dataset_scores(self):
        # trace_a has 2 ChallengeDatasetScore rows; after deletion only
        # the 1 row linked to trace_b should remain.
        self.client.post(reverse("delete_trace", args=[self.trace_a.pk]))

        self.assertEqual(ChallengeDatasetScore.objects.count(), 1)
        # The remaining score must belong to trace_b
        remaining = ChallengeDatasetScore.objects.first()
        self.assertEqual(remaining.trace_id, self.trace_b.pk)

    def test_delete_all_traces_zeroes_score(self):
        # Deleting both traces should bring the participant score to 0
        # and leave no ChallengeDatasetScore rows.
        self.client.post(reverse("delete_trace", args=[self.trace_a.pk]))
        self.client.post(reverse("delete_trace", args=[self.trace_b.pk]))

        self.participant.refresh_from_db()
        self.assertEqual(self.participant.score, 0)
        self.assertEqual(ChallengeDatasetScore.objects.count(), 0)

    def test_delete_trace_without_scores_does_not_affect_participant(self):
        # A trace with no linked ChallengeDatasetScore should not change
        # the participant score at all.
        orphan_trace = Trace.objects.create(route=small_route(), uploaded_by=self.user)

        self.client.post(reverse("delete_trace", args=[orphan_trace.pk]))

        self.participant.refresh_from_db()
        self.assertEqual(self.participant.score, 3)
