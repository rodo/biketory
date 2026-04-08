import hashlib
import json
import logging
import time
from pathlib import Path

from django.contrib.gis.geos import Point
from django.core.management.base import BaseCommand

from challenges.models import Dataset, DatasetFeature

logger = logging.getLogger(__name__)

DATA_DIR = Path("data")
BATCH_SIZE = 1000


def _md5(filepath):
    h = hashlib.md5()
    with open(filepath, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


class Command(BaseCommand):
    help = "Import GeoJSON Point datasets from data/ directory."

    def add_arguments(self, parser):
        parser.add_argument(
            "--path",
            type=str,
            default=None,
            help="Path to a specific GeoJSON file (relative or absolute).",
        )
        parser.add_argument(
            "--name",
            type=str,
            default=None,
            help="Human-readable name for the dataset (default: filename without extension).",
        )

    def handle(self, *args, **options):
        t0 = time.monotonic()
        specific_path = options["path"]
        custom_name = options["name"]

        if specific_path:
            files = [Path(specific_path)]
        else:
            if not DATA_DIR.exists():
                self.stderr.write(f"Directory {DATA_DIR} does not exist.")
                return
            files = sorted(DATA_DIR.rglob("*.geojson"))

        if not files:
            self.stderr.write("No .geojson files found.")
            return

        total_created = 0

        for filepath in files:
            filepath = filepath.resolve()
            if not filepath.exists():
                self.stderr.write(f"File not found: {filepath}")
                continue

            md5_hash = _md5(filepath)
            if Dataset.objects.filter(md5_hash=md5_hash).exists():
                logger.info("Skipping %s (already imported, MD5=%s)", filepath.name, md5_hash)
                continue

            with open(filepath, encoding="utf-8") as f:
                data = json.load(f)

            features = data.get("features", [])
            point_features = [
                feat for feat in features
                if feat.get("geometry", {}).get("type") == "Point"
            ]

            if not point_features:
                logger.info("Skipping %s (no Point features)", filepath.name)
                continue

            name = custom_name or filepath.stem
            source_file = str(filepath.relative_to(Path.cwd())) if filepath.is_relative_to(Path.cwd()) else str(filepath)

            dataset = Dataset.objects.create(
                name=name,
                source_file=source_file,
                md5_hash=md5_hash,
                feature_count=len(point_features),
            )

            batch = []
            for feat in point_features:
                coords = feat["geometry"]["coordinates"]
                geom = Point(coords[0], coords[1], srid=4326)
                props = feat.get("properties", {}) or {}
                batch.append(DatasetFeature(
                    dataset=dataset,
                    geom=geom,
                    properties=props,
                ))
                if len(batch) >= BATCH_SIZE:
                    DatasetFeature.objects.bulk_create(batch)
                    batch = []

            if batch:
                DatasetFeature.objects.bulk_create(batch)

            total_created += len(point_features)
            logger.info(
                "Imported %s: %d Point features (dataset #%d)",
                filepath.name, len(point_features), dataset.pk,
            )

        elapsed = time.monotonic() - t0
        logger.info("Done: %d features imported in %.1f s", total_created, elapsed)
