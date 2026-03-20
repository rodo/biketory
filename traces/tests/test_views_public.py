from django.test import TestCase
from django.urls import reverse

from django.contrib.auth.models import User

from ._helpers import make_user


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
