from django.conf import settings


def tile_server(request):
    return {
        "tile_server_url": settings.TILE_SERVER_URL,
        "media_url": settings.MEDIA_URL,
        "strava_auth_enabled": getattr(settings, "STRAVA_AUTH_ENABLED", False),
        "osm_auth_enabled": getattr(settings, "OSM_AUTH_ENABLED", False),
        "map_zoom_min": settings.MAP_ZOOM_MIN,
        "map_zoom_max": settings.MAP_ZOOM_MAX,
        "tiles_static_min_zoom": settings.TILES_STATIC_MIN_ZOOM,
        "tiles_static_max_zoom": settings.TILES_STATIC_MAX_ZOOM,
        "tiles_dynamic_min_zoom": settings.TILES_DYNAMIC_MIN_ZOOM,
        "tiles_dynamic_max_zoom": settings.TILES_DYNAMIC_MAX_ZOOM,
    }
