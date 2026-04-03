import json
from pathlib import Path

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.db import connection
from django.db.models import Count, Sum
from django.shortcuts import render

from statistics.models import LeaderboardEntry
from traces.badges import BADGE_CATALOGUE
from traces.models import Hexagon, HexagonScore, Trace, UserBadge, UserProfile

_SQL_DIR = Path(__file__).resolve().parent.parent / "sql"
_STREAK_DAILY_SQL = (_SQL_DIR / "streak_daily.sql").read_text()
_DISTANCE_TOTAL_SQL = (_SQL_DIR / "distance_total.sql").read_text()
_DISTANCE_MONTHLY_SQL = (_SQL_DIR / "distance_monthly.sql").read_text()
_FRIEND_ACTIVITY_SQL = (_SQL_DIR / "dashboard_friend_activity.sql").read_text()


@login_required
def dashboard(request):
    user = request.user
    uid = user.pk

    # ── Hero: user info ──
    user_profile, _ = UserProfile.objects.get_or_create(user=user)

    # ── Hero: last trace mini-map ──
    last_trace = (
        Trace.objects.filter(uploaded_by=user)
        .order_by("-uploaded_at")
        .first()
    )
    route_geojson = None
    surfaces_geojson = None
    hexagons_geojson = None
    map_config = None
    if last_trace and last_trace.route:
        map_config = {
            "elementId": "mini-map",
            "tileUrl": settings.TILE_SERVER_URL,
            "zoomMin": settings.MAP_ZOOM_MIN,
            "zoomMax": settings.MAP_ZOOM_MAX,
            "zoomControl": False,
            "attribution": False,
        }
        route_geojson = {
            "type": "Feature",
            "geometry": json.loads(last_trace.route.geojson),
            "properties": {},
        }
        surfaces = last_trace.closed_surfaces.all()
        surfaces_geojson = {
            "type": "FeatureCollection",
            "features": [
                {
                    "type": "Feature",
                    "geometry": json.loads(s.polygon.geojson),
                    "properties": {},
                }
                for s in surfaces
            ],
        }
        from django.contrib.gis.db.models import Union
        surface_union = surfaces.aggregate(u=Union("polygon"))["u"]
        if surface_union:
            hexagons = Hexagon.objects.filter(geom__within=surface_union)
            scores = {
                s.hexagon_id: s.points
                for s in HexagonScore.objects.filter(hexagon__in=hexagons, user=user)
            }
            hexagons_geojson = {
                "type": "FeatureCollection",
                "features": [
                    {
                        "type": "Feature",
                        "geometry": json.loads(h.geom.geojson),
                        "properties": {"points": scores.get(h.pk, 0)},
                    }
                    for h in hexagons
                ],
            }

    # ── Stat cards ──
    traces_count = Trace.objects.filter(uploaded_by=user).count()

    scores = HexagonScore.objects.filter(user=user, points__gte=1).aggregate(
        hexagons_count=Count("hexagon"),
        total_points=Sum("points"),
    )
    hexagons_acquired = scores["hexagons_count"] or 0
    total_points = scores["total_points"] or 0

    leaderboard_entry = LeaderboardEntry.objects.filter(user_id=uid).first()
    rank_points = leaderboard_entry.rank_points if leaderboard_entry else None

    # ── Progression: streak & distance ──
    with connection.cursor() as cursor:
        cursor.execute(_STREAK_DAILY_SQL, [uid])
        streak_daily = cursor.fetchone()[0]

        cursor.execute(_DISTANCE_TOTAL_SQL, [uid])
        distance_total = round(cursor.fetchone()[0], 1)

        cursor.execute(_DISTANCE_MONTHLY_SQL, [uid])
        distance_monthly = round(cursor.fetchone()[0], 1)

    # ── Progression: last 3 badges ──
    badge_lookup = {}
    for cat in BADGE_CATALOGUE:
        for b in cat["badges"]:
            badge_lookup[b["id"]] = b

    recent_user_badges = (
        UserBadge.objects.filter(user=user)
        .order_by("-earned_at")[:3]
    )
    recent_badges = []
    for ub in recent_user_badges:
        info = badge_lookup.get(ub.badge_id)
        if info:
            recent_badges.append({
                "id": ub.badge_id,
                "name": info["name"],
                "earned_at": ub.earned_at,
            })

    # ── Friend activity ──
    with connection.cursor() as cursor:
        cursor.execute(_FRIEND_ACTIVITY_SQL, [uid, uid])
        columns = [col[0] for col in cursor.description]
        friend_activity = [dict(zip(columns, row, strict=True)) for row in cursor.fetchall()]

    return render(request, "traces/dashboard.html", {
        "user_profile": user_profile,
        "last_trace": last_trace,
        "map_config": map_config,
        "route_geojson": route_geojson,
        "surfaces_geojson": surfaces_geojson,
        "hexagons_geojson": hexagons_geojson,
        "traces_count": traces_count,
        "hexagons_acquired": hexagons_acquired,
        "total_points": total_points,
        "rank_points": rank_points,
        "streak_daily": streak_daily,
        "distance_total": distance_total,
        "distance_monthly": distance_monthly,
        "recent_badges": recent_badges,
        "friend_activity": friend_activity,
    })
