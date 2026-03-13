import json

from django.db.models import Q
from django.shortcuts import render

from traces.models import Friendship, HexagonScore


def landing(request):
    current_user = request.user.username if request.user.is_authenticated else None

    # Collect friend usernames for the current user
    friend_usernames = set()
    if request.user.is_authenticated:
        pairs = Friendship.objects.filter(
            Q(from_user=request.user, status=Friendship.STATUS_ACCEPTED) |
            Q(to_user=request.user, status=Friendship.STATUS_ACCEPTED)
        ).values_list("from_user__username", "to_user__username")
        for a, b in pairs:
            friend_usernames.add(b if a == current_user else a)

    scores = HexagonScore.objects.select_related("hexagon", "user")
    features = [
        {
            "type": "Feature",
            "geometry": json.loads(s.hexagon.geom.geojson),
            "properties": {
                "hexagon_id": s.hexagon_id,
                "username": s.user.username,
                "points": s.points,
                "is_friend": s.user.username in friend_usernames,
            },
        }
        for s in scores
    ]
    geojson = json.dumps({"type": "FeatureCollection", "features": features})

    return render(request, "traces/landing.html", {
        "geojson": geojson,
        "current_user": current_user,
        "friend_usernames": json.dumps(list(friend_usernames)),
    })
