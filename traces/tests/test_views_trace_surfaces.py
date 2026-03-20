from django.test import TestCase
from django.urls import reverse

from traces.models import Trace

from ._helpers import make_user, small_route


class TraceSurfacesTest(TestCase):

    def setUp(self):
        self.user = make_user()
        self.client.login(username="alice", password="pass")
        self.trace = Trace.objects.create(route=small_route(), uploaded_by=self.user)

    def test_returns_200(self):
        resp = self.client.get(reverse("trace_surfaces", args=[self.trace.pk]))
        self.assertEqual(resp.status_code, 200)

    def test_surfaces_geojson_in_context(self):
        resp = self.client.get(reverse("trace_surfaces", args=[self.trace.pk]))
        self.assertIn("surfaces_geojson", resp.context)

    def test_route_geojson_in_context(self):
        resp = self.client.get(reverse("trace_surfaces", args=[self.trace.pk]))
        self.assertIn("route_geojson", resp.context)

    def test_hexagons_geojson_in_context(self):
        resp = self.client.get(reverse("trace_surfaces", args=[self.trace.pk]))
        self.assertIn("hexagons_geojson", resp.context)

    def test_unknown_trace_returns_404(self):
        resp = self.client.get(reverse("trace_surfaces", args=[99999]))
        self.assertEqual(resp.status_code, 404)

    def test_anonymous_redirects_to_login(self):
        self.client.logout()
        resp = self.client.get(reverse("trace_surfaces", args=[self.trace.pk]))
        self.assertRedirects(
            resp,
            f"{reverse('login')}?next={reverse('trace_surfaces', args=[self.trace.pk])}",
            fetch_redirect_response=False,
        )
