import math
from datetime import timedelta

from django.utils import timezone

# --- Thresholds ---
MAX_AVG_SPEED_KMH = 60
MAX_PEAK_SPEED_KMH = 80
MIN_DURATION_SECONDS = 120
MIN_POINTS = 50
FUTURE_TOLERANCE = timedelta(hours=1)
MAX_AGE = timedelta(days=365 * 2)
SAMPLING_STD_FACTOR = 10
MIN_POINTS_FOR_SAMPLING_CHECK = 10
MAX_ACCELERATION_MS2 = 20
IMMOBILE_THRESHOLD_M = 1
IMMOBILE_RATIO = 0.80


def _median(values):
    s = sorted(values)
    n = len(s)
    if n % 2 == 1:
        return s[n // 2]
    return (s[n // 2 - 1] + s[n // 2]) / 2


def _stdev(values):
    n = len(values)
    if n < 2:
        return 0
    mean = sum(values) / n
    return math.sqrt(sum((v - mean) ** 2 for v in values) / (n - 1))


def _haversine_m(lat1, lon1, lat2, lon2):
    """Great-circle distance in metres between two points (lat/lon in degrees)."""
    r = 6_371_000
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (
        math.sin(dlat / 2) ** 2
        + math.cos(math.radians(lat1))
        * math.cos(math.radians(lat2))
        * math.sin(dlon / 2) ** 2
    )
    return r * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def validate_trace(gpx):
    """Validate a parsed GPX object.

    Returns (True, None) if valid, or (False, reason_code) if rejected.
    """
    all_points = []
    for track in gpx.tracks:
        for segment in track.segments:
            all_points.extend(segment.points)

    # 1. Timestamps
    for p in all_points:
        if p.time is None:
            return False, "missing_timestamp"

    # 5. Minimum points (check early — many other checks need enough points)
    if len(all_points) < MIN_POINTS:
        return False, "too_few_points"

    # 6. Date not in the future
    first_time = all_points[0].time
    now = timezone.now()
    if first_time > now + FUTURE_TOLERANCE:
        return False, "future_date"

    # 7. Date not too old
    if first_time < now - MAX_AGE:
        return False, "too_old"

    # 4. Minimum duration
    last_time = all_points[-1].time
    duration = (last_time - first_time).total_seconds()
    if duration < MIN_DURATION_SECONDS:
        return False, "too_short"

    # 2. Average speed
    total_distance_m = 0
    for track in gpx.tracks:
        for segment in track.segments:
            pts = segment.points
            for i in range(1, len(pts)):
                total_distance_m += _haversine_m(
                    pts[i - 1].latitude, pts[i - 1].longitude,
                    pts[i].latitude, pts[i].longitude,
                )
    avg_speed_kmh = (total_distance_m / 1000) / (duration / 3600) if duration > 0 else 0
    if avg_speed_kmh >= MAX_AVG_SPEED_KMH:
        return False, "avg_speed_exceeded"

    # Per-segment checks: peak speed, acceleration, sampling, immobile
    for track in gpx.tracks:
        for segment in track.segments:
            pts = segment.points
            if len(pts) < 2:
                continue

            distances = []
            intervals = []
            speeds = []
            immobile_count = 0

            for i in range(1, len(pts)):
                d = _haversine_m(
                    pts[i - 1].latitude, pts[i - 1].longitude,
                    pts[i].latitude, pts[i].longitude,
                )
                dt = (pts[i].time - pts[i - 1].time).total_seconds()
                distances.append(d)
                intervals.append(dt)

                # 3. Peak speed
                if dt > 0:
                    speed_kmh = (d / 1000) / (dt / 3600)
                    speeds.append(speed_kmh)
                    if speed_kmh > MAX_PEAK_SPEED_KMH:
                        return False, "peak_speed_exceeded"
                else:
                    speeds.append(0)

                # 10. Immobile points
                if d < IMMOBILE_THRESHOLD_M:
                    immobile_count += 1

            # 10. Mostly immobile
            if len(distances) > 0 and immobile_count / len(distances) > IMMOBILE_RATIO:
                return False, "mostly_immobile"

            # 9. Unrealistic acceleration
            for i in range(1, len(speeds)):
                dt = intervals[i]
                if dt > 0:
                    speed_diff_ms = abs(speeds[i] - speeds[i - 1]) / 3.6
                    accel = speed_diff_ms / dt
                    if accel > MAX_ACCELERATION_MS2:
                        return False, "unrealistic_acceleration"

            # 8. Irregular sampling
            if len(intervals) >= MIN_POINTS_FOR_SAMPLING_CHECK:
                positive_intervals = [t for t in intervals if t > 0]
                if positive_intervals:
                    med = _median(positive_intervals)
                    if med > 0:
                        std = _stdev(positive_intervals)
                        if std > SAMPLING_STD_FACTOR * med:
                            return False, "irregular_sampling"

    return True, None
