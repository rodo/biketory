import logging
import time

from procrastinate.contrib.django import app
from procrastinate.exceptions import AlreadyEnqueued

from traces.badge_award import award_badges
from traces.models import Trace
from traces.tile_generation import (
    generate_score_tiles_for_bbox,
    generate_tiles_for_bbox,
    generate_user_tiles_for_bbox,
)
from traces.trace_processing import _extract_surfaces

logger = logging.getLogger(__name__)


@app.task(queue="analyze")
def extract_surfaces(trace_id: int):
    """Extract closed surfaces from a trace and mark it as surface_extracted."""
    t0 = time.monotonic()
    try:
        trace = Trace.objects.select_related("uploaded_by").get(pk=trace_id)
    except Trace.DoesNotExist:
        logger.warning("Trace %d does not exist, skipping.", trace_id)
        return

    if trace.status != Trace.STATUS_NOT_ANALYZED:
        logger.info("Trace %d already past extraction (status=%s), skipping.", trace_id, trace.status)
        return

    logger.info("Trace %d: Extracting surfaces", trace_id)
    _extract_surfaces(trace)
    Trace.objects.filter(pk=trace_id).update(status=Trace.STATUS_SURFACE_EXTRACTED)
    logger.info("Trace %d: surfaces extracted in %.2fs.", trace_id, time.monotonic() - t0)


@app.task(queue="badges")
def award_trace_badges(trace_id: int):
    """Award badges for a trace and mark it as analyzed."""
    t0 = time.monotonic()
    try:
        trace = Trace.objects.select_related("uploaded_by").get(pk=trace_id)
    except Trace.DoesNotExist:
        logger.warning("Trace %d does not exist, skipping.", trace_id)
        return

    if trace.status == Trace.STATUS_ANALYZED:
        logger.info("Trace %d already analyzed, skipping.", trace_id)
        return

    if trace.status != Trace.STATUS_SURFACE_EXTRACTED:
        logger.info(
            "Trace %d not ready for badges (status=%s), rescheduling.",
            trace_id, trace.status,
        )
        try:
            award_trace_badges.configure(
                queueing_lock=f"award_badges_{trace_id}",
                schedule_in={"seconds": 5},
            ).defer(trace_id=trace_id)
        except AlreadyEnqueued:
            pass
        return

    if trace.uploaded_by is None:
        logger.warning("Trace %d has no owner, skipping badges.", trace_id)
        Trace.objects.filter(pk=trace_id).update(status=Trace.STATUS_ANALYZED)
        return

    logger.info("Trace %d: Awarding badges (user %s)", trace_id, trace.uploaded_by.username)
    award_badges(trace.uploaded_by, trace)
    Trace.objects.filter(pk=trace_id).update(status=Trace.STATUS_ANALYZED)

    # from notifs.helpers import notify
    # from notifs.models import Notification

    # notify(
    #     trace.uploaded_by,
    #     Notification.TRACE_ANALYZED,
    #     "Your trace has been analyzed",
    #     f"/traces/{trace.uuid}/",
    # )
    logger.info("Trace %d: analyzed in %.2fs.", trace_id, time.monotonic() - t0)

    try:
        score_dataset_challenges_task.configure(
            queueing_lock=f"score_dataset_{trace_id}",
        ).defer(trace_id=trace_id)
    except AlreadyEnqueued:
        pass

    try:
        recompute_leaderboard.defer()
    except AlreadyEnqueued:
        pass

    try:
        recompute_user_challenges.configure(
            queueing_lock=f"recompute_user_challenges_{trace_id}",
        ).defer(trace_id=trace_id)
    except AlreadyEnqueued:
        pass


@app.task(queue="challenges")
def score_dataset_challenges_task(trace_id: int):
    """Score dataset_points challenges after trace analysis."""
    t0 = time.monotonic()
    try:
        status, user_id = Trace.objects.values_list("status", "uploaded_by").get(pk=trace_id)
    except Trace.DoesNotExist:
        logger.warning("Trace %d does not exist, skipping dataset scoring.", trace_id)
        return

    if status != Trace.STATUS_ANALYZED:
        logger.info(
            "Trace %d not yet analyzed (status=%s), rescheduling dataset scoring.",
            trace_id, status,
        )
        try:
            score_dataset_challenges_task.configure(
                queueing_lock=f"score_dataset_{trace_id}",
                schedule_in={"seconds": 5},
            ).defer(trace_id=trace_id)
        except AlreadyEnqueued:
            pass
        return

    if user_id is None:
        logger.warning("Trace %d has no owner, skipping dataset scoring.", trace_id)
        return

    from challenges.scoring import score_dataset_challenges
    score_dataset_challenges(trace_id, user_id)

    # Record dataset contributions per challenge for this trace
    from django.db import models as db_models

    from challenges.models import ChallengeDatasetScore, TraceChallengeContribution

    ds_counts = (
        ChallengeDatasetScore.objects
        .filter(trace_id=trace_id, user_id=user_id)
        .values("challenge_id")
        .annotate(pts=db_models.Count("id"))
    )
    ds_contributions = [
        TraceChallengeContribution(
            trace_id=trace_id,
            challenge_id=row["challenge_id"],
            points=row["pts"],
        )
        for row in ds_counts
        if row["pts"] > 0
    ]
    if ds_contributions:
        TraceChallengeContribution.objects.bulk_create(
            ds_contributions, ignore_conflicts=True,
        )
        logger.info(
            "Trace %d: recorded %d dataset challenge contributions.",
            trace_id, len(ds_contributions),
        )

    logger.info("Trace %d: dataset scoring done in %.2fs.", trace_id, time.monotonic() - t0)


@app.task(queue="challenges")
def recompute_user_challenges(trace_id: int):
    """Recompute leaderboards for active challenges the trace owner participates in."""
    t0 = time.monotonic()
    try:
        trace = Trace.objects.select_related("uploaded_by").get(pk=trace_id)
    except Trace.DoesNotExist:
        logger.warning("Trace %d does not exist, skipping challenge recompute.", trace_id)
        return

    if trace.status != Trace.STATUS_ANALYZED:
        logger.info(
            "Trace %d not yet analyzed (status=%s), rescheduling challenge recompute.",
            trace_id, trace.status,
        )
        try:
            recompute_user_challenges.configure(
                queueing_lock=f"recompute_user_challenges_{trace_id}",
                schedule_in={"seconds": 5},
            ).defer(trace_id=trace_id)
        except AlreadyEnqueued:
            pass
        return

    if trace.uploaded_by is None:
        logger.warning("Trace %d has no owner, skipping challenge recompute.", trace_id)
        return

    from django.utils import timezone as tz

    from challenges.models import Challenge, ChallengeParticipant
    from challenges.tasks import compute_single_challenge_leaderboard

    now = tz.now()
    challenge_ids = list(
        ChallengeParticipant.objects.filter(
            user=trace.uploaded_by,
            challenge__start_date__lte=now,
            challenge__end_date__gte=now,
        ).exclude(
            challenge__challenge_type=Challenge.TYPE_DATASET_POINTS,
        ).values_list("challenge_id", flat=True)
    )

    for pk in challenge_ids:
        try:
            compute_single_challenge_leaderboard.configure(
                queueing_lock=f"challenge_leaderboard_{pk}",
            ).defer(challenge_id=pk)
        except AlreadyEnqueued:
            pass

    _record_trace_contributions(trace, challenge_ids)

    logger.info(
        "Trace %d: dispatched leaderboard recompute for %d challenges (user %s) in %.2fs.",
        trace_id, len(challenge_ids), trace.uploaded_by.username, time.monotonic() - t0,
    )


def _record_trace_contributions(trace, challenge_ids):
    """Record how many points a trace contributed to each non-dataset challenge."""
    if not challenge_ids:
        return

    from django.contrib.gis.db.models import Union as GisUnion

    from challenges.models import (
        Challenge,
        ChallengeHexagon,
        TraceChallengeContribution,
    )
    from traces.models import ClosedSurface, Hexagon, HexagonGainEvent

    # Compute hexagons covered by this trace's surfaces
    surface_union = (
        ClosedSurface.objects.filter(trace=trace)
        .aggregate(u=GisUnion("polygon"))["u"]
    )
    trace_hexagon_ids = []
    if surface_union:
        trace_hexagon_ids = list(
            Hexagon.objects.filter(geom__within=surface_union)
            .values_list("pk", flat=True)
        )

    challenges = {
        c.pk: c
        for c in Challenge.objects.filter(pk__in=challenge_ids)
    }

    trace_date = trace.first_point_date or trace.uploaded_at
    contributions = []

    for cid, challenge in challenges.items():
        ctype = challenge.challenge_type
        points = 0

        if ctype in (Challenge.TYPE_CAPTURE_HEXAGON, Challenge.TYPE_MAX_POINTS):
            # Count trace hexagons that are in the challenge's hexagon set
            if trace_hexagon_ids:
                points = ChallengeHexagon.objects.filter(
                    challenge_id=cid,
                    hexagon_id__in=trace_hexagon_ids,
                ).count()

        elif ctype == Challenge.TYPE_ACTIVE_DAYS:
            points = 1

        elif ctype in (
            Challenge.TYPE_NEW_HEXAGONS,
            Challenge.TYPE_VISIT_HEXAGONS,
            Challenge.TYPE_DISTINCT_ZONES,
        ):
            # Count HexagonGainEvents earned on this trace date for trace hexagons
            if trace_hexagon_ids:
                points = HexagonGainEvent.objects.filter(
                    user=trace.uploaded_by,
                    hexagon_id__in=trace_hexagon_ids,
                    earned_at=trace_date,
                ).count()

        if points > 0:
            contributions.append(
                TraceChallengeContribution(
                    trace=trace,
                    challenge_id=cid,
                    points=points,
                )
            )

    if contributions:
        TraceChallengeContribution.objects.bulk_create(
            contributions, ignore_conflicts=True,
        )
        logger.info(
            "Trace %d: recorded %d challenge contributions.",
            trace.pk, len(contributions),
        )


@app.task(queue="tiles", queueing_lock="recompute_leaderboard")
def recompute_leaderboard():
    """Recompute the leaderboard after trace analysis."""
    t0 = time.monotonic()
    from django.core.management import call_command
    call_command("compute_leaderboard")

    try:
        recompute_zone_leaderboard.defer()
    except AlreadyEnqueued:
        pass

    from challenges.tasks import compute_challenge_leaderboards
    try:
        compute_challenge_leaderboards.defer()
    except AlreadyEnqueued:
        pass

    logger.info("Leaderboard recomputed in %.2fs.", time.monotonic() - t0)


@app.task(queue="tiles", queueing_lock="recompute_zone_leaderboard")
def recompute_zone_leaderboard():
    """Recompute per-zone leaderboards."""
    t0 = time.monotonic()
    from django.core.management import call_command
    call_command("compute_zone_leaderboard")
    logger.info("Zone leaderboard recomputed in %.2fs.", time.monotonic() - t0)


@app.task(queue="tiles")
def generate_tiles(trace_id: int, zoom: int):
    """Generate hexagon tiles for a trace's bounding box at a given zoom level."""
    t0 = time.monotonic()
    try:
        trace = Trace.objects.get(pk=trace_id)
    except Trace.DoesNotExist:
        logger.warning("Trace %d does not exist, skipping tile generation.", trace_id)
        return

    if trace.status == Trace.STATUS_NOT_ANALYZED:
        logger.info(
            "Trace %d not ready for tiles (status=%s), rescheduling.",
            trace_id, trace.status,
        )
        try:
            generate_tiles.configure(
                queueing_lock=f"generate_tiles_{trace_id}_{zoom}",
                schedule_in={"seconds": 5},
            ).defer(trace_id=trace_id, zoom=zoom)
        except AlreadyEnqueued:
            pass
        return

    if not trace.bbox:
        logger.warning("Trace %d has no bbox, skipping tile generation.", trace_id)
        return

    west, south, east, north = trace.bbox.extent
    count = generate_tiles_for_bbox(zoom, west, south, east, north)
    logger.info("Trace %d zoom %d: %d tiles generated in %.2fs.", trace_id, zoom, count, time.monotonic() - t0)


@app.task(queue="tiles")
def generate_score_tiles(trace_id: int, zoom: int):
    """Generate score label tiles for a trace's bounding box at a given zoom level."""
    t0 = time.monotonic()
    try:
        trace = Trace.objects.get(pk=trace_id)
    except Trace.DoesNotExist:
        logger.warning("Trace %d does not exist, skipping score tile generation.", trace_id)
        return

    if trace.status == Trace.STATUS_NOT_ANALYZED:
        logger.info(
            "Trace %d not ready for score tiles (status=%s), rescheduling.",
            trace_id, trace.status,
        )
        try:
            generate_score_tiles.configure(
                queueing_lock=f"generate_score_tiles_{trace_id}_{zoom}",
                schedule_in={"seconds": 5},
            ).defer(trace_id=trace_id, zoom=zoom)
        except AlreadyEnqueued:
            pass
        return

    if not trace.bbox:
        logger.warning("Trace %d has no bbox, skipping score tile generation.", trace_id)
        return

    west, south, east, north = trace.bbox.extent
    count = generate_score_tiles_for_bbox(zoom, west, south, east, north)
    logger.info("Trace %d zoom %d: %d score tiles generated in %.2fs.", trace_id, zoom, count, time.monotonic() - t0)


@app.task(queue="tiles")
def generate_user_tiles(trace_id: int, user_id: int, zoom: int):
    """Generate per-user hexagon tiles for a trace's bounding box at a given zoom level."""
    t0 = time.monotonic()
    try:
        trace = Trace.objects.get(pk=trace_id)
    except Trace.DoesNotExist:
        logger.warning("Trace %d does not exist, skipping user tile generation.", trace_id)
        return

    if trace.status == Trace.STATUS_NOT_ANALYZED:
        logger.info(
            "Trace %d not ready for user tiles (status=%s), rescheduling.",
            trace_id, trace.status,
        )
        try:
            generate_user_tiles.configure(
                queueing_lock=f"generate_user_tiles_{user_id}_{trace_id}_{zoom}",
                schedule_in={"seconds": 5},
            ).defer(trace_id=trace_id, user_id=user_id, zoom=zoom)
        except AlreadyEnqueued:
            pass
        return

    if not trace.bbox:
        logger.warning("Trace %d has no bbox, skipping user tile generation.", trace_id)
        return

    from traces.models import UserProfile
    try:
        hexagram = UserProfile.objects.values_list("hexagram", flat=True).get(user_id=user_id)
    except UserProfile.DoesNotExist:
        logger.warning("User %d has no profile, skipping user tile generation.", user_id)
        return

    west, south, east, north = trace.bbox.extent
    count = generate_user_tiles_for_bbox(user_id, hexagram, zoom, west, south, east, north)
    elapsed = time.monotonic() - t0
    logger.info("Trace %d user %d zoom %d: %d user tiles generated in %.2fs.", trace_id, user_id, zoom, count, elapsed)


@app.task(queue="tiles")
def regenerate_tiles_for_bbox(west: float, south: float, east: float, north: float, zoom: int):
    """Regenerate hexagon tiles for a bounding box (used after trace deletion)."""
    t0 = time.monotonic()
    count = generate_tiles_for_bbox(zoom, west, south, east, north)
    logger.info("Regenerated %d tiles at zoom %d for bbox in %.2fs.", count, zoom, time.monotonic() - t0)


@app.task(queue="tiles")
def regenerate_score_tiles_for_bbox(west: float, south: float, east: float, north: float, zoom: int):
    """Regenerate score tiles for a bounding box (used after trace deletion)."""
    t0 = time.monotonic()
    count = generate_score_tiles_for_bbox(zoom, west, south, east, north)
    logger.info("Regenerated %d score tiles at zoom %d for bbox in %.2fs.", count, zoom, time.monotonic() - t0)


@app.task(queue="tiles")
def regenerate_user_tiles_for_bbox(user_id: int, west: float, south: float, east: float, north: float, zoom: int):
    """Regenerate per-user tiles for a bounding box (used after trace deletion)."""
    from traces.models import UserProfile
    try:
        hexagram = UserProfile.objects.values_list("hexagram", flat=True).get(user_id=user_id)
    except UserProfile.DoesNotExist:
        logger.warning("User %d has no profile, skipping user tile regeneration.", user_id)
        return

    t0 = time.monotonic()
    count = generate_user_tiles_for_bbox(user_id, hexagram, zoom, west, south, east, north)
    elapsed = time.monotonic() - t0
    logger.info("Regenerated %d user tiles at zoom %d for user %d in %.2fs.", count, zoom, user_id, elapsed)


@app.periodic(cron="0 3 * * *")
@app.task(queue="analyze")
def purge_completed_jobs(timestamp: int):
    """Delete successful Procrastinate jobs older than 7 days."""
    from django.db import connection

    t0 = time.monotonic()
    with connection.cursor() as cursor:
        cursor.execute(
            "DELETE FROM procrastinate_jobs"
            " WHERE status = 'succeeded'"
            "   AND attempts >= 1"
            "   AND scheduled_at < now() - interval '7 days'"
        )
        count = cursor.rowcount
    elapsed = time.monotonic() - t0
    logger.info("Purged %d completed jobs older than 7 days in %.2fs.", count, elapsed)
