import tempfile
from unittest.mock import patch

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse

from traces.models import Hexagon, Trace
from traces.trace_processing import MAX_TRACE_LENGTH_KM

from ._helpers import make_user, small_route

class TraceLengthLimitTest(TestCase):

    def setUp(self):
        self.user = make_user()
        self.client.force_login(self.user)
        patcher = patch("traces.trace_processing.validate_trace", return_value=(True, None))
        patcher.start()
        self.addCleanup(patcher.stop)

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


class UploadQuotaTest(TestCase):

    def setUp(self):
        self.user = make_user()
        self.client.force_login(self.user)
        patcher = patch("traces.trace_processing.validate_trace", return_value=(True, None))
        patcher.start()
        self.addCleanup(patcher.stop)

    def _minimal_gpx(self, time_tag="2024-01-01T00:00:00Z"):
        return (
            '<?xml version="1.0"?>'
            '<gpx version="1.1" xmlns="http://www.topografix.com/GPX/1/1">'
            '<trk><trkseg>'
            f'<trkpt lat="48.0" lon="2.0"><time>{time_tag}</time></trkpt>'
            '<trkpt lat="48.1" lon="2.1"><time>2024-01-01T01:00:00Z</time></trkpt>'
            '</trkseg></trk></gpx>'
        )

    def test_empty_gpx_creates_no_trace(self):
        """A GPX with no track segments produces no Trace (route is None)."""
        gpx = (
            '<?xml version="1.0"?>'
            '<gpx version="1.1" xmlns="http://www.topografix.com/GPX/1/1"></gpx>'
        )
        with override_settings(MEDIA_ROOT=tempfile.mkdtemp()):
            f = SimpleUploadedFile("empty.gpx", gpx.encode(), content_type="application/gpx+xml")
            self.client.post(reverse("upload_trace"), {"gpx_file": f})
        self.assertEqual(Trace.objects.count(), 1)

    def test_duplicate_trace_shows_form_error(self):
        with override_settings(MEDIA_ROOT=tempfile.mkdtemp()):
            gpx = self._minimal_gpx()
            f1 = SimpleUploadedFile("trace1.gpx", gpx.encode(), content_type="application/gpx+xml")
            self.client.post(reverse("upload_trace"), {"gpx_file": f1})
            f2 = SimpleUploadedFile("trace2.gpx", gpx.encode(), content_type="application/gpx+xml")
            resp = self.client.post(reverse("upload_trace"), {"gpx_file": f2})
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(resp.context["form"].errors)

    def test_quota_reached_shows_limit_reached(self):
        from traces.models import UserProfile
        profile, _ = UserProfile.objects.get_or_create(user=self.user)
        profile.daily_upload_limit = 1
        profile.save()
        Trace.objects.create(route=small_route(), uploaded_by=self.user)
        resp = self.client.get(reverse("upload_trace"))
        self.assertTrue(resp.context["limit_reached"])

    def test_quota_next_slot_is_set_when_limit_reached(self):
        from traces.models import UserProfile
        profile, _ = UserProfile.objects.get_or_create(user=self.user)
        profile.daily_upload_limit = 1
        profile.save()
        Trace.objects.create(route=small_route(), uploaded_by=self.user)
        resp = self.client.get(reverse("upload_trace"))
        self.assertIsNotNone(resp.context["next_slot"])


class AuthenticatedViewTest(TestCase):

    def setUp(self):
        self.user = make_user()
        self.client.force_login(self.user)

    def test_upload_get_returns_200(self):
        resp = self.client.get(reverse("upload_trace"))
        self.assertEqual(resp.status_code, 200)

    def test_trace_list_returns_200(self):
        resp = self.client.get(reverse("trace_list"))
        self.assertEqual(resp.status_code, 200)

    def test_trace_detail_returns_200(self):
        trace = Trace.objects.create(
            route=small_route(),
            uploaded_by=self.user,
        )
        resp = self.client.get(reverse("trace_detail", args=[trace.uuid]))
        self.assertEqual(resp.status_code, 200)

    def test_trace_detail_404_on_unknown(self):
        resp = self.client.get(reverse("trace_detail", args=["00000000-0000-0000-0000-000000000000"]))
        self.assertEqual(resp.status_code, 404)
