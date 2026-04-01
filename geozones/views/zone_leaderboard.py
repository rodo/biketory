from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render

from geozones.models import GeoZone, ZoneLeaderboardEntry

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
def zone_leaderboard(request, zone_code):
    if not request.user.profile.is_premium:
        return redirect("subscription_required")

    zone = get_object_or_404(GeoZone, code=zone_code, active=True)

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

    qs = ZoneLeaderboardEntry.objects.filter(zone=zone).order_by(order_field)
    entries = list(qs[offset:offset + PAGE_SIZE + 1])
    has_more = len(entries) > PAGE_SIZE
    entries = entries[:PAGE_SIZE]

    uid = request.user.pk
    entries_data = [_entry_dict(e, rank_field, count_field, uid) for e in entries]

    # Extract user entry from loaded entries if present, else single query
    user_entry = None
    for e in entries:
        if e.user_id == uid:
            user_entry = {
                "rank": getattr(e, rank_field),
                "count": getattr(e, count_field),
            }
            break
    if user_entry is None:
        try:
            ue = ZoneLeaderboardEntry.objects.get(zone=zone, user_id=uid)
            user_entry = {
                "rank": getattr(ue, rank_field),
                "count": getattr(ue, count_field),
            }
        except ZoneLeaderboardEntry.DoesNotExist:
            pass

    # User neighborhood
    user_visible = any(e["is_current_user"] for e in entries_data)
    user_neighborhood = None
    if user_entry and not user_visible:
        user_rank = user_entry["rank"]
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

    # computed_at from already-loaded entries (no extra query)
    computed_at = entries[0].computed_at if entries else None

    # Sidebar zones: countries + children in a single query
    nav_zones = list(
        GeoZone.objects.filter(
            Q(admin_level=2) | Q(parent=zone),
            active=True,
        ).order_by("admin_level", "name")
    )
    zone_countries = [z for z in nav_zones if z.admin_level == 2]
    zone_children = [z for z in nav_zones if z.parent_id == zone.pk]

    return render(request, "geozones/zone_leaderboard.html", {
        "entries": entries_data,
        "has_more": has_more,
        "user_entry": user_entry,
        "user_neighborhood": user_neighborhood,
        "lb_type": lb_type,
        "computed_at": computed_at,
        "zone": zone,
        "zone_countries": zone_countries,
        "zone_children": zone_children,
    })
