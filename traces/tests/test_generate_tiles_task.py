import shutil
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

from django.contrib.gis.geos import Polygon
from django.test import TestCase, override_settings
from django.utils import timezone

from traces.models import Hexagon, HexagonScore, Trace
from traces.tasks import generate_tiles

from ._helpers import make_user, small_route


class GenerateTilesTaskTest(TestCase):

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.user = make_user()
        self.trace = Trace.objects.create(
            uploaded_by=self.user,
            route=small_route(),
            bbox=Polygon.from_bbox((2.29, 48.79, 2.41, 48.91)),
            status=Trace.STATUS_SURFACE_EXTRACTED,
        )
        self.hexagon = Hexagon.objects.create(
            geom=Polygon([
                (2.30, 48.80),
                (2.35, 48.80),
                (2.35, 48.85),
                (2.30, 48.85),
                (2.30, 48.80),
            ])
        )
        HexagonScore.objects.create(
            hexagon=self.hexagon,
            user=self.user,
            points=3,
            last_earned_at=timezone.now(),
        )

    def tearDown(self):
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    @override_settings()
    def test_generates_tiles_for_ready_trace(self):
        from django.conf import settings
        settings.MEDIA_ROOT = self.tmpdir

        generate_tiles(self.trace.pk, zoom=8)

        tiles = list((Path(self.tmpdir) / "tiles").rglob("*.png"))
        self.assertGreater(len(tiles), 0)

    @override_settings()
    def test_skips_missing_trace(self):
        from django.conf import settings
        settings.MEDIA_ROOT = self.tmpdir

        generate_tiles(999999, zoom=8)

        tiles_dir = Path(self.tmpdir) / "tiles"
        if tiles_dir.exists():
            self.assertEqual(list(tiles_dir.rglob("*.png")), [])

    @override_settings()
    def test_skips_trace_without_bbox(self):
        from django.conf import settings
        settings.MEDIA_ROOT = self.tmpdir

        self.trace.bbox = None
        self.trace.save()

        generate_tiles(self.trace.pk, zoom=8)

        tiles_dir = Path(self.tmpdir) / "tiles"
        if tiles_dir.exists():
            self.assertEqual(list(tiles_dir.rglob("*.png")), [])

    def test_reschedules_not_analyzed_trace(self):
        self.trace.status = Trace.STATUS_NOT_ANALYZED
        self.trace.save()

        mock_deferred = MagicMock()
        with patch.object(generate_tiles, "configure", return_value=mock_deferred) as mock_configure:
            generate_tiles(self.trace.pk, zoom=8)

        mock_configure.assert_called_once_with(
            queueing_lock=f"generate_tiles_{self.trace.pk}_8",
            schedule_in={"seconds": 5},
        )
        mock_deferred.defer.assert_called_once_with(
            trace_id=self.trace.pk, zoom=8,
        )
