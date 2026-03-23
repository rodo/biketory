import tempfile
from pathlib import Path

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings

from traces.badge_award import award_badges
from traces.models import Trace, UserBadge
from traces.views.upload import _create_trace_hexagons, _extract_surfaces, _parse_route

from ._helpers import make_user

_FIXTURES_DIR = Path(__file__).resolve().parent.parent.parent / "trace_samples"


def _upload_fixture(user, filename):
    """Parse a GPX fixture, create a Trace, run extraction, and award badges."""
    gpx_path = _FIXTURES_DIR / filename
    with gpx_path.open("rb") as f:
        route, first_point_date, length_km = _parse_route(f)
    gpx_file = SimpleUploadedFile(
        gpx_path.name, gpx_path.read_bytes(), content_type="application/gpx+xml"
    )
    trace = Trace.objects.create(
        gpx_file=gpx_file,
        route=route,
        length_km=length_km,
        first_point_date=first_point_date,
        uploaded_by=user,
    )
    if route:
        _create_trace_hexagons(route)
        _extract_surfaces(trace)
    award_badges(user, trace)
    return trace


@override_settings(MEDIA_ROOT=tempfile.mkdtemp())
class BadgeAwardTest(TestCase):

    def setUp(self):
        self.user = make_user()

    def test_new_user_has_zero_badges(self):
        self.assertEqual(UserBadge.objects.filter(user=self.user).count(), 0)

    def test_open_trace_awards_one_badge(self):
        """A trace with no closed surface should award only activite_premier_trace."""
        _upload_fixture(self.user, "closed_surface_0_hexagon_0.gpx")
        badges = set(UserBadge.objects.filter(user=self.user).values_list("badge_id", flat=True))
        self.assertEqual(badges, {"activite_premier_trace"})

    def test_closed_trace_awards_multiple_badges(self):
        """A trace with a closed surface and hexagons should award
        activite_premier_trace, territoire_premier, and surfaces_geometre."""
        _upload_fixture(self.user, "closed_surface_1_hexagon_20.gpx")
        badges = set(UserBadge.objects.filter(user=self.user).values_list("badge_id", flat=True))
        self.assertEqual(badges, {
            "activite_premier_trace",
            "territoire_premier",
            "surfaces_geometre",
        })
