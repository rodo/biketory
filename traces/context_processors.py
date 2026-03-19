from django.conf import settings


def tile_server(request):
    return {"tile_server_url": settings.TILE_SERVER_URL}
