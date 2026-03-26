import datetime
import tempfile

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from traces.models import ApiToken, Subscription

from ._helpers import make_user


def _today():
    return timezone.now().date()


def _make_token(user):
    return ApiToken.objects.create(
        user=user, expires_at=timezone.now() + datetime.timedelta(days=31),
    )


def _minimal_gpx():
    return (
        b'<?xml version="1.0"?>'
        b'<gpx version="1.1" xmlns="http://www.topografix.com/GPX/1/1">'
        b"<trk><trkseg>"
        b'<trkpt lat="48.0" lon="2.0"><time>2024-06-01T00:00:00Z</time></trkpt>'
        b'<trkpt lat="48.1" lon="2.1"><time>2024-06-01T01:00:00Z</time></trkpt>'
        b"</trkseg></trk></gpx>"
    )


# ── API upload requires premium ──


class ApiUploadPremiumCheckTest(TestCase):

    def setUp(self):
        self.user = make_user()
        self.token = _make_token(self.user)
        self.auth = f"Bearer {self.token.token}"

    def test_non_premium_returns_403(self):
        f = SimpleUploadedFile("t.gpx", _minimal_gpx(), content_type="application/gpx+xml")
        resp = self.client.post(
            reverse("api_upload_trace"),
            {"gpx_file": f},
            headers={"authorization": self.auth}
        )
        self.assertEqual(resp.status_code, 403)
        self.assertIn("Premium", resp.json()["error"])

    def test_expired_subscription_returns_403(self):
        Subscription.objects.create(
            user=self.user,
            start_date=_today() - datetime.timedelta(days=60),
            end_date=_today() - datetime.timedelta(days=1),
        )
        f = SimpleUploadedFile("t.gpx", _minimal_gpx(), content_type="application/gpx+xml")
        resp = self.client.post(
            reverse("api_upload_trace"),
            {"gpx_file": f},
            headers={"authorization": self.auth}
        )
        self.assertEqual(resp.status_code, 403)

    @override_settings(MEDIA_ROOT=tempfile.mkdtemp())
    def test_active_premium_returns_201(self):
        Subscription.objects.create(
            user=self.user,
            start_date=_today() - datetime.timedelta(days=1),
            end_date=_today() + datetime.timedelta(days=30),
        )
        f = SimpleUploadedFile("t.gpx", _minimal_gpx(), content_type="application/gpx+xml")
        resp = self.client.post(
            reverse("api_upload_trace"),
            {"gpx_file": f},
            headers={"authorization": self.auth}
        )
        self.assertEqual(resp.status_code, 201)


# ── Profile: token generation requires premium ──


class ProfileTokenPremiumTest(TestCase):

    def setUp(self):
        self.user = make_user()
        self.client.login(username="alice", password="pass")

    def test_generate_token_without_premium_creates_nothing(self):
        self.client.post(reverse("profile"), {"action": "generate_token"})
        self.assertFalse(ApiToken.objects.filter(user=self.user).exists())

    def test_generate_token_with_premium_creates_token(self):
        Subscription.objects.create(
            user=self.user,
            start_date=_today() - datetime.timedelta(days=1),
            end_date=_today() + datetime.timedelta(days=30),
        )
        self.client.post(reverse("profile"), {"action": "generate_token"})
        self.assertTrue(ApiToken.objects.filter(user=self.user).exists())

    def test_profile_context_is_premium_false_without_subscription(self):
        resp = self.client.get(reverse("profile"))
        self.assertFalse(resp.context["is_premium"])
        self.assertIsNone(resp.context["api_token"])

    def test_profile_context_is_premium_true_with_subscription(self):
        Subscription.objects.create(
            user=self.user,
            start_date=_today() - datetime.timedelta(days=1),
            end_date=_today() + datetime.timedelta(days=30),
        )
        resp = self.client.get(reverse("profile"))
        self.assertTrue(resp.context["is_premium"])
