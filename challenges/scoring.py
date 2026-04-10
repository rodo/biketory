import logging
from pathlib import Path

from django.db import connection
from django.utils import timezone

from challenges.models import Challenge, ChallengeDatasetScore

logger = logging.getLogger(__name__)

_SQL_DIR = Path(__file__).resolve().parent / "sql"
_SCORE_DATASET_ON_UPLOAD_SQL = (_SQL_DIR / "score_dataset_on_upload.sql").read_text()


def score_dataset_challenges(trace_id, user_id):
    """Score dataset_points challenges for a newly uploaded trace.

    For each active dataset_points challenge the user participates in,
    find dataset features that fall within hexagons acquired by the trace
    (i.e. hexagons contained in the trace's ClosedSurfaces), and create
    ChallengeDatasetScore rows. The SQL trigger on that table automatically
    increments ChallengeParticipant.score.
    """
    from challenges.models import ChallengeParticipant

    now = timezone.now()
    participations = (
        ChallengeParticipant.objects
        .filter(
            user_id=user_id,
            challenge__challenge_type=Challenge.TYPE_DATASET_POINTS,
            challenge__start_date__lte=now,
            challenge__end_date__gte=now,
            challenge__dataset__isnull=False,
        )
        .select_related("challenge")
    )

    for participation in participations:
        challenge = participation.challenge

        with connection.cursor() as cursor:
            cursor.execute(
                _SCORE_DATASET_ON_UPLOAD_SQL,
                [challenge.pk, trace_id, challenge.pk, user_id, trace_id],
            )
            rows = cursor.fetchall()

        if not rows:
            continue

        scores = [
            ChallengeDatasetScore(
                challenge=challenge,
                user_id=user_id,
                dataset_feature_id=row[0],
                trace_id=trace_id,
            )
            for row in rows
        ]
        created = ChallengeDatasetScore.objects.bulk_create(
            scores, ignore_conflicts=True,
        )
        logger.info(
            "Challenge %d: scored %d dataset features for user %d on trace %d",
            challenge.pk, len(created), user_id, trace_id,
        )
