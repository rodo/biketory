from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import render

from statistics.models import LeaderboardEntry

PAGE_SIZE = 20
NEIGHBORS = 2


def _entry_dict(e, rank_field, count_field, current_user_id):
    return {
        "rank": getattr(e, rank_field),
        "username": e.username,
        "count": getattr(e, count_field),
        "is_premium": e.is_premium,
        "is_current_user": e.user_id == current_user_id,
    }


@login_required
def leaderboard(request):
    lb_type = request.GET.get("type", "conquered")
    if lb_type not in ("conquered", "acquired"):
        lb_type = "conquered"

    offset = int(request.GET.get("offset", 0))
    is_ajax = request.headers.get("X-Requested-With") == "XMLHttpRequest"

    if lb_type == "conquered":
        order_field = "rank_conquered"
        count_field = "hexagons_conquered"
        rank_field = "rank_conquered"
    else:
        order_field = "rank_acquired"
        count_field = "hexagons_acquired"
        rank_field = "rank_acquired"

    qs = LeaderboardEntry.objects.order_by(order_field)
    entries = list(qs[offset:offset + PAGE_SIZE + 1])
    has_more = len(entries) > PAGE_SIZE
    entries = entries[:PAGE_SIZE]

    uid = request.user.pk
    entries_data = [_entry_dict(e, rank_field, count_field, uid) for e in entries]

    # Current user entry
    user_entry = None
    try:
        ue = LeaderboardEntry.objects.get(user_id=uid)
        user_entry = {
            "rank": getattr(ue, rank_field),
            "count": getattr(ue, count_field),
        }
    except LeaderboardEntry.DoesNotExist:
        pass

    # User neighborhood (2 before, user, 2 after) for bottom snippet
    user_visible = any(e["is_current_user"] for e in entries_data)
    user_neighborhood = None
    if user_entry and not user_visible:
        user_rank = user_entry["rank"]
        # Entries with rank in [user_rank - NEIGHBORS, user_rank + NEIGHBORS]
        neighbors = list(
            qs.filter(
                **{
                    f"{rank_field}__gte": max(1, user_rank - NEIGHBORS),
                    f"{rank_field}__lte": user_rank + NEIGHBORS,
                }
            )
        )
        user_neighborhood = [
            _entry_dict(e, rank_field, count_field, uid) for e in neighbors
        ]

    if is_ajax:
        return JsonResponse({
            "entries": entries_data,
            "has_more": has_more,
            "user_entry": user_entry,
            "user_neighborhood": user_neighborhood,
        })

    # Get computed_at from first entry
    computed_at = None
    first = LeaderboardEntry.objects.first()
    if first:
        computed_at = first.computed_at

    from geozones.models import GeoZone
    zone_countries = list(
        GeoZone.objects.filter(admin_level=2, active=True).order_by("name")
    )

    return render(request, "traces/leaderboard.html", {
        "entries": entries_data,
        "has_more": has_more,
        "user_entry": user_entry,
        "user_neighborhood": user_neighborhood,
        "lb_type": lb_type,
        "computed_at": computed_at,
        "zone_countries": zone_countries,
    })
