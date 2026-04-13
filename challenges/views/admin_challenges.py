import json
from datetime import datetime

from dateutil.relativedelta import relativedelta
from django.contrib.admin.views.decorators import staff_member_required
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from challenges.models import (
    Challenge,
    ChallengeHexagon,
    ChallengeLeaderboardEntry,
    ChallengeReward,
    ChallengeSponsor,
    Dataset,
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
        goal_raw = request.POST.get("goal_threshold", "").strip()
        zone_admin_raw = request.POST.get("zone_admin_level", "").strip()
        hex_per_zone_raw = request.POST.get("hexagons_per_zone", "").strip()

        dataset_raw = request.POST.get("dataset", "").strip()

        challenge = Challenge.objects.create(
            title=request.POST["title"],
            description=request.POST.get("description", ""),
            challenge_type=request.POST["challenge_type"],
            capture_mode=request.POST.get("capture_mode") or None,
            premium_only=request.POST.get("premium_only") == "on",
            is_visible=request.POST.get("is_visible") == "on",
            geozone_id=request.POST.get("geozone") or None,
            dataset_id=int(dataset_raw) if dataset_raw else None,
            goal_threshold=int(goal_raw) if goal_raw else None,
            zone_admin_level=int(zone_admin_raw) if zone_admin_raw else None,
            hexagons_per_zone=int(hex_per_zone_raw) if hex_per_zone_raw else None,
            start_date=timezone.make_aware(datetime.strptime(request.POST["start_date"], "%Y-%m-%d")),
            end_date=timezone.make_aware(datetime.strptime(request.POST["end_date"], "%Y-%m-%d")),
            created_by=request.user,
        )

        # Hexagons from map selection (only for types that use them)
        hexagon_ids_raw = request.POST.get("hexagon_ids", "")
        if hexagon_ids_raw and challenge.challenge_type in (Challenge.TYPE_CAPTURE_HEXAGON, Challenge.TYPE_MAX_POINTS):
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

    admin_levels = (
        GeoZone.objects.filter(active=True)
        .values_list("admin_level", flat=True)
        .distinct()
        .order_by("admin_level")
    )

    datasets = Dataset.objects.all().order_by("name")

    return render(request, "challenges/admin_challenge_create.html", {
        "geozones": geozones,
        "datasets": datasets,
        "challenge_types": Challenge.TYPE_CHOICES,
        "capture_modes": Challenge.CAPTURE_MODE_CHOICES,
        "reward_types": ChallengeReward.REWARD_TYPE_CHOICES,
        "admin_levels": admin_levels,
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

    # Hexagons GeoJSON (only for types that use hexagons)
    hexagons_geojson = {"type": "FeatureCollection", "features": []}
    if challenge.challenge_type in (Challenge.TYPE_CAPTURE_HEXAGON, Challenge.TYPE_MAX_POINTS):
        from challenges.views.challenge_detail import _build_hexagons_geojson
        hexagons_geojson = _build_hexagons_geojson(challenge)

    # Dataset GeoJSON for dataset_points challenges
    dataset_geojson = {"type": "FeatureCollection", "features": []}
    has_dataset = (
        challenge.challenge_type == Challenge.TYPE_DATASET_POINTS
        and challenge.dataset_id is not None
    )
    if has_dataset:
        from challenges.views.challenge_detail import _build_dataset_geojson
        dataset_geojson = _build_dataset_geojson(challenge)

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
        "has_dataset": has_dataset,
        "dataset_geojson": dataset_geojson,
    })


@staff_member_required
def admin_challenge_duplicate(request, pk):
    """Duplicate a challenge with dates set to the entire next month."""
    source = get_object_or_404(Challenge, pk=pk)

    today = timezone.now().date()
    first_of_next_month = (today.replace(day=1) + relativedelta(months=1))
    last_of_next_month = first_of_next_month + relativedelta(months=1, days=-1)

    start = timezone.make_aware(datetime.combine(first_of_next_month, datetime.min.time()))
    end = timezone.make_aware(datetime.combine(last_of_next_month, datetime.max.time()))

    clone = Challenge.objects.create(
        title=source.title,
        description=source.description,
        challenge_type=source.challenge_type,
        capture_mode=source.capture_mode,
        premium_only=source.premium_only,
        is_visible=False,
        geozone=source.geozone,
        dataset=source.dataset,
        goal_threshold=source.goal_threshold,
        zone_admin_level=source.zone_admin_level,
        hexagons_per_zone=source.hexagons_per_zone,
        start_date=start,
        end_date=end,
        created_by=request.user,
    )

    # Copy hexagons
    source_hexagons = ChallengeHexagon.objects.filter(challenge=source)
    if source_hexagons.exists():
        ChallengeHexagon.objects.bulk_create([
            ChallengeHexagon(challenge=clone, hexagon_id=ch.hexagon_id)
            for ch in source_hexagons
        ])

    # Copy rewards
    source_rewards = ChallengeReward.objects.filter(challenge=source)
    if source_rewards.exists():
        ChallengeReward.objects.bulk_create([
            ChallengeReward(
                challenge=clone,
                rank_threshold=r.rank_threshold,
                reward_type=r.reward_type,
                badge_id=r.badge_id,
            )
            for r in source_rewards
        ])

    # Copy sponsors (without logo)
    source_sponsors = ChallengeSponsor.objects.filter(challenge=source)
    if source_sponsors.exists():
        ChallengeSponsor.objects.bulk_create([
            ChallengeSponsor(
                challenge=clone,
                name=s.name,
                url=s.url,
            )
            for s in source_sponsors
        ])

    return redirect("admin_challenge_detail", pk=clone.pk)
