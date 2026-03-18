import math
from datetime import timedelta
from pathlib import Path

import gpxpy
from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.contrib.gis.geos import GEOSGeometry, LineString, MultiLineString
from django.db import connection
from django.shortcuts import redirect, render
from django.utils import timezone

from traces.forms import TraceUploadForm
from traces.models import ClosedSurface, Trace, UserProfile

_SQL_DIR = Path(__file__).resolve().parent.parent / "sql"

_INSERT_HEXAGONS_SQL = (_SQL_DIR / "insert_hexagons.sql").read_text()
_DISTANCE_M_SQL = (_SQL_DIR / "distance_m.sql").read_text()
_AWARD_HEXAGON_POINTS_SQL = (_SQL_DIR / "award_hexagon_points.sql").read_text()
_EXTRACT_SURFACES_SQL = (_SQL_DIR / "extract_surfaces.sql").read_text()

# Regular hexagon with area = 1 km²: side = sqrt(2 / (3√3)) ≈ 620.4 m
_HEX_SIDE_M = math.sqrt(2 / (3 * math.sqrt(3))) * 1000  # metres (SRID 3857)


def _create_trace_hexagons(route):
    """Fill the hexagon grid covering the route bbox using ST_HexagonGrid.

    ST_HexagonGrid anchors the grid to the global origin (0, 0) so hexagons
    from different traces align perfectly on the same cell boundaries.
    """
    with connection.cursor() as cursor:
        cursor.execute(_INSERT_HEXAGONS_SQL, [_HEX_SIDE_M, route.envelope.wkt])


MAX_TRACE_LENGTH_KM = 400
_MERGE_THRESHOLD_M = 50


def _distance_m(lon1, lat1, lon2, lat2):
    """Great-circle distance in metres between two (lon, lat) points."""
    with connection.cursor() as cursor:
        cursor.execute(_DISTANCE_M_SQL, [lon1, lat1, lon2, lat2])
        return cursor.fetchone()[0]


def _parse_route(gpx_file):
    gpx = gpxpy.parse(gpx_file)
    segments = []
    first_point_date = None

    for track in gpx.tracks:
        for segment in track.segments:
            if len(segment.points) < 2:
                continue
            coords = [(p.longitude, p.latitude) for p in segment.points]
            if _distance_m(*coords[0], *coords[-1]) <= _MERGE_THRESHOLD_M:
                coords[-1] = coords[0]
            segments.append(LineString(coords))
            if first_point_date is None and segment.points[0].time:
                first_point_date = segment.points[0].time

    if not segments:
        return None, None, 0.0

    length_km = gpx.length_2d() / 1000
    return MultiLineString(segments), first_point_date, length_km


def _extract_surfaces(trace):
    with connection.cursor() as cursor:
        cursor.execute(_EXTRACT_SURFACES_SQL, [trace.pk])
        rows = cursor.fetchall()

    surfaces = []
    for row in rows:
        geom = GEOSGeometry(row[2].tobytes() if hasattr(row[2], "tobytes") else row[2])
        if geom.transform(3857, clone=True).area >= settings.MIN_SURFACE_AREA_M2:
            surfaces.append(ClosedSurface(
                trace=trace,
                owner=trace.uploaded_by,
                segment_index=row[1],
                polygon=geom,
            ))
    if surfaces:
        created = ClosedSurface.objects.bulk_create(surfaces)
        earned_at = trace.first_point_date or trace.uploaded_at
        _award_hexagon_points(created, trace.uploaded_by, earned_at)

    trace.extracted = True
    trace.save(update_fields=["extracted"])


def _award_hexagon_points(surfaces, user, first_point_date):
    for surface in surfaces:
        with connection.cursor() as cursor:
            cursor.execute(_AWARD_HEXAGON_POINTS_SQL, [user.pk, first_point_date, surface.polygon.wkt])


def _upload_quota(user):
    """Return (uploads_today, daily_limit, next_slot) for the rolling 24h window.

    next_slot is the datetime when the earliest upload in the window expires
    (i.e. when a new slot opens), or None if the user is under the limit.
    """
    profile, _ = UserProfile.objects.get_or_create(user=user)
    limit = profile.daily_upload_limit
    since = timezone.now() - timedelta(hours=24)
    recent = (
        Trace.objects.filter(uploaded_by=user, uploaded_at__gte=since)
        .order_by("uploaded_at")
    )
    count = recent.count()
    if count >= limit:
        oldest = recent.first()
        next_slot = oldest.uploaded_at + timedelta(hours=24)
    else:
        next_slot = None
    return count, limit, next_slot


@login_required
def upload_trace(request):
    uploads_today, daily_limit, next_slot = _upload_quota(request.user)
    limit_reached = next_slot is not None

    if request.method == "POST":
        if limit_reached:
            form = TraceUploadForm()
        else:
            form = TraceUploadForm(request.POST, request.FILES)
            if form.is_valid():
                gpx_file = form.cleaned_data["gpx_file"]
                route, first_point_date, length_km = _parse_route(gpx_file)
                if length_km > MAX_TRACE_LENGTH_KM:
                    form.add_error(
                        "gpx_file",
                        f"Trace too long ({length_km:.0f} km). Maximum allowed is {MAX_TRACE_LENGTH_KM} km.",
                    )
                elif first_point_date and Trace.objects.filter(
                    uploaded_by=request.user, first_point_date=first_point_date
                ).exists():
                    form.add_error(
                        "gpx_file",
                        "Cette trace a déjà été uploadée (même date de départ détectée).",
                    )
                else:
                    trace = Trace.objects.create(
                        gpx_file=gpx_file,
                        route=route,
                        first_point_date=first_point_date,
                        uploaded_by=request.user,
                    )
                    if route:
                        _create_trace_hexagons(route)
                        _extract_surfaces(trace)
                    return redirect("trace_detail", pk=trace.pk)
    else:
        form = TraceUploadForm()

    return render(request, "traces/upload.html", {
        "form": form,
        "uploads_today": uploads_today,
        "daily_limit": daily_limit,
        "limit_reached": limit_reached,
        "next_slot": next_slot,
    })
