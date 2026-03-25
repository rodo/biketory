"""
Tests d'import de traces GPX réelles.

Convention de nommage des fixtures :
    trace_samples/closed_surface_<nb_surfaces>_hexagon_<nb_hexagons>.gpx

Le nom encode le résultat attendu après import :
- nb_surfaces : nombre de ClosedSurface extraites
- nb_hexagons : nombre de HexagonScore attribués à l'utilisateur
"""
import re
from datetime import timedelta
from pathlib import Path

import pytest
from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.utils import timezone

from traces.models import ClosedSurface, HexagonScore, Subscription, Trace
from traces.views.upload import _create_trace_hexagons, _extract_surfaces, _parse_route

_FIXTURES_DIR = Path(__file__).resolve().parent.parent.parent / "trace_samples"

_GPX_FIXTURES = list(_FIXTURES_DIR.glob("closed_surface_*_hexagon_*.gpx"))


def _parse_gpx_filename(path: Path) -> tuple[int, int]:
    m = re.match(r"closed_surface_(\d+)_hexagon_(\d+)\.gpx", path.name)
    assert m, f"Unexpected fixture filename: {path.name}"
    return int(m.group(1)), int(m.group(2))


@pytest.mark.django_db
@pytest.mark.parametrize("gpx_path", _GPX_FIXTURES, ids=lambda p: p.stem)
def test_gpx_import_surfaces_and_hexagons(settings, tmp_path, gpx_path):
    settings.MEDIA_ROOT = tmp_path
    expected_surfaces, expected_hexagons = _parse_gpx_filename(gpx_path)

    user = User.objects.create_user(username="testuser", password="testpass")
    today = timezone.now().date()
    Subscription.objects.create(
        user=user,
        start_date=today - timedelta(days=30),
        end_date=today + timedelta(days=30),
    )

    gpx_file = SimpleUploadedFile(
        gpx_path.name,
        gpx_path.read_bytes(),
        content_type="application/gpx+xml",
    )
    with gpx_path.open("rb") as f:
        route, first_point_date, length_km = _parse_route(f)

    trace = Trace.objects.create(
        gpx_file=gpx_file,
        route=route,
        first_point_date=first_point_date,
        uploaded_by=user,
    )
    _create_trace_hexagons(route)
    _extract_surfaces(trace)

    assert ClosedSurface.objects.filter(trace=trace).count() == expected_surfaces
    assert HexagonScore.objects.filter(user=user).count() == expected_hexagons
