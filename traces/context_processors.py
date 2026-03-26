from django.conf import settings


def tile_server(request):
    return {
        "tile_server_url": settings.TILE_SERVER_URL,
        "media_url": settings.MEDIA_URL,
        "strava_auth_enabled": getattr(settings, "STRAVA_AUTH_ENABLED", False),
    }
