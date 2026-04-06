import logging
import math
from collections import defaultdict
from datetime import timedelta
from pathlib import Path

import gpxpy
from django.conf import settings
from django.contrib.gis.geos import GEOSGeometry, LineString, MultiLineString
from django.db import connection
from django.utils import timezone
from django.utils.translation import gettext as _

from traces.models import ClosedSurface, Trace, UserProfile
from traces.trace_validation import validate_trace

logger = logging.getLogger(__name__)

_SQL_DIR = Path(__file__).resolve().parent / "sql"

_INSERT_HEXAGONS_SQL = (_SQL_DIR / "insert_hexagons.sql").read_text()
_DISTANCE_M_SQL = (_SQL_DIR / "distance_m.sql").read_text()
_AWARD_HEXAGON_POINTS_SQL = (_SQL_DIR / "award_hexagon_points.sql").read_text()
_UPDATE_HEXAGON_OWNERS_SQL = (_SQL_DIR / "update_hexagon_owners.sql").read_text()
_EXTRACT_SURFACES_SQL = (_SQL_DIR / "extract_surfaces.sql").read_text()
_DELETE_ISLAND_SURFACES_SQL = (_SQL_DIR / "delete_island_surfaces.sql").read_text()

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


def _merge_adjacent_polygons(polygons):
    """Merge touching polygons into their union (one polygon per connected component).

    ST_Polygonize produces individual face polygons for each enclosed region of a
    self-intersecting trace. Adjacent faces share edges and must be merged so that
    a single loop results in a single surface, regardless of how many times the
    trace crosses itself.
    """
    if not polygons:
        return []

    n = len(polygons)
    parent = list(range(n))

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    for i in range(n):
        for j in range(i + 1, n):
            shared = polygons[i].boundary.intersection(polygons[j].boundary)
            if not shared.empty and shared.length > 0:
                parent[find(i)] = find(j)

    groups = defaultdict(list)
    for i in range(n):
        groups[find(i)].append(polygons[i])

    result = []
    for group in groups.values():
        merged = group[0]
        for g in group[1:]:
            merged = merged.union(g)
        if merged.geom_type == "MultiPolygon":
            merged = max(merged, key=lambda p: p.area)
        result.append(merged)
    return result


def _extract_surfaces(trace):
    with connection.cursor() as cursor:
        cursor.execute(_EXTRACT_SURFACES_SQL, [trace.pk])
        rows = cursor.fetchall()

    faces_by_segment = defaultdict(list)
    for row in rows:
        geom = GEOSGeometry(row[2].tobytes() if hasattr(row[2], "tobytes") else row[2])
        faces_by_segment[row[1]].append(geom)

    surfaces = []
    for seg_idx, faces in faces_by_segment.items():
        for geom in _merge_adjacent_polygons(faces):
            if geom.transform(3857, clone=True).area >= settings.MIN_SURFACE_AREA_M2:
                surfaces.append(ClosedSurface(
                    trace=trace,
                    owner=trace.uploaded_by,
                    segment_index=seg_idx,
                    polygon=geom,
                ))

    if surfaces:
        ClosedSurface.objects.bulk_create(surfaces)
        with connection.cursor() as cursor:
            cursor.execute(_DELETE_ISLAND_SURFACES_SQL, [trace.pk, trace.pk])
        surviving = list(ClosedSurface.objects.filter(trace=trace))
        earned_at = trace.first_point_date or trace.uploaded_at
        _award_hexagon_points(surviving, trace.uploaded_by, earned_at)
        _update_hexagon_owners(surviving)

    trace.extracted = True
    trace.save(update_fields=["extracted"])


def _award_hexagon_points(surfaces, user, first_point_date):
    for surface in surfaces:
        with connection.cursor() as cursor:
            cursor.execute(_AWARD_HEXAGON_POINTS_SQL, [user.pk, first_point_date, surface.polygon.wkt])


def _update_hexagon_owners(surfaces):
    for surface in surfaces:
        with connection.cursor() as cursor:
            cursor.execute(_UPDATE_HEXAGON_OWNERS_SQL, [surface.polygon.wkt])


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


def create_trace(gpx_file, user):
    """Shared upload pipeline: parse, validate, create Trace, enqueue jobs.

    Returns (trace, error_message). On success trace is set and error is None.
    On failure trace is None and error is a translatable string.
    """
    from django.contrib.gis.geos import Polygon
    from procrastinate.exceptions import AlreadyEnqueued

    gpx = gpxpy.parse(gpx_file)

    if settings.TRACE_VALIDATION_ENABLED:
        valid, reason_code = validate_trace(gpx)
        if not valid:
            logger.warning("Trace rejected for user %s: %s", user, reason_code)
            return None, _("Unable to analyze this trace.")

    gpx_file.seek(0)
    route, first_point_date, length_km = _parse_route(gpx_file)

    if length_km > MAX_TRACE_LENGTH_KM:
        return None, _(
            "Trace too long (%(length).0f km)."
            " Maximum allowed is %(max)d km."
        ) % {"length": length_km, "max": MAX_TRACE_LENGTH_KM}

    if first_point_date and Trace.objects.filter(
        uploaded_by=user, first_point_date=first_point_date
    ).exists():
        return None, _("This trace has already been uploaded (same start date detected).")

    trace = Trace.objects.create(
        gpx_file=gpx_file,
        route=route,
        length_km=length_km,
        first_point_date=first_point_date,
        uploaded_by=user,
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
    if route:
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

    _reward_referral_sponsor(user)

    return trace, None


def _reward_referral_sponsor(user):
    if Trace.objects.filter(uploaded_by=user).count() != 1:
        return

    from referrals.models import Referral

    referral = Referral.objects.filter(
        referee=user, status=Referral.ACCEPTED, rewarded=False
    ).first()
    if not referral:
        return

    import datetime

    from dateutil.relativedelta import relativedelta

    from traces.models import Subscription

    today = datetime.date.today()
    latest_sub = Subscription.objects.filter(user=referral.sponsor).order_by("-end_date").first()
    if latest_sub:
        start = max(latest_sub.end_date + datetime.timedelta(days=1), today)
    else:
        start = today
    Subscription.objects.create(
        user=referral.sponsor,
        start_date=start,
        end_date=start + relativedelta(months=1),
    )

    referral.rewarded = True
    referral.save(update_fields=["rewarded"])
