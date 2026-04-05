import json

from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import render

from statistics.models import ClusterLeaderboardEntry

PAGE_SIZE = 20
NEIGHBORS = 2
TOP_N = 3


def _entry_dict(e, current_user_id):
    return {
        "rank": e.rank,
        "username": e.username,
        "hex_count": e.largest_cluster_hex_count,
        "area_km2": round(e.largest_cluster_area_m2 / 1_000_000, 2),
        "is_premium": e.is_premium,
        "is_current_user": e.user_id == current_user_id,
    }


def _top_entry_data(e):
    geojson = None
    if e.largest_cluster_geom:
        geojson = {
            "type": "FeatureCollection",
            "features": [{
                "type": "Feature",
                "geometry": json.loads(e.largest_cluster_geom.geojson),
                "properties": {},
            }],
        }
    return {
        "rank": e.rank,
        "username": e.username,
        "hex_count": e.largest_cluster_hex_count,
        "area_km2": round(e.largest_cluster_area_m2 / 1_000_000, 2),
        "geojson": json.dumps(geojson) if geojson else "null",
    }


@login_required
def cluster_leaderboard(request):
    offset = int(request.GET.get("offset", 0))
    is_ajax = request.headers.get("X-Requested-With") == "XMLHttpRequest"

    qs = ClusterLeaderboardEntry.objects.order_by("rank")
    entries = list(qs[offset : offset + PAGE_SIZE + 1])
    has_more = len(entries) > PAGE_SIZE
    entries = entries[:PAGE_SIZE]

    uid = request.user.pk
    entries_data = [_entry_dict(e, uid) for e in entries]

    # Current user entry
    user_entry = None
    try:
        ue = ClusterLeaderboardEntry.objects.get(user_id=uid)
        user_entry = {
            "rank": ue.rank,
            "hex_count": ue.largest_cluster_hex_count,
            "area_km2": round(ue.largest_cluster_area_m2 / 1_000_000, 2),
        }
    except ClusterLeaderboardEntry.DoesNotExist:
        pass

    # Neighborhood
    user_visible = any(e["is_current_user"] for e in entries_data)
    user_neighborhood = None
    if user_entry and not user_visible:
        user_rank = user_entry["rank"]
        neighbors = list(
            qs.filter(
                rank__gte=max(1, user_rank - NEIGHBORS),
                rank__lte=user_rank + NEIGHBORS,
            )
        )
        user_neighborhood = [_entry_dict(e, uid) for e in neighbors]

    if is_ajax:
        return JsonResponse(
            {
                "entries": entries_data,
                "has_more": has_more,
                "user_entry": user_entry,
                "user_neighborhood": user_neighborhood,
            }
        )

    # Top 3 with individual geometry for separate maps
    top_entries = list(qs.filter(rank__lte=TOP_N)[:TOP_N])
    top_data = [_top_entry_data(e) for e in top_entries]

    computed_at = None
    first = ClusterLeaderboardEntry.objects.first()
    if first:
        computed_at = first.computed_at

    return render(
        request,
        "traces/cluster_leaderboard.html",
        {
            "entries": entries_data,
            "has_more": has_more,
            "user_entry": user_entry,
            "user_neighborhood": user_neighborhood,
            "top_entries": top_data,
            "computed_at": computed_at,
        },
    )
