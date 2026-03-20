from django.test import TestCase
from django.utils import timezone

from traces.models import ClosedSurface, Hexagon, HexagonScore, Trace
from traces.views.upload import _HEX_SIDE_M, _award_hexagon_points, _create_trace_hexagons

from ._helpers import make_user, small_route, square_polygon


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
        _award_hexagon_points([self.surface], self.user, timezone.now())
        score = HexagonScore.objects.get(hexagon=self.hex_inside, user=self.user)
        self.assertEqual(score.points, 1)

    def test_does_not_score_hexagon_outside_surface(self):
        _award_hexagon_points([self.surface], self.user, timezone.now())
        self.assertFalse(HexagonScore.objects.filter(hexagon=self.hex_outside).exists())

    def test_increments_points_on_second_upload(self):
        _award_hexagon_points([self.surface], self.user, timezone.now())
        _award_hexagon_points([self.surface], self.user, timezone.now())
        score = HexagonScore.objects.get(hexagon=self.hex_inside, user=self.user)
        self.assertEqual(score.points, 2)

    def test_different_users_score_independently(self):
        other_user = make_user("bob")
        _award_hexagon_points([self.surface], self.user, timezone.now())
        _award_hexagon_points([self.surface], other_user, timezone.now())
        self.assertEqual(HexagonScore.objects.get(hexagon=self.hex_inside, user=self.user).points, 1)
        self.assertEqual(HexagonScore.objects.get(hexagon=self.hex_inside, user=other_user).points, 1)
