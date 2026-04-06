from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from challenges.models import (
    Challenge,
    ChallengeLeaderboardEntry,
    ChallengeParticipant,
)

PAGE_SIZE = 20


@login_required
def challenge_detail(request, pk):
    challenge = get_object_or_404(Challenge, pk=pk)
    now = timezone.now()

    is_active = challenge.start_date <= now <= challenge.end_date
    is_upcoming = challenge.start_date > now
    is_ended = challenge.end_date < now

    is_participant = ChallengeParticipant.objects.filter(
        challenge=challenge, user=request.user
    ).exists()

    # Premium gate
    can_join = True
    if challenge.premium_only:
        can_join = hasattr(request.user, "profile") and request.user.profile.is_premium

    # Leaderboard
    offset = int(request.GET.get("offset", 0))
    is_ajax = request.headers.get("X-Requested-With") == "XMLHttpRequest"

    qs = ChallengeLeaderboardEntry.objects.filter(
        challenge=challenge
    ).order_by("rank")

    entries = list(qs[offset:offset + PAGE_SIZE + 1])
    has_more = len(entries) > PAGE_SIZE
    entries = entries[:PAGE_SIZE]

    uid = request.user.pk
    entries_data = [
        {
            "rank": e.rank,
            "username": e.username,
            "score": e.score,
            "is_premium": e.is_premium,
            "is_current_user": e.user_id == uid,
        }
        for e in entries
    ]

    # User entry
    user_entry = None
    try:
        ue = ChallengeLeaderboardEntry.objects.get(challenge=challenge, user_id=uid)
        user_entry = {"rank": ue.rank, "score": ue.score}
    except ChallengeLeaderboardEntry.DoesNotExist:
        pass

    participant_count = ChallengeParticipant.objects.filter(challenge=challenge).count()
    sponsors = list(challenge.sponsors.all())
    rewards = list(challenge.rewards.order_by("rank_threshold"))

    if is_ajax:
        return JsonResponse({
            "entries": entries_data,
            "has_more": has_more,
            "user_entry": user_entry,
        })

    # Hexagons GeoJSON for map display
    hexagons_geojson = _build_hexagons_geojson(challenge)

    return render(request, "challenges/challenge_detail.html", {
        "challenge": challenge,
        "is_active": is_active,
        "is_upcoming": is_upcoming,
        "is_ended": is_ended,
        "is_participant": is_participant,
        "can_join": can_join,
        "entries": entries_data,
        "has_more": has_more,
        "user_entry": user_entry,
        "participant_count": participant_count,
        "sponsors": sponsors,
        "rewards": rewards,
        "hexagons_geojson": hexagons_geojson,
    })


def _build_hexagons_geojson(challenge):
    """Build a GeoJSON FeatureCollection of the challenge hexagons."""
    import json

    from django.contrib.gis.geos import GEOSGeometry

    hexagons = (
        challenge.challenge_hexagons.select_related("hexagon")
        .values_list("hexagon__geom", "hexagon__owner_id")
    )

    features = []
    for geom_wkt, owner_id in hexagons:
        geom = GEOSGeometry(geom_wkt)
        features.append({
            "type": "Feature",
            "geometry": json.loads(geom.geojson),
            "properties": {"owner_id": owner_id},
        })

    return json.dumps({"type": "FeatureCollection", "features": features})


@require_POST
@login_required
def join_challenge(request, pk):
    challenge = get_object_or_404(Challenge, pk=pk)
    now = timezone.now()

    # Can only join active or upcoming challenges
    if challenge.end_date < now:
        return redirect("challenge_detail", pk=pk)

    # Premium gate
    if challenge.premium_only:
        if not hasattr(request.user, "profile") or not request.user.profile.is_premium:
            return redirect("challenge_detail", pk=pk)

    ChallengeParticipant.objects.get_or_create(
        challenge=challenge,
        user=request.user,
    )

    return redirect("challenge_detail", pk=pk)
