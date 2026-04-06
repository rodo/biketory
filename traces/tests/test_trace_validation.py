from datetime import datetime, timedelta, timezone as dt_tz

import gpxpy
import gpxpy.gpx

from django.test import TestCase
from django.utils import timezone

from traces.trace_validation import validate_trace


def _make_gpx(points, time_start=None, time_interval=None):
    """Build a GPX object with a single track and segment.

    points: list of (lat, lon) tuples
    time_start: datetime for the first point (default: 1 hour ago)
    time_interval: timedelta between points (default: 3 seconds)
    """
    if time_start is None:
        time_start = timezone.now() - timedelta(hours=1)
    if time_interval is None:
        time_interval = timedelta(seconds=3)

    gpx = gpxpy.gpx.GPX()
    track = gpxpy.gpx.GPXTrack()
    gpx.tracks.append(track)
    segment = gpxpy.gpx.GPXTrackSegment()
    track.segments.append(segment)

    for i, (lat, lon) in enumerate(points):
        p = gpxpy.gpx.GPXTrackPoint(
            latitude=lat,
            longitude=lon,
            time=time_start + time_interval * i,
        )
        segment.points.append(p)

    return gpx


def _gentle_ride(n=100):
    """Generate n points of a slow ride heading roughly north from Paris.

    ~15 km/h, 3 seconds apart, ~12.5 m between points.
    """
    points = []
    lat, lon = 48.8, 2.3
    for i in range(n):
        points.append((lat + i * 0.000112, lon + i * 0.000005))
    return points


class ValidTraceTest(TestCase):

    def test_valid_trace(self):
        gpx = _make_gpx(_gentle_ride(100))
        valid, reason = validate_trace(gpx)
        self.assertTrue(valid)
        self.assertIsNone(reason)


class MissingTimestampTest(TestCase):

    def test_missing_timestamp(self):
        gpx = _make_gpx(_gentle_ride(100))
        gpx.tracks[0].segments[0].points[10].time = None
        valid, reason = validate_trace(gpx)
        self.assertFalse(valid)
        self.assertEqual(reason, "missing_timestamp")


class TooFewPointsTest(TestCase):

    def test_too_few_points(self):
        gpx = _make_gpx(_gentle_ride(30))
        valid, reason = validate_trace(gpx)
        self.assertFalse(valid)
        self.assertEqual(reason, "too_few_points")

    def test_exactly_50_points_passes(self):
        gpx = _make_gpx(_gentle_ride(50))
        valid, _ = validate_trace(gpx)
        self.assertTrue(valid)


class FutureDateTest(TestCase):

    def test_future_date(self):
        future = timezone.now() + timedelta(hours=5)
        gpx = _make_gpx(_gentle_ride(100), time_start=future)
        valid, reason = validate_trace(gpx)
        self.assertFalse(valid)
        self.assertEqual(reason, "future_date")

    def test_slight_future_ok(self):
        """Within 1h tolerance should pass."""
        slight_future = timezone.now() + timedelta(minutes=30)
        gpx = _make_gpx(_gentle_ride(100), time_start=slight_future)
        valid, _ = validate_trace(gpx)
        self.assertTrue(valid)


class TooOldTest(TestCase):

    def test_too_old(self):
        old = timezone.now() - timedelta(days=800)
        gpx = _make_gpx(_gentle_ride(100), time_start=old)
        valid, reason = validate_trace(gpx)
        self.assertFalse(valid)
        self.assertEqual(reason, "too_old")


class TooShortTest(TestCase):

    def test_too_short_duration(self):
        """100 points but only 1 second apart = 99 seconds total < 120."""
        gpx = _make_gpx(_gentle_ride(100), time_interval=timedelta(seconds=1))
        valid, reason = validate_trace(gpx)
        self.assertFalse(valid)
        self.assertEqual(reason, "too_short")


class AvgSpeedExceededTest(TestCase):

    def test_avg_speed_exceeded(self):
        """Points ~200m apart, 3s interval = ~240 km/h average."""
        points = [(48.8 + i * 0.0018, 2.3) for i in range(100)]
        gpx = _make_gpx(points)
        valid, reason = validate_trace(gpx)
        self.assertFalse(valid)
        self.assertEqual(reason, "avg_speed_exceeded")


class PeakSpeedExceededTest(TestCase):

    def test_peak_speed_spike(self):
        """Normal ride with one spike that exceeds 80 km/h between 2 points."""
        points = _gentle_ride(100)
        points = list(points)
        # ~100m jump in 3s = ~120 km/h (> 80 km/h peak, but barely affects avg)
        lat, lon = points[49]
        points[50] = (lat + 0.0009, lon)
        # Put point 51 back near 50 to not propagate the jump
        points[51] = (points[50][0] + 0.000112, points[50][1] + 0.000005)
        gpx = _make_gpx(points)
        valid, reason = validate_trace(gpx)
        self.assertFalse(valid)
        self.assertEqual(reason, "peak_speed_exceeded")


class MostlyImmobileTest(TestCase):

    def test_mostly_immobile(self):
        """All points at the same location."""
        points = [(48.8, 2.3)] * 100
        gpx = _make_gpx(points)
        valid, reason = validate_trace(gpx)
        self.assertFalse(valid)
        self.assertEqual(reason, "mostly_immobile")


class UnrealisticAccelerationTest(TestCase):

    def test_unrealistic_acceleration(self):
        """Gentle ride then sudden 500m jump in 1 second then back to normal."""
        points = _gentle_ride(100)
        points = list(points)
        gpx = _make_gpx(points, time_interval=timedelta(seconds=3))
        seg = gpx.tracks[0].segments[0]
        # Make point 50 very far, with only 1s gap
        seg.points[50].latitude += 0.01  # ~1.1 km jump
        seg.points[50].time = seg.points[49].time + timedelta(seconds=1)
        # Point 51 back to normal, 1s later
        seg.points[51].time = seg.points[50].time + timedelta(seconds=1)
        valid, reason = validate_trace(gpx)
        self.assertFalse(valid)
        self.assertIn(reason, ("peak_speed_exceeded", "unrealistic_acceleration"))


class IrregularSamplingTest(TestCase):

    def test_irregular_sampling(self):
        """Points with wildly varying time intervals (editor-like pattern)."""
        points = _gentle_ride(100)
        start = timezone.now() - timedelta(hours=1)
        gpx = _make_gpx(points, time_start=start, time_interval=timedelta(seconds=3))
        seg = gpx.tracks[0].segments[0]
        # Make every 5th point have a 10-minute gap, rest 1 second
        t = start
        for i, pt in enumerate(seg.points):
            pt.time = t
            if i % 5 == 0:
                t += timedelta(minutes=10)
            else:
                t += timedelta(seconds=1)
        valid, reason = validate_trace(gpx)
        self.assertFalse(valid)
        self.assertEqual(reason, "irregular_sampling")
