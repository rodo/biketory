import json

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from traces.models import Hexagon, HexagonScore

from ._helpers import make_user, square_polygon


class HexagonDetailTest(TestCase):

    def setUp(self):
        self.user = make_user()
        self.hexagon = Hexagon.objects.create(geom=square_polygon(2.35, 48.85, 0.001))

    def test_returns_200(self):
        resp = self.client.get(reverse("hexagon_detail", args=[self.hexagon.pk]))
        self.assertEqual(resp.status_code, 200)

    def test_returns_json(self):
        resp = self.client.get(reverse("hexagon_detail", args=[self.hexagon.pk]))
        self.assertEqual(resp["Content-Type"], "application/json")

    def test_scores_empty_when_no_scores(self):
        resp = self.client.get(reverse("hexagon_detail", args=[self.hexagon.pk]))
        data = json.loads(resp.content)
        self.assertEqual(data["scores"], [])

    def test_scores_contain_entry(self):
        HexagonScore.objects.create(
            hexagon=self.hexagon, user=self.user, points=5, last_earned_at=timezone.now()
        )
        resp = self.client.get(reverse("hexagon_detail", args=[self.hexagon.pk]))
        data = json.loads(resp.content)
        self.assertEqual(len(data["scores"]), 1)
        self.assertEqual(data["scores"][0]["username"], self.user.username)
        self.assertEqual(data["scores"][0]["points"], 5)

    def test_unknown_hexagon_returns_404(self):
        resp = self.client.get(reverse("hexagon_detail", args=[99999]))
        self.assertEqual(resp.status_code, 404)
