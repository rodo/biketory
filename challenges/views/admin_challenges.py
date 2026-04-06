import json

from django.contrib.admin.views.decorators import staff_member_required
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from challenges.models import (
    Challenge,
    ChallengeHexagon,
    ChallengeLeaderboardEntry,
    ChallengeReward,
    ChallengeSponsor,
)
from geozones.models import GeoZone


@staff_member_required
def admin_challenges(request):
    now = timezone.now()
    active = Challenge.objects.filter(start_date__lte=now, end_date__gte=now).order_by("end_date")
    upcoming = Challenge.objects.filter(start_date__gt=now).order_by("start_date")
    ended = Challenge.objects.filter(end_date__lt=now).order_by("-end_date")[:20]

    return render(request, "challenges/admin_challenges.html", {
        "active_challenges": active,
        "upcoming_challenges": upcoming,
        "ended_challenges": ended,
    })


@staff_member_required
def admin_challenge_create(request):
    geozones = GeoZone.objects.filter(active=True).order_by("name")

    if request.method == "POST":
        challenge = Challenge.objects.create(
            title=request.POST["title"],
            description=request.POST.get("description", ""),
            challenge_type=request.POST["challenge_type"],
            capture_mode=request.POST.get("capture_mode") or None,
            premium_only=request.POST.get("premium_only") == "on",
            geozone_id=request.POST.get("geozone") or None,
            start_date=request.POST["start_date"],
            end_date=request.POST["end_date"],
            created_by=request.user,
        )

        # Hexagons from map selection
        hexagon_ids_raw = request.POST.get("hexagon_ids", "")
        if hexagon_ids_raw:
            hexagon_ids = [int(h) for h in hexagon_ids_raw.split(",") if h.strip()]
            ChallengeHexagon.objects.bulk_create(
                [ChallengeHexagon(challenge=challenge, hexagon_id=hid) for hid in hexagon_ids],
                ignore_conflicts=True,
            )

        # Rewards
        reward_rows = request.POST.get("rewards_json", "")
        if reward_rows:
            rewards_data = json.loads(reward_rows)
            ChallengeReward.objects.bulk_create([
                ChallengeReward(
                    challenge=challenge,
                    rank_threshold=r["rank_threshold"],
                    reward_type=r["reward_type"],
                    badge_id=r.get("badge_id", ""),
                )
                for r in rewards_data
            ])

        # Sponsor
        sponsor_name = request.POST.get("sponsor_name", "").strip()
        if sponsor_name:
            ChallengeSponsor.objects.create(
                challenge=challenge,
                name=sponsor_name,
                url=request.POST.get("sponsor_url", ""),
                logo=request.FILES.get("sponsor_logo"),
            )

        return redirect("admin_challenge_detail", pk=challenge.pk)

    return render(request, "challenges/admin_challenge_create.html", {
        "geozones": geozones,
        "challenge_types": Challenge.TYPE_CHOICES,
        "capture_modes": Challenge.CAPTURE_MODE_CHOICES,
        "reward_types": ChallengeReward.REWARD_TYPE_CHOICES,
    })


@staff_member_required
def admin_challenge_detail(request, pk):
    challenge = get_object_or_404(Challenge, pk=pk)
    now = timezone.now()

    is_active = challenge.start_date <= now <= challenge.end_date
    is_ended = challenge.end_date < now

    entries = list(
        ChallengeLeaderboardEntry.objects.filter(challenge=challenge)
        .order_by("rank")[:50]
    )

    participant_count = challenge.participants.count()
    hexagon_count = challenge.challenge_hexagons.count()
    sponsors = list(challenge.sponsors.all())
    rewards = list(challenge.rewards.order_by("rank_threshold"))

    # Hexagons GeoJSON
    from challenges.views.challenge_detail import _build_hexagons_geojson
    hexagons_geojson = _build_hexagons_geojson(challenge)

    return render(request, "challenges/admin_challenge_detail.html", {
        "challenge": challenge,
        "is_active": is_active,
        "is_ended": is_ended,
        "entries": entries,
        "participant_count": participant_count,
        "hexagon_count": hexagon_count,
        "sponsors": sponsors,
        "rewards": rewards,
        "hexagons_geojson": hexagons_geojson,
    })
