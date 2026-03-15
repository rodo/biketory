import json
from datetime import timedelta

from django.contrib.auth.decorators import login_required
from django.db.models import Count, Q, Sum
from django.shortcuts import redirect, render
from django.utils import timezone

from traces.models import ApiToken, Friendship, Hexagon, HexagonScore, Trace, UserSurfaceStats


@login_required
def profile(request):
    if request.method == "POST" and request.POST.get("action") == "generate_token":
        ApiToken.objects.filter(user=request.user).delete()
        ApiToken.objects.create(
            user=request.user,
            expires_at=timezone.now() + timedelta(days=31),
        )
        return redirect("profile")
    user = request.user

    traces_count = Trace.objects.filter(uploaded_by=user).count()
    first_trace_date = (
        Trace.objects.filter(uploaded_by=user)
        .order_by("first_point_date")
        .values_list("first_point_date", flat=True)
        .first()
    )

    scores = HexagonScore.objects.filter(user=user).aggregate(
        hexagons_count=Count("hexagon"),
        total_points=Sum("points"),
    )
    hexagons_count = scores["hexagons_count"] or 0
    total_points = scores["total_points"] or 0

    hexagon_ids = HexagonScore.objects.filter(user=user).values_list("hexagon_id", flat=True)
    hexagons = Hexagon.objects.filter(pk__in=hexagon_ids)

    score_map = {
        s.hexagon_id: s.points
        for s in HexagonScore.objects.filter(user=user)
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

    stats, _ = UserSurfaceStats.objects.get_or_create(user=user)

    # Friends summary
    pending_received = Friendship.objects.filter(
        to_user=user, status=Friendship.STATUS_PENDING
    ).select_related("from_user")

    friends_count = Friendship.objects.filter(
        Q(from_user=user, status=Friendship.STATUS_ACCEPTED) |
        Q(to_user=user, status=Friendship.STATUS_ACCEPTED)
    ).count()

    api_token = ApiToken.objects.filter(user=user).first()

    return render(request, "traces/profile.html", {
        "traces_count": traces_count,
        "first_trace_date": first_trace_date,
        "hexagons_count": hexagons_count,
        "total_points": total_points,
        "hexagons_geojson": hexagons_geojson,
        "secret_uuid": stats.secret_uuid,
        "friends_count": friends_count,
        "pending_received": pending_received,
        "api_token": api_token,
    })
