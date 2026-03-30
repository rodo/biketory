from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from ._helpers import make_user


class AuthRedirectTest(TestCase):
    """Protected views redirect anonymous users to login."""

    protected = [
        "upload_trace",
        "trace_list",
    ]

    def test_redirects_anonymous(self):
        for name in self.protected:
            with self.subTest(view=name):
                resp = self.client.get(reverse(name))
                self.assertRedirects(
                    resp,
                    f"{reverse('account_login')}?next={reverse(name)}",
                    fetch_redirect_response=False,
                )


class LandingViewTest(TestCase):

    def test_anonymous_returns_200(self):
        resp = self.client.get(reverse("landing"))
        self.assertEqual(resp.status_code, 200)

    def test_hexagons_api_returns_json(self):
        resp = self.client.get(reverse("landing_hexagons"))
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIn("geojson", data)
        self.assertIsNone(data["current_user"])

    def test_hexagons_api_current_user_when_authenticated(self):
        user = make_user()
        self.client.force_login(user)
        resp = self.client.get(reverse("landing_hexagons"))
        data = resp.json()
        self.assertEqual(data["current_user"], user.username)

    def test_hexagons_api_with_bbox(self):
        resp = self.client.get(
            reverse("landing_hexagons"), {"bbox": "-180,-90,180,90"}
        )
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIn("geojson", data)


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
            "email": "newuser@example.com",
            "password1": "Str0ngPass!",
            "password2": "Str0ngPass!",
        })
        self.assertTrue(User.objects.filter(email="newuser@example.com").exists())
