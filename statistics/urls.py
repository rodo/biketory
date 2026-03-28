from django.conf import settings
from django.urls import path

urlpatterns = []

if settings.DEBUG:
    from statistics.views import api_compute_stats

    urlpatterns += [
        path("api/compute-stats/", api_compute_stats, name="api_compute_stats"),
    ]
