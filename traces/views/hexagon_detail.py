from django.http import JsonResponse
from django.shortcuts import get_object_or_404

from traces.models import Hexagon, HexagonScore


def hexagon_detail(request, pk):
    get_object_or_404(Hexagon, pk=pk)
    scores = (
        HexagonScore.objects
        .filter(hexagon_id=pk)
        .select_related("user")
        .order_by("-last_earned_at")[:10]
    )
    return JsonResponse({
        "scores": [
            {
                "username": s.user.username,
                "points": s.points,
                "last_earned_at": s.last_earned_at.strftime("%Y-%m-%d %H:%M"),
            }
            for s in scores
        ]
    })
