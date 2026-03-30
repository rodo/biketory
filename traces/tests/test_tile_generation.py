import shutil
import tempfile
from pathlib import Path

from django.contrib.gis.geos import Polygon
from django.test import TestCase, override_settings
from django.utils import timezone
from PIL import Image

from traces.models import Hexagon, HexagonScore
from traces.tile_generation import generate_tiles_for_bbox

from ._helpers import make_user


class GenerateTilesForBboxTest(TestCase):

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.user = make_user()
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
    def test_generates_png_for_bbox(self):
        from django.conf import settings
        settings.MEDIA_ROOT = self.tmpdir

        count = generate_tiles_for_bbox(8, 2.29, 48.79, 2.41, 48.91)

        tiles = list((Path(self.tmpdir) / "tiles" / "8").rglob("*.png"))
        self.assertGreater(len(tiles), 0)
        self.assertGreater(count, 0)

    @override_settings()
    def test_returns_tile_count(self):
        from django.conf import settings
        settings.MEDIA_ROOT = self.tmpdir

        count = generate_tiles_for_bbox(8, 2.29, 48.79, 2.41, 48.91)

        tiles = list((Path(self.tmpdir) / "tiles").rglob("*.png"))
        self.assertEqual(count, len(tiles))

    @override_settings()
    def test_no_hexagons_returns_zero(self):
        from django.conf import settings
        settings.MEDIA_ROOT = self.tmpdir

        # bbox far from any hexagon
        count = generate_tiles_for_bbox(8, 10.0, 50.0, 10.1, 50.1)

        self.assertEqual(count, 0)
        tiles_dir = Path(self.tmpdir) / "tiles"
        if tiles_dir.exists():
            self.assertEqual(list(tiles_dir.rglob("*.png")), [])

    @override_settings()
    def test_tile_is_valid_png(self):
        from django.conf import settings
        settings.MEDIA_ROOT = self.tmpdir

        generate_tiles_for_bbox(8, 2.29, 48.79, 2.41, 48.91)

        tile = next((Path(self.tmpdir) / "tiles").rglob("*.png"))
        img = Image.open(tile)
        self.assertEqual(img.size, (256, 256))
        self.assertEqual(img.mode, "RGBA")
