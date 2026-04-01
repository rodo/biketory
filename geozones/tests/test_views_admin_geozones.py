from django.test import TestCase
from django.urls import reverse

from ._helpers import make_superuser, make_user, make_zone


class AdminGeozonesAuthTest(TestCase):

    def test_anonymous_redirects(self):
        resp = self.client.get(reverse("admin_dashboard_geozones"))
        self.assertEqual(resp.status_code, 302)

    def test_non_superuser_redirects(self):
        self.client.force_login(make_user())
        resp = self.client.get(reverse("admin_dashboard_geozones"))
        self.assertEqual(resp.status_code, 302)

    def test_superuser_returns_200(self):
        self.client.force_login(make_superuser())
        resp = self.client.get(reverse("admin_dashboard_geozones"))
        self.assertEqual(resp.status_code, 200)


class AdminGeozonesListTest(TestCase):

    @classmethod
    def setUpTestData(cls):
        cls.admin = make_superuser()
        cls.zone = make_zone(code="FR", name="France", admin_level=2)

    def setUp(self):
        self.client.force_login(self.admin)

    def test_zones_in_context(self):
        resp = self.client.get(reverse("admin_dashboard_geozones"))
        self.assertIn(self.zone, resp.context["zones"])


class AdminGeozoneDetailTest(TestCase):

    @classmethod
    def setUpTestData(cls):
        cls.admin = make_superuser()
        cls.zone = make_zone(code="FR", name="France", admin_level=2)

    def setUp(self):
        self.client.force_login(self.admin)

    def test_returns_200(self):
        resp = self.client.get(
            reverse("admin_dashboard_geozone_detail", args=[self.zone.pk])
        )
        self.assertEqual(resp.status_code, 200)

    def test_zone_in_context(self):
        resp = self.client.get(
            reverse("admin_dashboard_geozone_detail", args=[self.zone.pk])
        )
        self.assertEqual(resp.context["zone"], self.zone)

    def test_geojson_in_context(self):
        resp = self.client.get(
            reverse("admin_dashboard_geozone_detail", args=[self.zone.pk])
        )
        self.assertIn("zone_geojson", resp.context)

    def test_prev_next_siblings(self):
        z_a = make_zone(code="AT", name="Austria", admin_level=2)
        z_b = make_zone(code="DE", name="Germany", admin_level=2)
        # France is between Austria and Germany alphabetically
        resp = self.client.get(
            reverse("admin_dashboard_geozone_detail", args=[self.zone.pk])
        )
        self.assertEqual(resp.context["prev_zone"], z_a)
        self.assertEqual(resp.context["next_zone"], z_b)

    def test_children_in_context(self):
        child = make_zone(code="IDF", name="Ile-de-France", admin_level=4,
                          parent=self.zone)
        resp = self.client.get(
            reverse("admin_dashboard_geozone_detail", args=[self.zone.pk])
        )
        self.assertIn(child, resp.context["children"])


class AdminGeozoneToggleTest(TestCase):

    @classmethod
    def setUpTestData(cls):
        cls.admin = make_superuser()

    def setUp(self):
        self.client.force_login(self.admin)
        self.zone = make_zone(code="FR", active=False)

    def test_get_returns_405(self):
        resp = self.client.get(
            reverse("admin_dashboard_geozone_toggle", args=[self.zone.pk])
        )
        self.assertEqual(resp.status_code, 405)

    def test_post_toggles_active(self):
        self.assertFalse(self.zone.active)
        resp = self.client.post(
            reverse("admin_dashboard_geozone_toggle", args=[self.zone.pk])
        )
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertTrue(data["active"])
        self.zone.refresh_from_db()
        self.assertTrue(self.zone.active)

    def test_toggle_twice(self):
        url = reverse("admin_dashboard_geozone_toggle", args=[self.zone.pk])
        self.client.post(url)
        self.client.post(url)
        self.zone.refresh_from_db()
        self.assertFalse(self.zone.active)

    def test_non_superuser_cannot_toggle(self):
        self.client.force_login(make_user(username="bob"))
        resp = self.client.post(
            reverse("admin_dashboard_geozone_toggle", args=[self.zone.pk])
        )
        self.assertEqual(resp.status_code, 302)
