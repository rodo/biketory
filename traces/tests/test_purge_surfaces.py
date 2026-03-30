from django.core.management import call_command
from django.test import TestCase
from django.utils import timezone

from traces.models import ClosedSurface, Trace, UserSurfaceStats

from ._helpers import make_user, small_route, square_polygon


class PurgeSurfacesTests(TestCase):

    def setUp(self):
        self.user = make_user()
        self.trace = Trace.objects.create(
            gpx_file="test.gpx",
            route=small_route(),
            uploaded_by=self.user,
            extracted=True,
        )
        ClosedSurface.objects.create(
            trace=self.trace,
            owner=self.user,
            segment_index=0,
            polygon=square_polygon(2.35, 48.85, 0.01),
            detected_at=timezone.now(),
        )
        UserSurfaceStats.objects.get_or_create(user=self.user)

    def test_purge_deletes_surfaces(self):
        call_command("purge_surfaces", "--yes")
        self.assertEqual(ClosedSurface.objects.count(), 0)

    def test_purge_resets_extracted_flag(self):
        call_command("purge_surfaces", "--yes")
        self.trace.refresh_from_db()
        self.assertFalse(self.trace.extracted)

    def test_purge_clears_user_stats(self):
        call_command("purge_surfaces", "--yes")
        self.assertEqual(UserSurfaceStats.objects.count(), 0)

    def test_purge_with_no_data(self):
        ClosedSurface.objects.all().delete()
        Trace.objects.filter(extracted=True).update(extracted=False)
        UserSurfaceStats.objects.all().delete()
        call_command("purge_surfaces", "--yes")
        self.assertEqual(ClosedSurface.objects.count(), 0)
