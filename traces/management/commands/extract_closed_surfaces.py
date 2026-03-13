from django.conf import settings
from django.contrib.gis.db.models import Union
from django.contrib.gis.geos import MultiPolygon, Polygon
from django.core.management.base import BaseCommand

from traces.models import ClosedSurface, Trace, UserSurfaceStats

# Maximum distance in degrees between start and end point to consider a trace closed (~100m)
CLOSURE_THRESHOLD = 0.001

# 10 metres expressed in degrees (1 deg ≈ 111 320 m); used to merge adjacent surfaces
ADJACENCY_THRESHOLD_DEG = 10 / 111_320
HALF_ADJACENCY = ADJACENCY_THRESHOLD_DEG / 2


class Command(BaseCommand):
    help = "List all traces and extract closed surfaces from them"

    def handle(self, *args, **options):
        traces = Trace.objects.select_related("uploaded_by").exclude(route=None).filter(extracted=False).order_by("uploaded_at")

        if not traces.exists():
            self.stdout.write("No traces found.")
            return

        closed_count = 0
        affected_users = set()

        for trace in traces:
            total_segments = trace.route.num_geom
            self.stdout.write(f"\nTrace #{trace.pk} — {trace.gpx_file.name} — {trace.uploaded_at:%Y-%m-%d %H:%M} — {total_segments} segment(s)")

            for idx, segment in enumerate(trace.route):
                start = segment[0]
                end = segment[-1]
                distance = ((end[0] - start[0]) ** 2 + (end[1] - start[1]) ** 2) ** 0.5

                if segment.closed or distance <= CLOSURE_THRESHOLD:
                    coords = list(segment.coords)
                    if coords[0] != coords[-1]:
                        coords.append(coords[0])
                    polygon = Polygon(coords)
                    if not polygon.valid:
                        polygon = polygon.buffer(0)
                        if polygon.geom_type == "MultiPolygon":
                            polygon = max(polygon, key=lambda p: p.area)
                    if polygon.transform(3857, clone=True).area < settings.MIN_SURFACE_AREA_M2:
                        self.stdout.write(f"  [seg {idx}] Skipped (area < {settings.MIN_SURFACE_AREA_M2} m²)")
                        continue
                    surface, created = ClosedSurface.objects.get_or_create(
                        trace=trace,
                        segment_index=idx,
                        defaults={"polygon": polygon, "owner": trace.uploaded_by},
                    )
                    status = "stored" if created else "already exists"
                    self.stdout.write(
                        self.style.SUCCESS(
                            f"  [seg {idx}] Closed surface {status}. "
                            f"Area: {polygon.area:.6f} deg² | "
                            f"Centroid: {polygon.centroid.x:.5f}, {polygon.centroid.y:.5f}"
                        )
                    )
                    if trace.uploaded_by:
                        affected_users.add(trace.uploaded_by)
                    closed_count += 1
                else:
                    self.stdout.write(f"  [seg {idx}] Open segment (gap: {distance:.5f}°)")

            trace.extracted = True
            trace.save(update_fields=["extracted"])

        # Step 1 — compute each user's merged union (with adjacency merging)
        user_unions = {}
        for user in affected_users:
            surfaces = ClosedSurface.objects.filter(owner=user)
            buffered = [cs.polygon.buffer(HALF_ADJACENCY) for cs in surfaces]
            merged = buffered[0]
            for geom in buffered[1:]:
                merged = merged.union(geom)
            user_unions[user] = merged.buffer(-HALF_ADJACENCY)

        # Step 2 — subtract every other user's union to resolve overlaps
        users = list(user_unions)
        for user in users:
            geom = user_unions[user]
            for other_user in users:
                if other_user is not user:
                    geom = geom.difference(user_unions[other_user])
            user_unions[user] = geom

        # Step 3 — persist
        for user, merged in user_unions.items():
            if isinstance(merged, Polygon):
                merged = MultiPolygon(merged)
            total = merged.area if merged else 0.0
            UserSurfaceStats.objects.update_or_create(
                user=user,
                defaults={"total_area": total, "union": merged if not merged.empty else None},
            )
            self.stdout.write(
                self.style.SUCCESS(f"\nUpdated stats for {user.username}: {total:.6f} deg²")
            )

        self.stdout.write(
            f"\nSummary: {traces.count()} traces — {closed_count} closed surface(s) found."
        )
