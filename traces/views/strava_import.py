import logging

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.gis.geos import Polygon
from django.core.files.base import ContentFile
from django.db import IntegrityError
from django.shortcuts import redirect, render
from django.utils.translation import gettext as _
from procrastinate.exceptions import AlreadyEnqueued

from traces.models import StravaImport, Trace
from traces.strava_client import (
    StravaAPIError,
    StravaNotConnectedError,
    fetch_activity_streams,
    fetch_recent_activities,
)
from traces.strava_gpx import build_gpx_from_streams
from traces.trace_processing import (
    MAX_TRACE_LENGTH_KM,
    _create_trace_hexagons,
    _parse_route,
    _upload_quota,
)

logger = logging.getLogger(__name__)

MAX_IMPORT_BATCH = 5


@login_required
def strava_activities(request):
    if not settings.STRAVA_AUTH_ENABLED:
        messages.error(request, _("Strava integration is not enabled."))
        return redirect("upload_trace")

    uploads_today, daily_limit, next_slot = _upload_quota(request.user)
    limit_reached = next_slot is not None

    activities = []
    strava_error = None
    strava_connected = True

    try:
        raw_activities = fetch_recent_activities(request.user)
        imported_ids = set(
            StravaImport.objects.filter(user=request.user)
            .values_list("strava_activity_id", flat=True)
        )
        for act in raw_activities:
            act["already_imported"] = act["id"] in imported_ids
            act["distance_km"] = act.get("distance", 0) / 1000
        activities = raw_activities
    except StravaNotConnectedError:
        strava_connected = False
    except StravaAPIError as e:
        strava_error = str(e)

    return render(request, "traces/strava_activities.html", {
        "activities": activities,
        "strava_connected": strava_connected,
        "strava_error": strava_error,
        "uploads_today": uploads_today,
        "daily_limit": daily_limit,
        "limit_reached": limit_reached,
        "next_slot": next_slot,
    })


@login_required
def strava_import(request):
    if request.method != "POST":
        return redirect("strava_activities")

    if not settings.STRAVA_AUTH_ENABLED:
        messages.error(request, _("Strava integration is not enabled."))
        return redirect("upload_trace")

    activity_ids = request.POST.getlist("activity_ids")
    if not activity_ids:
        messages.warning(request, _("No activities selected."))
        return redirect("strava_activities")

    activity_ids = activity_ids[:MAX_IMPORT_BATCH]
    imported_count = 0
    skipped_count = 0

    for raw_id in activity_ids:
        try:
            activity_id = int(raw_id)
        except (ValueError, TypeError):
            continue

        uploads_today, daily_limit, next_slot = _upload_quota(request.user)
        if next_slot is not None:
            messages.warning(request, _("Daily upload limit reached."))
            break

        if StravaImport.objects.filter(user=request.user, strava_activity_id=activity_id).exists():
            skipped_count += 1
            continue

        try:
            streams = fetch_activity_streams(request.user, activity_id)
        except StravaAPIError as e:
            messages.error(request, str(e))
            break

        # We need activity metadata for GPX construction; fetch from the list
        # or build a minimal dict. The streams endpoint doesn't return metadata,
        # so we fetch the single activity.
        try:
            activity_meta = _fetch_activity_detail(request.user, activity_id)
        except StravaAPIError as e:
            messages.error(request, str(e))
            break

        gpx_bytes = build_gpx_from_streams(activity_meta, streams)
        if gpx_bytes is None:
            skipped_count += 1
            continue

        gpx_file = ContentFile(gpx_bytes, name=f"strava_{activity_id}.gpx")
        route, first_point_date, length_km = _parse_route(gpx_file)

        if length_km > MAX_TRACE_LENGTH_KM:
            skipped_count += 1
            continue

        if first_point_date and Trace.objects.filter(
            uploaded_by=request.user, first_point_date=first_point_date
        ).exists():
            skipped_count += 1
            continue

        trace = Trace.objects.create(
            gpx_file=gpx_file,
            route=route,
            length_km=length_km,
            first_point_date=first_point_date,
            uploaded_by=request.user,
        )

        if route:
            _create_trace_hexagons(route)
            extent = route.extent
            buf = 0.01
            bbox = Polygon.from_bbox((
                extent[0] - buf, extent[1] - buf,
                extent[2] + buf, extent[3] + buf,
            ))
            bbox.srid = 4326
            trace.bbox = bbox
            trace.save(update_fields=["bbox"])

        try:
            StravaImport.objects.create(
                user=request.user,
                strava_activity_id=activity_id,
                trace=trace,
            )
        except IntegrityError:
            skipped_count += 1
            continue

        _defer_post_upload_tasks(trace, request.user)
        imported_count += 1

    if imported_count == 1:
        _reward_referral_sponsor(request.user)

    if imported_count:
        messages.success(
            request,
            _("%(count)d trace(s) imported successfully.") % {"count": imported_count},
        )
    if skipped_count:
        messages.info(
            request,
            _("%(count)d activity(ies) skipped (already imported, no GPS, or too long).") % {"count": skipped_count},
        )

    return redirect("trace_list")


def _fetch_activity_detail(user, activity_id):
    """Fetch a single activity's metadata from Strava."""
    import requests

    from traces.strava_client import STRAVA_API_BASE, _get_social_token, _refresh_if_needed

    token = _get_social_token(user)
    token = _refresh_if_needed(token)

    resp = requests.get(
        f"{STRAVA_API_BASE}/activities/{activity_id}",
        headers={"Authorization": f"Bearer {token.token}"},
        timeout=15,
    )

    if resp.status_code == 429:
        raise StravaAPIError("Strava rate limit reached. Please try again later.", status_code=429)
    if resp.status_code != 200:
        raise StravaAPIError(f"Strava API error ({resp.status_code}).", status_code=resp.status_code)

    return resp.json()


def _defer_post_upload_tasks(trace, user):
    """Defer async tasks after trace creation (same pattern as upload.py)."""
    from traces.tasks import (
        award_trace_badges,
        extract_surfaces,
        generate_tiles,
        generate_user_tiles,
    )

    try:
        extract_surfaces.configure(
            queueing_lock=f"extract_surfaces_{trace.pk}",
        ).defer(trace_id=trace.pk)
    except AlreadyEnqueued:
        pass

    try:
        award_trace_badges.configure(
            queueing_lock=f"award_badges_{trace.pk}",
        ).defer(trace_id=trace.pk)
    except AlreadyEnqueued:
        pass

    if trace.route:
        for zoom in range(settings.TILES_STATIC_MIN_ZOOM, settings.TILES_STATIC_MAX_ZOOM + 1):
            try:
                generate_tiles.configure(
                    queueing_lock=f"generate_tiles_{trace.pk}_{zoom}",
                ).defer(trace_id=trace.pk, zoom=zoom)
            except AlreadyEnqueued:
                pass
        if user.profile.is_premium:
            for zoom in range(settings.TILES_STATIC_MIN_ZOOM, settings.TILES_STATIC_MAX_ZOOM + 1):
                try:
                    generate_user_tiles.configure(
                        queueing_lock=f"generate_user_tiles_{user.pk}_{trace.pk}_{zoom}",
                    ).defer(trace_id=trace.pk, user_id=user.pk, zoom=zoom)
                except AlreadyEnqueued:
                    pass


def _reward_referral_sponsor(user):
    """Reward sponsor on first trace (reuse shared logic)."""
    from traces.trace_processing import _reward_referral_sponsor as _reward
    _reward(user)
