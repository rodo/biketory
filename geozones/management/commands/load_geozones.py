import gzip
import json
import logging
import time
from pathlib import Path

from django.conf import settings
from django.contrib.gis.geos import GEOSGeometry, MultiPolygon, Polygon
from django.core.management.base import BaseCommand

from geozones.models import GeoZone

logger = logging.getLogger(__name__)

SRC_DIR = Path(settings.MEDIA_ROOT) / "src"


def _normalize_multipolygon(geom):
    """Ensure geometry is a MultiPolygon."""
    geos = GEOSGeometry(json.dumps(geom))
    if isinstance(geos, Polygon):
        geos = MultiPolygon(geos, srid=geos.srid)
    return geos


def _load_features(filepath):
    """Load GeoJSON features from a .geojson or .geojson.gz file."""
    if filepath.suffix == ".gz":
        with gzip.open(filepath, "rt", encoding="utf-8") as f:
            data = json.load(f)
    else:
        with open(filepath, encoding="utf-8") as f:
            data = json.load(f)
    return data.get("features", [])


def _is_osmb(feature):
    """Check if a feature comes from an OSM Boundaries export."""
    props = feature.get("properties", {})
    return "osm_id" in props and "admin_level" in props


def _extract_osmb(feature):
    """Extract code, name, and admin_level from an OSMB feature."""
    props = feature.get("properties", {})
    osm_id = props.get("osm_id")
    admin_level = props.get("admin_level")
    if osm_id is None or admin_level is None:
        return None, None, None
    code = str(abs(int(osm_id)))
    name = props.get("name") or props.get("name_en") or ""
    return code, name.strip(), int(admin_level)


def _extract_eurostat(feature):
    """Extract code, name, and admin_level from a Eurostat country file."""
    props = feature.get("properties", {})
    code = props.get("CNTR_ID") or props.get("ISO_A2", "")
    name = props.get("NAME_ENGL") or props.get("CNTR_NAME") or ""
    if not code:
        return None, None, None
    return str(code).strip(), str(name).strip(), 2


class Command(BaseCommand):
    help = "Load geographic zones from GeoJSON files in media/src/."

    def add_arguments(self, parser):
        parser.add_argument(
            "--admin-level",
            type=int,
            default=None,
            help="Only load features with this admin_level (OSMB files only).",
        )

    def handle(self, *args, **options):
        t0 = time.monotonic()
        level_filter = options["admin_level"]

        if not SRC_DIR.exists():
            self.stderr.write(f"Source directory {SRC_DIR} does not exist.")
            return

        geojson_files = sorted(
            list(SRC_DIR.rglob("*.geojson")) + list(SRC_DIR.rglob("*.geojson.gz"))
        )
        if not geojson_files:
            self.stderr.write("No .geojson or .geojson.gz files found.")
            return

        created = 0
        updated = 0
        skipped = 0

        for filepath in geojson_files:
            features = _load_features(filepath)
            logger.info("  %s: %d features", filepath.relative_to(SRC_DIR), len(features))

            for feature in features:
                if _is_osmb(feature):
                    code, name, admin_level = _extract_osmb(feature)
                else:
                    code, name, admin_level = _extract_eurostat(feature)

                if not code or admin_level is None:
                    skipped += 1
                    continue

                if level_filter is not None and admin_level != level_filter:
                    skipped += 1
                    continue

                # Skip non-administrative boundaries
                boundary = feature.get("properties", {}).get("boundary", "administrative")
                if boundary != "administrative":
                    skipped += 1
                    continue

                geom = _normalize_multipolygon(feature["geometry"])

                _, is_created = GeoZone.objects.update_or_create(
                    code=code,
                    defaults={
                        "name": name,
                        "admin_level": admin_level,
                        "geom": geom,
                    },
                )
                if is_created:
                    created += 1
                else:
                    updated += 1

        # Second pass: link parents via spatial containment
        self._link_parents()

        elapsed = time.monotonic() - t0
        logger.info(
            "Done: %d created, %d updated, %d skipped in %.1f s",
            created, updated, skipped, elapsed,
        )

    def _link_parents(self):
        """Link child zones to their nearest parent by admin_level via spatial containment."""
        all_levels = sorted(
            GeoZone.objects.values_list("admin_level", flat=True).distinct()
        )
        if len(all_levels) < 2:
            return

        for i, level in enumerate(all_levels[1:], start=1):
            parent_level = all_levels[i - 1]
            parents = list(GeoZone.objects.filter(admin_level=parent_level))
            children = GeoZone.objects.filter(admin_level=level, parent__isnull=True)

            for child in children:
                centroid = child.geom.centroid
                for parent in parents:
                    if parent.geom.contains(centroid):
                        child.parent = parent
                        child.save(update_fields=["parent"])
                        break
