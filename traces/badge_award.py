"""Automatic badge attribution after a trace upload."""

from pathlib import Path

from django.db import connection

from traces.badges import BADGE_CATALOGUE
from traces.models import ClosedSurface, HexagonScore, Trace, UserBadge

_SQL_DIR = Path(__file__).resolve().parent / "sql"
_STREAK_DAILY_SQL = (_SQL_DIR / "streak_daily.sql").read_text()
_STREAK_WEEKLY_SQL = (_SQL_DIR / "streak_weekly.sql").read_text()
_STREAK_MONTHLY_SQL = (_SQL_DIR / "streak_monthly.sql").read_text()
_VOLUME_WEEKLY_SQL = (_SQL_DIR / "volume_weekly.sql").read_text()
_DISTANCE_MONTHLY_SQL = (_SQL_DIR / "distance_monthly.sql").read_text()
_DISTANCE_TOTAL_SQL = (_SQL_DIR / "distance_total.sql").read_text()

# Build a flat {badge_id: badge_name} lookup from the catalogue.
_BADGE_NAMES = {}
for _cat in BADGE_CATALOGUE:
    for _b in _cat["badges"]:
        _BADGE_NAMES[_b["id"]] = _b["name"]


def _fetch_scalar(sql, params):
    with connection.cursor() as cursor:
        cursor.execute(sql, params)
        return cursor.fetchone()[0]


def _check_territoire(user_id, owned):
    """Hexagon count thresholds."""
    hex_count = HexagonScore.objects.filter(user_id=user_id).count()
    thresholds = [
        (1, "territoire_premier"),
        (100, "territoire_explorateur"),
        (500, "territoire_conquerant"),
        (2000, "territoire_seigneur"),
        (10000, "territoire_legende"),
    ]
    for threshold, badge_id in thresholds:
        if badge_id not in owned and hex_count >= threshold:
            yield badge_id


def _check_activite(user, trace, owned):
    """Activity badges: first trace, 7-day streak, 100 traces, >100km."""
    trace_count = Trace.objects.filter(uploaded_by=user).count()

    if "activite_premier_trace" not in owned and trace_count >= 1:
        yield "activite_premier_trace"

    if "activite_regulier" not in owned:
        daily_streak = _fetch_scalar(_STREAK_DAILY_SQL, [user.pk])
        if daily_streak >= 7:
            yield "activite_regulier"

    if "activite_centurion" not in owned and trace_count >= 100:
        yield "activite_centurion"

    if "activite_randonneur" not in owned and trace.length_km and trace.length_km > 100:
        yield "activite_randonneur"


def _check_surfaces(user_id, owned):
    """Surface count thresholds."""
    surface_count = ClosedSurface.objects.filter(owner_id=user_id).count()

    if "surfaces_geometre" not in owned and surface_count >= 1:
        yield "surfaces_geometre"

    if "surfaces_architecte" not in owned and surface_count >= 50:
        yield "surfaces_architecte"


def _check_special(trace, owned):
    """Night owl badge: trace started between 0h and 5h."""
    if "special_nuit_noire" not in owned and trace.first_point_date:
        hour = trace.first_point_date.hour
        if 0 <= hour < 5:
            yield "special_nuit_noire"


def _check_streaks_daily(user_id, owned):
    """Daily streak badges."""
    thresholds = [
        (3, "quotidien_3j"),
        (7, "quotidien_7j"),
        (14, "quotidien_14j"),
        (30, "quotidien_30j"),
        (100, "quotidien_100j"),
    ]
    needed = [(t, bid) for t, bid in thresholds if bid not in owned]
    if not needed:
        return
    streak = _fetch_scalar(_STREAK_DAILY_SQL, [user_id])
    for threshold, badge_id in needed:
        if streak >= threshold:
            yield badge_id


def _check_streaks_weekly(user_id, owned):
    """Weekly streak badges."""
    thresholds = [
        (2, "hebdo_2sem"),
        (4, "hebdo_4sem"),
        (8, "hebdo_8sem"),
        (26, "hebdo_26sem"),
        (52, "hebdo_52sem"),
    ]
    needed = [(t, bid) for t, bid in thresholds if bid not in owned]
    if not needed:
        return
    streak = _fetch_scalar(_STREAK_WEEKLY_SQL, [user_id])
    for threshold, badge_id in needed:
        if streak >= threshold:
            yield badge_id


def _check_streaks_monthly(user_id, owned):
    """Monthly streak badges."""
    thresholds = [
        (2, "mensuel_2m"),
        (3, "mensuel_3m"),
        (6, "mensuel_6m"),
        (12, "mensuel_12m"),
    ]
    needed = [(t, bid) for t, bid in thresholds if bid not in owned]
    if not needed:
        return
    streak = _fetch_scalar(_STREAK_MONTHLY_SQL, [user_id])
    for threshold, badge_id in needed:
        if streak >= threshold:
            yield badge_id


def _check_volume_weekly(user_id, owned):
    """Volume badges: X traces/week over last 4 weeks."""
    thresholds = [
        (2, "volume_2x"),
        (3, "volume_3x"),
        (5, "volume_5x"),
        (7, "volume_7x"),
    ]
    needed = [(t, bid) for t, bid in thresholds if bid not in owned]
    if not needed:
        return
    min_weekly = _fetch_scalar(_VOLUME_WEEKLY_SQL, [user_id])
    for threshold, badge_id in needed:
        if min_weekly >= threshold:
            yield badge_id


def _check_distance(user_id, owned):
    """Distance badges: monthly and all-time totals."""
    monthly_thresholds = [
        (100, "dist_100"),
        (500, "dist_500"),
        (1000, "dist_1000"),
    ]
    monthly_needed = [(t, bid) for t, bid in monthly_thresholds if bid not in owned]
    if monthly_needed:
        monthly_km = _fetch_scalar(_DISTANCE_MONTHLY_SQL, [user_id])
        for threshold, badge_id in monthly_needed:
            if monthly_km >= threshold:
                yield badge_id

    if "dist_10000" not in owned:
        total_km = _fetch_scalar(_DISTANCE_TOTAL_SQL, [user_id])
        if total_km >= 10000:
            yield "dist_10000"


def award_badges(user, trace):
    """Evaluate all badge criteria and award new ones.

    Returns a list of badge names newly earned.
    """
    owned = set(
        UserBadge.objects.filter(user=user).values_list("badge_id", flat=True)
    )

    new_badge_ids = []

    for badge_id in _check_territoire(user.pk, owned):
        new_badge_ids.append(badge_id)

    for badge_id in _check_activite(user, trace, owned):
        new_badge_ids.append(badge_id)

    for badge_id in _check_surfaces(user.pk, owned):
        new_badge_ids.append(badge_id)

    for badge_id in _check_special(trace, owned):
        new_badge_ids.append(badge_id)

    for badge_id in _check_streaks_daily(user.pk, owned):
        new_badge_ids.append(badge_id)

    for badge_id in _check_streaks_weekly(user.pk, owned):
        new_badge_ids.append(badge_id)

    for badge_id in _check_streaks_monthly(user.pk, owned):
        new_badge_ids.append(badge_id)

    for badge_id in _check_volume_weekly(user.pk, owned):
        new_badge_ids.append(badge_id)

    for badge_id in _check_distance(user.pk, owned):
        new_badge_ids.append(badge_id)

    # Bulk-create new UserBadge rows (ignore duplicates from race conditions)
    if new_badge_ids:
        UserBadge.objects.bulk_create(
            [UserBadge(user=user, badge_id=bid, trace=trace) for bid in new_badge_ids],
            ignore_conflicts=True,
        )

    return [_BADGE_NAMES.get(bid, bid) for bid in new_badge_ids]
