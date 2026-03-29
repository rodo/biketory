import json
from datetime import timedelta

from django.contrib.auth.decorators import login_required
from django.db.models import Count, Q, Sum
from django.shortcuts import redirect, render
from django.utils import timezone
from django.utils.translation import gettext as _

from traces.base62 import uuid_to_base62
from traces.models import (
    ApiToken,
    Friendship,
    Hexagon,
    HexagonScore,
    Subscription,
    Trace,
    UserBadge,
    UserProfile,
    UserSurfaceStats,
)


@login_required
def profile(request):
    if request.method == "POST":
        action = request.POST.get("action")

        if action == "generate_token":
            sub = Subscription.objects.filter(user=request.user).first()
            if sub and sub.is_active():
                ApiToken.objects.filter(user=request.user).delete()
                ApiToken.objects.create(
                    user=request.user,
                    expires_at=timezone.now() + timedelta(days=31),
                )
            return redirect("/profile/?tab=settings")

        if action == "update_home_location":
            try:
                lat = float(request.POST.get("lat", ""))
                lng = float(request.POST.get("lng", ""))
                from django.contrib.gis.geos import Point
                profile, _created = UserProfile.objects.get_or_create(user=request.user)
                profile.home_location = Point(lng, lat, srid=4326)
                profile.save(update_fields=["home_location"])
            except (ValueError, TypeError):
                pass
            return redirect("/profile/?tab=settings")

        if action == "update_email":
            new_email = request.POST.get("email", "").strip()
            email_error = None
            if not new_email:
                email_error = _("The email address cannot be empty.")
            elif "@" not in new_email:
                email_error = _("Invalid email address.")
            else:
                from django.contrib.auth import get_user_model
                user = get_user_model()
                if user.objects.filter(email=new_email).exclude(pk=request.user.pk).exists():
                    email_error = _("This email address is already in use.")
                else:
                    request.user.email = new_email
                    request.user.save(update_fields=["email"])
                    return redirect("/profile/?tab=settings")
            # Fall through to render with error
            request.email_error = email_error
    user = request.user

    traces_count = Trace.objects.filter(uploaded_by=user).count()
    first_trace_date = (
        Trace.objects.filter(uploaded_by=user)
        .order_by("first_point_date")
        .values_list("first_point_date", flat=True)
        .first()
    )

    scores = HexagonScore.objects.filter(user=user, points__gte=1).aggregate(
        hexagons_count=Count("hexagon"),
        total_points=Sum("points"),
    )
    hexagons_count = scores["hexagons_count"] or 0
    total_points = scores["total_points"] or 0

    hexagon_ids = HexagonScore.objects.filter(user=user, points__gte=1).values_list("hexagon_id", flat=True)
    hexagons = Hexagon.objects.filter(pk__in=hexagon_ids)

    score_map = {
        s.hexagon_id: s.points
        for s in HexagonScore.objects.filter(user=user, points__gte=1)
    }

    hexagons_geojson = json.dumps({
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "geometry": json.loads(h.geom.geojson),
                "properties": {"points": score_map.get(h.pk, 0)},
            }
            for h in hexagons
        ],
    })

    stats, _created = UserSurfaceStats.objects.get_or_create(user=user)

    # Friends summary
    pending_received = Friendship.objects.filter(
        to_user=user, status=Friendship.STATUS_PENDING
    ).select_related("from_user")

    friends_count = Friendship.objects.filter(
        Q(from_user=user, status=Friendship.STATUS_ACCEPTED) |
        Q(to_user=user, status=Friendship.STATUS_ACCEPTED)
    ).count()

    badges_earned = UserBadge.objects.filter(user=user).count()
    sub = Subscription.objects.filter(user=user).first()
    is_premium = sub is not None and sub.is_active()
    api_token = ApiToken.objects.filter(user=user).first() if is_premium else None
    email_error = getattr(request, "email_error", None)
    home_location = stats.profile.home_location if hasattr(stats, "profile") else None
    user_profile, _created = UserProfile.objects.get_or_create(user=user)
    home_location = user_profile.home_location

    share_code = uuid_to_base62(stats.secret_uuid)
    share_url = request.build_absolute_uri(f"/s/{share_code}/")

    return render(request, "traces/profile.html", {
        "traces_count": traces_count,
        "first_trace_date": first_trace_date,
        "hexagons_count": hexagons_count,
        "total_points": total_points,
        "hexagons_geojson": hexagons_geojson,
        "secret_uuid": stats.secret_uuid,
        "share_url": share_url,
        "friends_count": friends_count,
        "pending_received": pending_received,
        "api_token": api_token,
        "is_premium": is_premium,
        "email_error": email_error,
        "home_location": home_location,
        "badges_earned": badges_earned,
    })
