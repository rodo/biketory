from django.shortcuts import render

from ..badges import BADGE_CATALOGUE
from ..models import UserBadge


def badges(request):
    earned_ids = set()
    if request.user.is_authenticated:
        earned_ids = set(
            UserBadge.objects.filter(user=request.user).values_list("badge_id", flat=True)
        )

    catalogue = []
    for group in BADGE_CATALOGUE:
        enriched = []
        for badge in group["badges"]:
            enriched.append({**badge, "earned": badge["id"] in earned_ids})
        catalogue.append({"category": group["category"], "badges": enriched})

    total = sum(len(g["badges"]) for g in BADGE_CATALOGUE)
    earned_count = len(earned_ids)

    return render(request, "traces/badges.html", {
        "catalogue": catalogue,
        "total": total,
        "earned_count": earned_count,
    })
