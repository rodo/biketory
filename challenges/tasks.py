import logging
from pathlib import Path

from django.db import connection, transaction
from django.utils import timezone
from procrastinate.contrib.django import app
from procrastinate.exceptions import AlreadyEnqueued

from challenges.models import Challenge, ChallengeLeaderboardEntry

logger = logging.getLogger(__name__)

_SQL_DIR = Path(__file__).resolve().parent / "sql"
_SCORE_CAPTURE_SQL = (_SQL_DIR / "challenge_score_capture.sql").read_text()
_SCORE_POINTS_SQL = (_SQL_DIR / "challenge_score_points.sql").read_text()
_SCORE_ACTIVE_DAYS_SQL = (_SQL_DIR / "challenge_score_active_days.sql").read_text()
_SCORE_NEW_HEXAGONS_SQL = (_SQL_DIR / "challenge_score_new_hexagons.sql").read_text()
_SCORE_NEW_HEXAGONS_GEOZONE_SQL = (_SQL_DIR / "challenge_score_new_hexagons_geozone.sql").read_text()
_SCORE_DISTINCT_ZONES_SQL = (_SQL_DIR / "challenge_score_distinct_zones.sql").read_text()


def _compute_scores(challenge):
    """Return a list of (user_id, score) for the given challenge."""
    with connection.cursor() as cursor:
        if challenge.challenge_type == Challenge.TYPE_CAPTURE_HEXAGON:
            cursor.execute(_SCORE_CAPTURE_SQL, [challenge.pk])
        elif challenge.challenge_type == Challenge.TYPE_MAX_POINTS:
            cursor.execute(
                _SCORE_POINTS_SQL,
                [challenge.start_date, challenge.end_date, challenge.pk],
            )
        elif challenge.challenge_type == Challenge.TYPE_ACTIVE_DAYS:
            cursor.execute(
                _SCORE_ACTIVE_DAYS_SQL,
                [challenge.start_date, challenge.end_date, challenge.pk],
            )
        elif challenge.challenge_type == Challenge.TYPE_NEW_HEXAGONS:
            if challenge.geozone_id:
                cursor.execute(
                    _SCORE_NEW_HEXAGONS_GEOZONE_SQL,
                    [challenge.start_date, challenge.end_date, challenge.geozone_id, challenge.pk],
                )
            else:
                cursor.execute(
                    _SCORE_NEW_HEXAGONS_SQL,
                    [challenge.start_date, challenge.end_date, challenge.pk],
                )
        elif challenge.challenge_type == Challenge.TYPE_DISTINCT_ZONES:
            if challenge.zone_admin_level is None or challenge.hexagons_per_zone is None:
                logger.warning(
                    "Challenge %d: distinct_zones requires zone_admin_level and hexagons_per_zone",
                    challenge.pk,
                )
                return []
            cursor.execute(
                _SCORE_DISTINCT_ZONES_SQL,
                [
                    challenge.zone_admin_level,
                    challenge.start_date,
                    challenge.end_date,
                    challenge.hexagons_per_zone,
                    challenge.pk,
                ],
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

    threshold = challenge.goal_threshold
    for entry in entries:
        entry.goal_met = threshold is None or entry.score >= threshold

    with transaction.atomic():
        ChallengeLeaderboardEntry.objects.filter(challenge=challenge).delete()
        ChallengeLeaderboardEntry.objects.bulk_create(entries)

    return entries


@app.task(queue="challenges", queueing_lock="compute_challenge_leaderboards")
def compute_challenge_leaderboards():
    """Dispatch one task per active or recently ended challenge."""
    now = timezone.now()

    active_ids = list(
        Challenge.objects.filter(
            start_date__lte=now,
            end_date__gte=now,
        ).values_list("pk", flat=True)
    )

    ended_ids = list(
        Challenge.objects.filter(
            end_date__lt=now,
            end_date__gte=now - timezone.timedelta(hours=4),
        ).values_list("pk", flat=True)
    )

    for pk in active_ids:
        try:
            compute_single_challenge_leaderboard.configure(
                queueing_lock=f"challenge_leaderboard_{pk}",
            ).defer(challenge_id=pk, award=False)
        except AlreadyEnqueued:
            pass

    already_scored = set(
        ChallengeLeaderboardEntry.objects.filter(
            challenge_id__in=ended_ids,
        ).values_list("challenge_id", flat=True).distinct()
    )

    for pk in ended_ids:
        needs_scoring = pk not in already_scored
        try:
            compute_single_challenge_leaderboard.configure(
                queueing_lock=f"challenge_leaderboard_{pk}",
            ).defer(
                challenge_id=pk,
                compute=needs_scoring,
                award=True,
            )
        except AlreadyEnqueued:
            pass

    logger.info(
        "Dispatched %d active + %d ended challenge tasks.",
        len(active_ids), len(ended_ids),
    )


@app.task(queue="challenges")
def compute_single_challenge_leaderboard(
    challenge_id: int, compute: bool = True, award: bool = False,
):
    """Compute leaderboard for a single challenge, optionally awarding rewards."""
    try:
        challenge = Challenge.objects.get(pk=challenge_id)
    except Challenge.DoesNotExist:
        logger.warning("Challenge %d does not exist, skipping.", challenge_id)
        return

    if compute:
        logger.info("Computing leaderboard for challenge %d: %s", challenge.pk, challenge.title)
        _build_leaderboard(challenge)

    if award:
        from challenges.rewards import award_challenge_rewards
        award_challenge_rewards(challenge)

    logger.info("Challenge %d leaderboard done.", challenge.pk)
