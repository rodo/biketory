import json

from django.conf import settings
from django.contrib.gis.geos import Polygon
from django.db.models import Q
from django.http import JsonResponse
from django.shortcuts import render

from traces.models import Friendship, HexagonScore, UserProfile


def _friend_usernames(user):
    """Return the set of friend usernames for the given user."""
    if not user.is_authenticated:
        return set()
    current = user.username
    pairs = Friendship.objects.filter(
        Q(from_user=user, status=Friendship.STATUS_ACCEPTED)
        | Q(to_user=user, status=Friendship.STATUS_ACCEPTED)
    ).values_list("from_user__username", "to_user__username")
    return {b if a == current else a for a, b in pairs}


def landing(request):
    last_center = None
    if not request.user.is_authenticated:
        last_score = (
            HexagonScore.objects.filter(points__gt=0)
            .select_related("hexagon")
            .order_by("-last_earned_at")
            .first()
        )
        if last_score:
            centroid = last_score.hexagon.geom.centroid
            last_center = [centroid.y, centroid.x]
    is_premium = False
    user_tile_prefix = ""
    if request.user.is_authenticated:
        is_premium = request.user.profile.is_premium
        if is_premium:
            hexagram = UserProfile.objects.values_list("hexagram", flat=True).get(user=request.user)
            user_tile_prefix = f"{hexagram[0]}/{hexagram[1]}/{hexagram}"

    return render(request, "traces/landing.html", {
        "last_center": json.dumps(last_center),
        "is_premium": is_premium,
        "user_tile_prefix": user_tile_prefix,
    })


def landing_hexagons(request):
    show_own_dynamic = getattr(settings, "LANDING_SHOW_OWN_DYNAMIC_HEXAGONS", True)
    show_others_dynamic = getattr(settings, "LANDING_SHOW_OTHER_DYNAMIC_HEXAGONS", True)

    current_user = request.user.username if request.user.is_authenticated else None
    friends = _friend_usernames(request.user)

    scores = HexagonScore.objects.filter(points__gt=0).select_related("hexagon", "user")

    bbox_param = request.GET.get("bbox")
    if bbox_param:
        west, south, east, north = map(float, bbox_param.split(","))
        bbox_poly = Polygon.from_bbox((west, south, east, north))
        scores = scores.filter(hexagon__geom__bboverlaps=bbox_poly)

    if not request.user.is_authenticated:
        if not show_others_dynamic:
            scores = scores.none()
    elif not show_own_dynamic and not show_others_dynamic:
        scores = scores.none()
    elif not show_own_dynamic:
        scores = scores.exclude(user=request.user)
    elif not show_others_dynamic:
        scores = scores.filter(user=request.user)

    features = [
        {
            "type": "Feature",
            "geometry": json.loads(s.hexagon.geom.geojson),
            "properties": {
                "hexagon_id": s.hexagon_id,
                "username": s.user.username,
                "points": s.points,
                "is_friend": s.user.username in friends,
            },
        }
        for s in scores
    ]
    return JsonResponse({
        "geojson": {"type": "FeatureCollection", "features": features},
        "current_user": current_user,
        "friend_usernames": sorted(friends),
    })
