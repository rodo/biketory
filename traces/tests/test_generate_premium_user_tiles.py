import datetime
import shutil
from pathlib import Path

from django.conf import settings
from django.contrib.gis.geos import Polygon
from django.core.management import call_command
from django.test import TestCase
from django.utils import timezone

from traces.models import Hexagon, HexagonScore, Subscription, Trace, UserProfile

from ._helpers import make_user, small_route


def _today():
    return timezone.now().date()


def _tiles_dir():
    return Path(settings.MEDIA_ROOT) / "tiles"


def _user_tiles_dir(user):
    hexagram = UserProfile.objects.values_list("hexagram", flat=True).get(user=user)
    return _tiles_dir() / hexagram[0] / hexagram[1] / hexagram


class _BaseTileTest(TestCase):
    """Set up a user with a hexagon score and a recent trace."""

    def setUp(self):
        self.user = make_user("premium_user")
        # Create an active subscription
        self.sub = Subscription.objects.create(
            user=self.user,
            start_date=_today() - datetime.timedelta(days=30),
            end_date=_today() + datetime.timedelta(days=30),
        )
        # Create a recent trace
        self.trace = Trace.objects.create(
            uploaded_by=self.user,
            route=small_route(),
        )
        # Create a hexagon with a score
        self.hexagon = Hexagon.objects.create(
            geom=Polygon([
                (2.30, 48.80),
                (2.35, 48.80),
                (2.35, 48.85),
                (2.30, 48.85),
                (2.30, 48.80),
            ])
        )
        self.score = HexagonScore.objects.create(
            hexagon=self.hexagon,
            user=self.user,
            points=3,
            last_earned_at=timezone.now(),
        )

    def tearDown(self):
        user_dir = _user_tiles_dir(self.user)
        if user_dir.exists():
            shutil.rmtree(user_dir)


class PremiumUserWithRecentTraceTest(_BaseTileTest):

    def test_generates_tiles(self):
        call_command("generate_premium_user_tiles", zoom_min=8, zoom_max=8)
        user_dir = _user_tiles_dir(self.user)
        tiles = list(user_dir.rglob("*.png"))
        self.assertGreater(len(tiles), 0)


class NonPremiumUserIgnoredTest(TestCase):

    def setUp(self):
        self.user = make_user("free_user")
        self.trace = Trace.objects.create(
            uploaded_by=self.user,
            route=small_route(),
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
        self._user_dir = _user_tiles_dir(self.user)
        if self._user_dir.exists():
            shutil.rmtree(self._user_dir)

    def tearDown(self):
        if self._user_dir.exists():
            shutil.rmtree(self._user_dir)

    def test_no_tiles_generated(self):
        call_command("generate_premium_user_tiles", zoom_min=8, zoom_max=8)
        tiles = list(self._user_dir.rglob("*.png")) if self._user_dir.exists() else []
        self.assertEqual(len(tiles), 0)


class PremiumUserWithoutRecentTraceTest(TestCase):

    def setUp(self):
        self.user = make_user("old_premium")
        Subscription.objects.create(
            user=self.user,
            start_date=_today() - datetime.timedelta(days=30),
            end_date=_today() + datetime.timedelta(days=30),
        )
        # Trace uploaded 10 days ago (outside 7-day window)
        self.trace = Trace.objects.create(
            uploaded_by=self.user,
            route=small_route(),
        )
        # Manually backdate uploaded_at
        Trace.objects.filter(pk=self.trace.pk).update(
            uploaded_at=timezone.now() - datetime.timedelta(days=10)
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
        self._user_dir = _user_tiles_dir(self.user)
        if self._user_dir.exists():
            shutil.rmtree(self._user_dir)

    def tearDown(self):
        if self._user_dir.exists():
            shutil.rmtree(self._user_dir)

    def test_no_tiles_generated(self):
        call_command("generate_premium_user_tiles", zoom_min=8, zoom_max=8)
        tiles = list(self._user_dir.rglob("*.png")) if self._user_dir.exists() else []
        self.assertEqual(len(tiles), 0)


class CleanOptionTest(_BaseTileTest):

    def test_clean_removes_existing_tiles(self):
        # Generate tiles first
        call_command("generate_premium_user_tiles", zoom_min=8, zoom_max=8)
        user_dir = _user_tiles_dir(self.user)
        self.assertTrue(user_dir.exists())

        # Place a marker file to verify cleanup
        marker = user_dir / "marker.txt"
        marker.write_text("test")

        # Regenerate with --clean
        call_command("generate_premium_user_tiles", zoom_min=8, zoom_max=8, clean=True)

        # Marker should be gone (directory was removed and recreated)
        self.assertFalse(marker.exists())
        # But tiles should exist again
        tiles = list(user_dir.rglob("*.png"))
        self.assertGreater(len(tiles), 0)
