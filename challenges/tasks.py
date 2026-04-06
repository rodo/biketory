import logging
from pathlib import Path

from django.db import connection, transaction
from django.utils import timezone
from procrastinate.contrib.django import app

from challenges.models import Challenge, ChallengeLeaderboardEntry

logger = logging.getLogger(__name__)

_SQL_DIR = Path(__file__).resolve().parent / "sql"
_SCORE_CAPTURE_SQL = (_SQL_DIR / "challenge_score_capture.sql").read_text()
_SCORE_POINTS_SQL = (_SQL_DIR / "challenge_score_points.sql").read_text()


def _compute_scores(challenge):
    """Return a list of (user_id, score) for the given challenge."""
    with connection.cursor() as cursor:
        if challenge.challenge_type == Challenge.TYPE_CAPTURE_HEXAGON:
            cursor.execute(_SCORE_CAPTURE_SQL, [challenge.pk])
        else:
            cursor.execute(
                _SCORE_POINTS_SQL,
                [challenge.start_date, challenge.end_date, challenge.pk],
            )
        return cursor.fetchall()


def _build_leaderboard(challenge):
    """Compute scores, rank participants, and atomically replace leaderboard entries."""
    from traces.models import UserProfile

    now = timezone.now()
    scores = _compute_scores(challenge)

    # Include participants with 0 score
    participant_ids = set(
        challenge.participants.values_list("user_id", flat=True)
    )
    scored_ids = {uid for uid, _ in scores}
    for uid in participant_ids - scored_ids:
        scores.append((uid, 0))

    # Sort by score descending for dense ranking
    scores.sort(key=lambda x: -x[1])

    # Fetch usernames and premium status
    user_ids = [uid for uid, _ in scores]
    profiles = dict(
        UserProfile.objects.filter(user_id__in=user_ids)
        .values_list("user_id", "is_premium")
    )
    from django.contrib.auth import get_user_model
    user_model = get_user_model()
    usernames = dict(
        user_model.objects.filter(pk__in=user_ids).values_list("pk", "username")
    )

    # Dense rank
    entries = []
    rank = 0
    prev_score = None
    for user_id, score in scores:
        if score != prev_score:
            rank += 1
            prev_score = score
        entries.append(
            ChallengeLeaderboardEntry(
                challenge=challenge,
                user_id=user_id,
                username=usernames.get(user_id, ""),
                is_premium=profiles.get(user_id, False),
                score=score,
                rank=rank,
                computed_at=now,
            )
        )

    with transaction.atomic():
        ChallengeLeaderboardEntry.objects.filter(challenge=challenge).delete()
        ChallengeLeaderboardEntry.objects.bulk_create(entries)

    return entries


@app.task(queue="challenges", queueing_lock="compute_challenge_leaderboards")
def compute_challenge_leaderboards():
    """Compute leaderboards for all active challenges."""
    now = timezone.now()

    active_challenges = Challenge.objects.filter(
        start_date__lte=now,
        end_date__gte=now,
    )

    for challenge in active_challenges:
        logger.info("Computing leaderboard for challenge %d: %s", challenge.pk, challenge.title)
        _build_leaderboard(challenge)

    # Check for recently ended challenges that need final scoring + rewards
    from challenges.rewards import award_challenge_rewards

    ended_challenges = Challenge.objects.filter(
        end_date__lt=now,
        end_date__gte=now - timezone.timedelta(hours=4),
    )

    for challenge in ended_challenges:
        # Only award if leaderboard exists (was computed at least once)
        if not ChallengeLeaderboardEntry.objects.filter(challenge=challenge).exists():
            logger.info("Final leaderboard for ended challenge %d: %s", challenge.pk, challenge.title)
            _build_leaderboard(challenge)

        award_challenge_rewards(challenge)

    logger.info("Challenge leaderboards computed.")
