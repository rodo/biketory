from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase, override_settings
from django.utils import timezone

from traces.models import Hexagon, HexagonScore, Trace, UserBadge

from ._helpers import make_user, small_route, square_polygon


class ResetDataTests(TestCase):
    def setUp(self):
        self.user = make_user()
        self.trace = Trace.objects.create(
            gpx_file="test.gpx",
            route=small_route(),
            uploaded_by=self.user,
        )
        self.hexagon = Hexagon.objects.create(geom=square_polygon(2.35, 48.85, 0.01))
        HexagonScore.objects.create(
            hexagon=self.hexagon, user=self.user, points=5,
            last_earned_at=timezone.now(),
        )
        UserBadge.objects.create(user=self.user, badge_id="first_trace", trace=self.trace)

    @override_settings(DEBUG=True)
    def test_reset_data_deletes_everything(self):
        call_command("reset_data", "--yes")

        self.assertEqual(Trace.objects.count(), 0)
        self.assertEqual(UserBadge.objects.count(), 0)
        self.assertEqual(Hexagon.objects.count(), 0)
        self.assertEqual(HexagonScore.objects.count(), 0)

    @override_settings(DEBUG=False)
    def test_reset_data_refused_when_debug_false(self):
        with self.assertRaises(CommandError):
            call_command("reset_data", "--yes")

        self.assertEqual(Trace.objects.count(), 1)
        self.assertEqual(UserBadge.objects.count(), 1)
