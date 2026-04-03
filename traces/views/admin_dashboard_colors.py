from django.conf import settings
from django.contrib.auth.decorators import user_passes_test
from django.shortcuts import render


@user_passes_test(lambda u: u.is_superuser)
def admin_dashboard_colors(request):
    return render(
        request,
        "traces/admin_dashboard_colors.html",
        {
            "zoom_min": settings.TILES_STATIC_MIN_ZOOM,
            "zoom_max": settings.TILES_STATIC_MAX_ZOOM,
            "global_rgb": [200, 145, 45],
            "user_rgb": [41, 128, 185],
            "opacity_at_min_zoom": 200,
            "opacity_at_knee": 140,
            "opacity_at_max_zoom": 90,
            "knee_zoom": 8,
        },
    )
