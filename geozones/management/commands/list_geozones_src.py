import gzip
import json
import time
from collections import Counter, defaultdict
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand

SRC_DIR = Path(settings.MEDIA_ROOT) / "src"


def _load_features(filepath):
    if filepath.suffix == ".gz":
        with gzip.open(filepath, "rt", encoding="utf-8") as f:
            data = json.load(f)
    else:
        with open(filepath, encoding="utf-8") as f:
            data = json.load(f)
    return data.get("features", [])


class Command(BaseCommand):
    help = "List all features per GeoJSON file in media/src/ with statistics."

    def add_arguments(self, parser):
        parser.add_argument(
            "--admin-level",
            type=int,
            default=None,
            help="Only show features with this admin_level.",
        )
        parser.add_argument(
            "--verbose",
            action="store_true",
            help="Show individual feature names.",
        )

    def handle(self, *args, **options):
        t0 = time.monotonic()
        level_filter = options["admin_level"]
        verbose = options["verbose"]

        if not SRC_DIR.exists():
            self.stderr.write(f"Source directory {SRC_DIR} does not exist.")
            return

        geojson_files = sorted(
            list(SRC_DIR.rglob("*.geojson")) + list(SRC_DIR.rglob("*.geojson.gz"))
        )
        if not geojson_files:
            self.stderr.write("No .geojson or .geojson.gz files found.")
            return

        total_files = 0
        total_features = 0
        total_admin_levels = Counter()
        total_geom_types = Counter()
        total_boundaries = Counter()

        for filepath in geojson_files:
            features = _load_features(filepath)
            rel_path = filepath.relative_to(SRC_DIR)

            if level_filter is not None:
                features = [
                    f for f in features
                    if f.get("properties", {}).get("admin_level") == level_filter
                ]

            if not features:
                continue

            total_files += 1
            total_features += len(features)

            admin_levels = Counter()
            geom_types = Counter()
            boundaries = Counter()
            names_by_level = defaultdict(list)

            for feat in features:
                props = feat.get("properties", {})
                geom = feat.get("geometry", {})

                al = props.get("admin_level")
                gt = geom.get("type", "?")
                boundary = props.get("boundary", "?")
                name = props.get("name") or props.get("name_en") or props.get("NAME_ENGL") or "—"

                admin_levels[al] += 1
                geom_types[gt] += 1
                boundaries[boundary] += 1
                total_admin_levels[al] += 1
                total_geom_types[gt] += 1
                total_boundaries[boundary] += 1
                names_by_level[al].append(name)

            self.stdout.write(f"\n{'=' * 70}")
            self.stdout.write(self.style.SUCCESS(f"  {rel_path}"))
            self.stdout.write(f"  Features: {len(features)}")
            self.stdout.write(f"  Admin levels: {_format_counter(admin_levels)}")
            self.stdout.write(f"  Geometry types: {_format_counter(geom_types)}")
            if len(boundaries) > 1 or "administrative" not in boundaries:
                self.stdout.write(f"  Boundaries: {_format_counter(boundaries)}")

            if verbose:
                for al in sorted(names_by_level.keys(), key=lambda x: (x is None, x)):
                    label = f"level {al}" if al is not None else "level ?"
                    names = sorted(names_by_level[al])
                    self.stdout.write(f"  [{label}] {', '.join(names[:20])}")
                    if len(names) > 20:
                        self.stdout.write(f"           ... and {len(names) - 20} more")

        elapsed = time.monotonic() - t0

        self.stdout.write(f"\n{'=' * 70}")
        self.stdout.write(self.style.SUCCESS("  TOTALS"))
        self.stdout.write(f"  Files: {total_files}")
        self.stdout.write(f"  Features: {total_features}")
        self.stdout.write(f"  Admin levels: {_format_counter(total_admin_levels)}")
        self.stdout.write(f"  Geometry types: {_format_counter(total_geom_types)}")
        self.stdout.write(f"  Boundary types: {_format_counter(total_boundaries)}")
        self.stdout.write(f"  Elapsed: {elapsed:.1f} s")
        self.stdout.write("")


def _format_counter(counter):
    parts = []
    for key in sorted(counter.keys(), key=lambda x: (x is None, x)):
        label = str(key) if key is not None else "?"
        parts.append(f"{label}={counter[key]}")
    return ", ".join(parts)
