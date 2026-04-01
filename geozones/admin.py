from django.contrib.gis import admin

from geozones.models import GeoZone


@admin.register(GeoZone)
class GeoZoneAdmin(admin.GISModelAdmin):
    list_display = ("code", "name", "admin_level", "parent", "loaded_at")
    list_filter = ("admin_level",)
    search_fields = ("code", "name")
