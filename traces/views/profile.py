import json

from django.contrib.auth.decorators import login_required
from django.db.models import Count, Q, Sum
from django.shortcuts import render

from traces.models import (
    Friendship,
    Hexagon,
    HexagonScore,
    Trace,
    UserBadge,
    UserProfile,
)


@login_required
def profile(request):
    user = request.user

    traces_count = Trace.objects.filter(uploaded_by=user).count()
    first_trace_date = (
        Trace.objects.filter(uploaded_by=user)
        .order_by("first_point_date")
        .values_list("first_point_date", flat=True)
        .first()
    )

    scores = HexagonScore.objects.filter(user=user, points__gte=1).aggregate(
        hexagons_count=Count("hexagon"),
        total_points=Sum("points"),
    )
    hexagons_count = scores["hexagons_count"] or 0
    total_points = scores["total_points"] or 0

    hexagon_ids = HexagonScore.objects.filter(user=user, points__gte=1).values_list("hexagon_id", flat=True)
    hexagons = Hexagon.objects.filter(pk__in=hexagon_ids)

    score_map = {
        s.hexagon_id: s.points
        for s in HexagonScore.objects.filter(user=user, points__gte=1)
    }

    hexagons_geojson = json.dumps({
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "geometry": json.loads(h.geom.geojson),
                "properties": {"points": score_map.get(h.pk, 0)},
            }
            for h in hexagons
        ],
    })

    # Friends summary
    pending_received = Friendship.objects.filter(
        to_user=user, status=Friendship.STATUS_PENDING
    ).select_related("from_user")

    friends_count = Friendship.objects.filter(
        Q(from_user=user, status=Friendship.STATUS_ACCEPTED) |
        Q(to_user=user, status=Friendship.STATUS_ACCEPTED)
    ).count()

    badges_earned = UserBadge.objects.filter(user=user).count()

    user_profile, _created = UserProfile.objects.get_or_create(user=user)
    home_location = user_profile.home_location

    return render(request, "traces/profile.html", {
        "traces_count": traces_count,
        "first_trace_date": first_trace_date,
        "hexagons_count": hexagons_count,
        "total_points": total_points,
        "hexagons_geojson": hexagons_geojson,
        "friends_count": friends_count,
        "pending_received": pending_received,
        "home_location": home_location,
        "badges_earned": badges_earned,
    })
