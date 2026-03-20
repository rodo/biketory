import tempfile

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse

from django.utils import timezone

from traces.models import Hexagon, HexagonScore, Trace
from traces.views.upload import MAX_TRACE_LENGTH_KM

from ._helpers import make_user, small_route, square_polygon


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
        with override_settings(MEDIA_ROOT=tempfile.mkdtemp()):
            gpx = self._gpx_with_length(10)
            f = SimpleUploadedFile("short.gpx", gpx.encode(), content_type="application/gpx+xml")
            self.client.post(reverse("upload_trace"), {"gpx_file": f})
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
        HexagonScore.objects.create(hexagon=h, user=self.user, points=3, last_earned_at=timezone.now())
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
