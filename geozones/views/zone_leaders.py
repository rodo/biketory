from django.contrib.auth.decorators import login_required
from django.shortcuts import render

from geozones.models import GeoZone, ZoneLeaderboardEntry

TOP_N = 3


@login_required
def zone_leaders(request):
    lb_type = request.GET.get("type", "conquered")
    if lb_type not in ("conquered", "acquired"):
        lb_type = "conquered"

    if lb_type == "conquered":
        rank_field = "rank_conquered"
        count_field = "hexagons_conquered"
    else:
        rank_field = "rank_acquired"
        count_field = "hexagons_acquired"

    zones = GeoZone.objects.filter(active=True).order_by("admin_level", "name")
    uid = request.user.pk

    zone_data = []
    for zone in zones:
        top = list(
            ZoneLeaderboardEntry.objects.filter(zone=zone)
            .order_by(rank_field)[:TOP_N]
        )
        leaders = [
            {
                "rank": getattr(e, rank_field),
                "username": e.username,
                "count": getattr(e, count_field),
                "is_premium": e.is_premium,
                "is_current_user": e.user_id == uid,
            }
            for e in top
        ]

        # Current user rank in this zone
        user_rank = None
        try:
            ue = ZoneLeaderboardEntry.objects.get(zone=zone, user_id=uid)
            user_rank = {
                "rank": getattr(ue, rank_field),
                "count": getattr(ue, count_field),
            }
        except ZoneLeaderboardEntry.DoesNotExist:
            pass

        zone_data.append({
            "zone": zone,
            "leaders": leaders,
            "user_rank": user_rank,
        })

    return render(request, "geozones/zone_leaders.html", {
        "zone_data": zone_data,
        "lb_type": lb_type,
    })
