from django.contrib.auth.models import User
from django.contrib.gis.geos import LineString, MultiLineString, Polygon
from django.test import TestCase
from django.urls import reverse

from traces.models import ClosedSurface, Hexagon, HexagonScore, Trace
from traces.views.upload import (
    _HEX_SIDE_M,
    MAX_TRACE_LENGTH_KM,
    _award_hexagon_points,
    _create_trace_hexagons,
    _distance_m,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_user(username="alice", password="pass"):
    return User.objects.create_user(username=username, password=password)


def small_route():
    """A short two-point route near Paris (lon 2.3-2.4, lat 48.8-48.9)."""
    return MultiLineString(LineString([(2.30, 48.80), (2.40, 48.90)]))


def square_polygon(cx, cy, half):
    """Axis-aligned square polygon centred at (cx, cy)."""
    return Polygon([
        (cx - half, cy - half),
        (cx + half, cy - half),
        (cx + half, cy + half),
        (cx - half, cy + half),
        (cx - half, cy - half),
    ])


# ---------------------------------------------------------------------------
# _hex_polygon
# ---------------------------------------------------------------------------

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
        from io import BytesIO

        from traces.views.upload import _parse_route
        # Shift last point by ~10 m northward (≈ 0.00009 deg)
        gpx = self._make_gpx([(2.0, 48.0), (2.1, 48.05), (2.0, 48.0 + 0.00009)])
        route, _, _ = _parse_route(BytesIO(gpx))
        coords = list(route.geoms[0].coords)
        self.assertEqual(coords[0], coords[-1])

    def test_endpoints_beyond_threshold_are_not_merged(self):
        from io import BytesIO

        from traces.views.upload import _parse_route
        # Shift last point by ~200 m northward (≈ 0.0018 deg)
        gpx = self._make_gpx([(2.0, 48.0), (2.1, 48.05), (2.0, 48.0 + 0.0018)])
        route, _, _ = _parse_route(BytesIO(gpx))
        coords = list(route.geoms[0].coords)
        self.assertNotEqual(coords[0], coords[-1])


# ---------------------------------------------------------------------------
# _create_trace_hexagons
# ---------------------------------------------------------------------------

class CreateTraceHexagonsTest(TestCase):

    def setUp(self):
        self.route = small_route()

    def test_creates_hexagons(self):
        _create_trace_hexagons(self.route)
        self.assertGreater(Hexagon.objects.count(), 0)

    def test_hexagons_cover_bbox(self):
        _create_trace_hexagons(self.route)
        xmin, ymin, xmax, ymax = self.route.extent
        for h in Hexagon.objects.all():
            cx, cy = h.geom.centroid.x, h.geom.centroid.y
            # centroid should be near the bbox (with one hex margin)
            delta_deg = 2 * _HEX_SIDE_M / 111_320
            self.assertAlmostEqual(cx, max(xmin, min(xmax, cx)), delta=delta_deg)
            self.assertAlmostEqual(cy, max(ymin, min(ymax, cy)), delta=delta_deg)

    def test_no_duplicates_on_second_call(self):
        _create_trace_hexagons(self.route)
        count_first = Hexagon.objects.count()
        _create_trace_hexagons(self.route)
        self.assertEqual(Hexagon.objects.count(), count_first)

    def test_hexagons_have_created_at(self):
        _create_trace_hexagons(self.route)
        h = Hexagon.objects.first()
        self.assertIsNotNone(h.created_at)


# ---------------------------------------------------------------------------
# _claim_hexagons
# ---------------------------------------------------------------------------

class AwardHexagonPointsTest(TestCase):

    def setUp(self):
        self.user = make_user()
        self.trace = Trace.objects.create(
            route=small_route(),
            uploaded_by=self.user,
        )
        self.surface = ClosedSurface.objects.create(
            trace=self.trace,
            owner=self.user,
            polygon=square_polygon(2.35, 48.85, 0.01),
        )
        self.hex_inside = Hexagon.objects.create(geom=square_polygon(2.35, 48.85, 0.001))
        self.hex_outside = Hexagon.objects.create(geom=square_polygon(10.0, 10.0, 0.001))

    def test_creates_score_for_hexagon_inside_surface(self):
        _award_hexagon_points([self.surface], self.user)
        score = HexagonScore.objects.get(hexagon=self.hex_inside, user=self.user)
        self.assertEqual(score.points, 1)

    def test_does_not_score_hexagon_outside_surface(self):
        _award_hexagon_points([self.surface], self.user)
        self.assertFalse(HexagonScore.objects.filter(hexagon=self.hex_outside).exists())

    def test_increments_points_on_second_upload(self):
        _award_hexagon_points([self.surface], self.user)
        _award_hexagon_points([self.surface], self.user)
        score = HexagonScore.objects.get(hexagon=self.hex_inside, user=self.user)
        self.assertEqual(score.points, 2)

    def test_different_users_score_independently(self):
        other_user = make_user("bob")
        _award_hexagon_points([self.surface], self.user)
        _award_hexagon_points([self.surface], other_user)
        self.assertEqual(HexagonScore.objects.get(hexagon=self.hex_inside, user=self.user).points, 1)
        self.assertEqual(HexagonScore.objects.get(hexagon=self.hex_inside, user=other_user).points, 1)


# ---------------------------------------------------------------------------
# Views — authentication
# ---------------------------------------------------------------------------

class AuthRedirectTest(TestCase):
    """Protected views redirect anonymous users to login."""

    protected = [
        "upload_trace",
        "trace_list",
        "surface_list",
        "hexagon_stats",
    ]

    def test_redirects_anonymous(self):
        for name in self.protected:
            with self.subTest(view=name):
                resp = self.client.get(reverse(name))
                self.assertRedirects(
                    resp,
                    f"{reverse('login')}?next={reverse(name)}",
                    fetch_redirect_response=False,
                )


# ---------------------------------------------------------------------------
# Views — public pages
# ---------------------------------------------------------------------------

class LandingViewTest(TestCase):

    def test_anonymous_returns_200(self):
        resp = self.client.get(reverse("landing"))
        self.assertEqual(resp.status_code, 200)

    def test_geojson_in_context(self):
        resp = self.client.get(reverse("landing"))
        self.assertIn("geojson", resp.context)

    def test_current_user_none_when_anonymous(self):
        resp = self.client.get(reverse("landing"))
        self.assertIsNone(resp.context["current_user"])

    def test_current_user_set_when_authenticated(self):
        make_user()
        self.client.login(username="alice", password="pass")
        resp = self.client.get(reverse("landing"))
        self.assertEqual(resp.context["current_user"], "alice")


class LegalViewTest(TestCase):

    def test_anonymous_returns_200(self):
        resp = self.client.get(reverse("legal"))
        self.assertEqual(resp.status_code, 200)


class RegisterViewTest(TestCase):

    def test_get_returns_200(self):
        resp = self.client.get(reverse("register"))
        self.assertEqual(resp.status_code, 200)

    def test_post_creates_user(self):
        self.client.post(reverse("register"), {
            "username": "newuser",
            "password1": "Str0ngPass!",
            "password2": "Str0ngPass!",
        })
        self.assertTrue(User.objects.filter(username="newuser").exists())


# ---------------------------------------------------------------------------
# Views — authenticated pages
# ---------------------------------------------------------------------------

class TraceLengthLimitTest(TestCase):

    def setUp(self):
        self.user = make_user()
        self.client.login(username="alice", password="pass")

    def _gpx_with_length(self, length_km):
        """Build a minimal GPX string spanning approximately length_km."""
        # 1 degree latitude ≈ 111.32 km
        delta = length_km / 111.32
        return (
            '<?xml version="1.0"?>'
            '<gpx version="1.1" xmlns="http://www.topografix.com/GPX/1/1">'
            '<trk><trkseg>'
            f'<trkpt lat="48.0" lon="2.0"><time>2024-01-01T00:00:00Z</time></trkpt>'
            f'<trkpt lat="{48.0 + delta:.6f}" lon="2.0"><time>2024-01-01T01:00:00Z</time></trkpt>'
            '</trkseg></trk></gpx>'
        )

    def test_short_trace_is_accepted(self):
        gpx = self._gpx_with_length(10)
        self.client.post(
            reverse("upload_trace"),
            {"gpx_file": ("short.gpx", gpx.encode(), "application/gpx+xml")},
        )
        self.assertEqual(Trace.objects.count(), 1)

    def test_long_trace_is_rejected(self):
        gpx = self._gpx_with_length(MAX_TRACE_LENGTH_KM + 50)
        self.client.post(
            reverse("upload_trace"),
            {"gpx_file": ("long.gpx", gpx.encode(), "application/gpx+xml")},
        )
        self.assertEqual(Trace.objects.count(), 0)
        self.assertEqual(Hexagon.objects.count(), 0)

    def test_long_trace_shows_error(self):
        gpx = self._gpx_with_length(MAX_TRACE_LENGTH_KM + 50)
        resp = self.client.post(
            reverse("upload_trace"),
            {"gpx_file": ("long.gpx", gpx.encode(), "application/gpx+xml")},
        )
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(resp.context["form"].errors)


class AuthenticatedViewTest(TestCase):

    def setUp(self):
        self.user = make_user()
        self.client.login(username="alice", password="pass")

    def test_upload_get_returns_200(self):
        resp = self.client.get(reverse("upload_trace"))
        self.assertEqual(resp.status_code, 200)

    def test_trace_list_returns_200(self):
        resp = self.client.get(reverse("trace_list"))
        self.assertEqual(resp.status_code, 200)

    def test_surface_list_returns_200(self):
        resp = self.client.get(reverse("surface_list"))
        self.assertEqual(resp.status_code, 200)

    def test_hexagon_stats_returns_200(self):
        resp = self.client.get(reverse("hexagon_stats"))
        self.assertEqual(resp.status_code, 200)

    def test_hexagon_stats_total_count(self):
        Hexagon.objects.create(geom=square_polygon(2.35, 48.85, 0.001))
        resp = self.client.get(reverse("hexagon_stats"))
        self.assertEqual(resp.context["total_hexagons"], 1)

    def test_hexagon_stats_per_user_points(self):
        h = Hexagon.objects.create(geom=square_polygon(2.35, 48.85, 0.001))
        HexagonScore.objects.create(hexagon=h, user=self.user, points=3)
        resp = self.client.get(reverse("hexagon_stats"))
        row = resp.context["per_user"][0]
        self.assertEqual(row["user__username"], "alice")
        self.assertEqual(row["total_points"], 3)

    def test_trace_detail_returns_200(self):
        trace = Trace.objects.create(
            route=small_route(),
            uploaded_by=self.user,
        )
        resp = self.client.get(reverse("trace_detail", args=[trace.pk]))
        self.assertEqual(resp.status_code, 200)

    def test_trace_detail_404_on_unknown(self):
        resp = self.client.get(reverse("trace_detail", args=[99999]))
        self.assertEqual(resp.status_code, 404)
