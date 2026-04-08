import json

from django.contrib.auth.decorators import user_passes_test
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, render

from geozones.models import GeoZone


@user_passes_test(lambda u: u.is_superuser)
def admin_dashboard_geozones(request):
    zones = GeoZone.objects.filter(admin_level=2).order_by("name").values('pk','name','admin_level','active')

    return render(
        request,
        "traces/admin_dashboard_geozones.html",
        {"zones": zones},
    )


@user_passes_test(lambda u: u.is_superuser)
def admin_dashboard_geozone_detail(request, pk):
    zone = get_object_or_404(GeoZone.objects.select_related("parent"), pk=pk)
    children = zone.children.order_by("name")

    zone_geojson = json.dumps(json.loads(zone.geom.geojson))

    # Previous / next siblings (same parent + admin_level, ordered by name)
    siblings = GeoZone.objects.filter(
        parent=zone.parent, admin_level=zone.admin_level,
    ).order_by("name")
    prev_zone = siblings.filter(name__lt=zone.name).order_by("-name").first()
    next_zone = siblings.filter(name__gt=zone.name).order_by("name").first()

    return render(
        request,
        "traces/admin_dashboard_geozone_detail.html",
        {
            "zone": zone,
            "children": children,
            "zone_geojson": zone_geojson,
            "prev_zone": prev_zone,
            "next_zone": next_zone,
        },
    )


@user_passes_test(lambda u: u.is_superuser)
def admin_dashboard_geozone_toggle(request, pk):
    """Toggle the active status of a GeoZone via POST."""
    if request.method != "POST":
        return JsonResponse({"error": "POST required"}, status=405)

    zone = get_object_or_404(GeoZone, pk=pk)
    zone.active = not zone.active
    zone.save(update_fields=["active"])

    return JsonResponse({"active": zone.active})
