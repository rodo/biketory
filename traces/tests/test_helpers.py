from io import BytesIO

from django.test import TestCase

from traces.trace_processing import _distance_m, _parse_route


class DistanceTest(TestCase):

    def test_same_point_is_zero(self):
        self.assertAlmostEqual(_distance_m(2.0, 48.0, 2.0, 48.0), 0.0)

    def test_known_distance(self):
        # ~111 km per degree latitude
        d = _distance_m(0.0, 0.0, 0.0, 1.0)
        self.assertAlmostEqual(d / 1000, 111.2, delta=0.5)


class ParseRouteMergeTest(TestCase):

    def _make_gpx(self, coords):
        pts = "".join(
            f'<trkpt lat="{lat}" lon="{lon}"><time>2024-01-01T00:00:00Z</time></trkpt>'
            for lon, lat in coords
        )
        return (
            '<?xml version="1.0"?>'
            '<gpx version="1.1" xmlns="http://www.topografix.com/GPX/1/1">'
            f'<trk><trkseg>{pts}</trkseg></trk></gpx>'
        ).encode()

    def test_endpoints_within_threshold_are_merged(self):
        # Shift last point by ~10 m northward (≈ 0.00009 deg)
        gpx = self._make_gpx([(2.0, 48.0), (2.1, 48.05), (2.0, 48.0 + 0.00009)])
        route, _, _ = _parse_route(BytesIO(gpx))
        coords = list(route[0].coords)
        self.assertEqual(coords[0], coords[-1])

    def test_endpoints_beyond_threshold_are_not_merged(self):
        # Shift last point by ~200 m northward (≈ 0.0018 deg)
        gpx = self._make_gpx([(2.0, 48.0), (2.1, 48.05), (2.0, 48.0 + 0.0018)])
        route, _, _ = _parse_route(BytesIO(gpx))
        coords = list(route[0].coords)
        self.assertNotEqual(coords[0], coords[-1])
