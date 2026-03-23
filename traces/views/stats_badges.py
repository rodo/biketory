from django.contrib.auth import get_user_model
from django.db.models import Count
from django.shortcuts import render

from traces.badges import BADGE_CATALOGUE
from traces.models import UserBadge

_BADGE_LOOKUP = {}
for _cat in BADGE_CATALOGUE:
    for _b in _cat["badges"]:
        _BADGE_LOOKUP[_b["id"]] = _b


def stats_badges(request):
    total_badges = UserBadge.objects.count()
    users_with_badges = UserBadge.objects.values("user").distinct().count()
    total_users = get_user_model().objects.count()
    avg_badges = round(total_badges / users_with_badges, 1) if users_with_badges else 0

    # Count per badge_id
    badge_counts = {
        row["badge_id"]: row["cnt"]
        for row in UserBadge.objects.values("badge_id").annotate(cnt=Count("id"))
    }

    def _enrich(badge_id, cnt):
        info = _BADGE_LOOKUP.get(badge_id, {})
        pct = round(cnt / total_users * 100, 1) if total_users else 0
        return {"id": badge_id, "name": info.get("name", badge_id), "pct": pct, "cnt": cnt}

    all_badge_stats = [_enrich(bid, cnt) for bid, cnt in badge_counts.items()]
    for bid, info in _BADGE_LOOKUP.items():
        if bid not in badge_counts:
            all_badge_stats.append({"id": bid, "name": info["name"], "pct": 0, "cnt": 0})

    rarest = sorted(all_badge_stats, key=lambda b: b["cnt"])[:5]
    most_common = sorted(all_badge_stats, key=lambda b: -b["cnt"])[:5]

    # Leaderboard top 10
    badge_leaderboard = (
        UserBadge.objects
        .values("user__username")
        .annotate(cnt=Count("id"))
        .order_by("-cnt")[:10]
    )

    # Recent activity
    recent_badges = UserBadge.objects.select_related("user").order_by("-earned_at")[:10]
    recent_activity = []
    for ub in recent_badges:
        info = _BADGE_LOOKUP.get(ub.badge_id, {})
        recent_activity.append({
            "id": ub.badge_id,
            "name": info.get("name", ub.badge_id),
            "username": ub.user.username,
            "earned_at": ub.earned_at,
        })

    return render(request, "traces/stats_badges.html", {
        "total_badges": total_badges,
        "avg_badges": avg_badges,
        "rarest": rarest,
        "most_common": most_common,
        "badge_leaderboard": badge_leaderboard,
        "recent_activity": recent_activity,
    })
