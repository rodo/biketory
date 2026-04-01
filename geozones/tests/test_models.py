from django.db import IntegrityError
from django.test import TestCase

from geozones.models import ZoneLeaderboardEntry

from ._helpers import make_entry, make_zone


class GeoZoneModelTest(TestCase):

    def test_str(self):
        zone = make_zone(code="FR", name="France", admin_level=2)
        self.assertEqual(str(zone), "FR — France (level 2)")

    def test_code_unique(self):
        make_zone(code="FR")
        with self.assertRaises(IntegrityError):
            make_zone(code="FR")

    def test_default_active_false(self):
        zone = make_zone()
        self.assertFalse(zone.active)

    def test_parent_relationship(self):
        parent = make_zone(code="FR", admin_level=2)
        child = make_zone(code="IDF", admin_level=4, parent=parent)
        self.assertEqual(child.parent, parent)
        self.assertIn(child, parent.children.all())

    def test_parent_set_null_on_delete(self):
        parent = make_zone(code="FR", admin_level=2)
        child = make_zone(code="IDF", admin_level=4, parent=parent)
        parent.delete()
        child.refresh_from_db()
        self.assertIsNone(child.parent)


class ZoneLeaderboardEntryModelTest(TestCase):

    def test_str(self):
        zone = make_zone(code="FR", name="France")
        entry = make_entry(zone, user_id=1, username="alice", conquered=10, acquired=5)
        self.assertIn("FR", str(entry))
        self.assertIn("alice", str(entry))

    def test_unique_zone_user(self):
        zone = make_zone(code="FR")
        make_entry(zone, user_id=1)
        with self.assertRaises(IntegrityError):
            make_entry(zone, user_id=1)

    def test_different_zones_same_user(self):
        z1 = make_zone(code="FR")
        z2 = make_zone(code="DE")
        make_entry(z1, user_id=1)
        make_entry(z2, user_id=1)  # should not raise
        self.assertEqual(ZoneLeaderboardEntry.objects.filter(user_id=1).count(), 2)
