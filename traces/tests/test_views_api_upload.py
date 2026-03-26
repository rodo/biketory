import tempfile
from datetime import timedelta

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from traces.models import ApiToken, Subscription, Trace

from ._helpers import make_user


def _minimal_gpx():
    return (
        b'<?xml version="1.0"?>'
        b'<gpx version="1.1" xmlns="http://www.topografix.com/GPX/1/1">'
        b"<trk><trkseg>"
        b'<trkpt lat="48.0" lon="2.0"><time>2024-06-01T00:00:00Z</time></trkpt>'
        b'<trkpt lat="48.1" lon="2.1"><time>2024-06-01T01:00:00Z</time></trkpt>'
        b"</trkseg></trk></gpx>"
    )


class ApiUploadAuthTest(TestCase):
    def test_no_auth_returns_401(self):
        resp = self.client.post(reverse("api_upload_trace"))
        self.assertEqual(resp.status_code, 401)

    def test_invalid_token_returns_401(self):
        resp = self.client.post(
            reverse("api_upload_trace"),
            headers={"authorization": "Bearer invalidtoken"}
        )
        self.assertEqual(resp.status_code, 401)

    def test_expired_token_returns_401(self):
        user = make_user()
        token = ApiToken.objects.create(
            user=user,
            expires_at=timezone.now() - timedelta(days=1),
        )
        resp = self.client.post(
            reverse("api_upload_trace"),
            headers={"authorization": f"Bearer {token.token}"}
        )
        self.assertEqual(resp.status_code, 401)


class ApiUploadTest(TestCase):
    def setUp(self):
        self.user = make_user()
        self.token = ApiToken.objects.create(
            user=self.user,
            expires_at=timezone.now() + timedelta(days=31),
        )
        self.auth = f"Bearer {self.token.token}"
        today = timezone.now().date()
        Subscription.objects.create(
            user=self.user,
            start_date=today - timedelta(days=1),
            end_date=today + timedelta(days=30),
        )

    def test_missing_file_returns_400(self):
        resp = self.client.post(
            reverse("api_upload_trace"),
            headers={"authorization": self.auth}
        )
        self.assertEqual(resp.status_code, 400)

    @override_settings(MEDIA_ROOT=tempfile.mkdtemp())
    def test_valid_upload_returns_201(self):
        f = SimpleUploadedFile("trace.gpx", _minimal_gpx(), content_type="application/gpx+xml")
        resp = self.client.post(
            reverse("api_upload_trace"),
            {"gpx_file": f},
            headers={"authorization": self.auth}
        )
        self.assertEqual(resp.status_code, 201)
        self.assertEqual(Trace.objects.count(), 1)
        data = resp.json()
        self.assertIn("id", data)

    @override_settings(MEDIA_ROOT=tempfile.mkdtemp())
    def test_quota_exceeded_returns_429(self):
        from traces.models import UserProfile

        profile, _ = UserProfile.objects.get_or_create(user=self.user)
        profile.daily_upload_limit = 1
        profile.save()
        # First upload
        f1 = SimpleUploadedFile("t1.gpx", _minimal_gpx(), content_type="application/gpx+xml")
        self.client.post(
            reverse("api_upload_trace"),
            {"gpx_file": f1},
            headers={"authorization": self.auth}
        )
        # Second upload should be rejected
        gpx2 = (
            b'<?xml version="1.0"?>'
            b'<gpx version="1.1" xmlns="http://www.topografix.com/GPX/1/1">'
            b"<trk><trkseg>"
            b'<trkpt lat="48.0" lon="2.0"><time>2024-07-01T00:00:00Z</time></trkpt>'
            b'<trkpt lat="48.1" lon="2.1"><time>2024-07-01T01:00:00Z</time></trkpt>'
            b"</trkseg></trk></gpx>"
        )
        f2 = SimpleUploadedFile("t2.gpx", gpx2, content_type="application/gpx+xml")
        resp = self.client.post(
            reverse("api_upload_trace"),
            {"gpx_file": f2},
            headers={"authorization": self.auth}
        )
        self.assertEqual(resp.status_code, 429)
