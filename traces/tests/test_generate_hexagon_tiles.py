import shutil
import tempfile
from pathlib import Path

from django.contrib.gis.geos import Polygon
from django.core.management import call_command
from django.test import TestCase, override_settings
from django.utils import timezone

from traces.models import Hexagon, HexagonScore

from ._helpers import make_user


class GenerateHexagonTilesEmptyTest(TestCase):
    """Command runs without error when no hexagons exist."""

    @override_settings(MEDIA_ROOT=tempfile.mkdtemp())
    def test_no_hexagons_no_error(self):
        call_command("generate_hexagon_tiles", zoom_min=5, zoom_max=5)


class GenerateHexagonTilesWithDataTest(TestCase):
    """Command generates PNG files when hexagons with scores exist."""

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
    def test_generates_png_files(self):
        from django.conf import settings
        settings.MEDIA_ROOT = self.tmpdir
        call_command("generate_hexagon_tiles", zoom_min=8, zoom_max=8)
        tiles_dir = Path(self.tmpdir) / "tiles"
        tiles = list(tiles_dir.rglob("*.png"))
        self.assertGreater(len(tiles), 0)

    @override_settings()
    def test_tile_path_structure(self):
        from django.conf import settings
        settings.MEDIA_ROOT = self.tmpdir
        call_command("generate_hexagon_tiles", zoom_min=8, zoom_max=8)
        tiles_dir = Path(self.tmpdir) / "tiles"
        # Tiles should be at tiles/<zoom>/<x>/<y>.png
        for tile in tiles_dir.rglob("*.png"):
            parts = tile.relative_to(tiles_dir).parts
            self.assertEqual(len(parts), 3, f"Unexpected path: {tile}")
            self.assertEqual(parts[0], "8")  # zoom level
            self.assertTrue(tile.name.endswith(".png"))

    @override_settings()
    def test_clean_option(self):
        from django.conf import settings
        settings.MEDIA_ROOT = self.tmpdir
        tiles_dir = Path(self.tmpdir) / "tiles"
        tiles_dir.mkdir(parents=True, exist_ok=True)
        marker = tiles_dir / "marker.txt"
        marker.write_text("test")

        call_command("generate_hexagon_tiles", zoom_min=8, zoom_max=8, clean=True)

        self.assertFalse(marker.exists())
        tiles = list(tiles_dir.rglob("*.png"))
        self.assertGreater(len(tiles), 0)
