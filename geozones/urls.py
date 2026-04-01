from django.urls import path

from geozones.views import zone_leaderboard, zone_leaders

urlpatterns = [
    path(
        "leaderboard/zones/",
        zone_leaders,
        name="zone_leaders",
    ),
    path(
        "leaderboard/zone/<str:zone_code>/",
        zone_leaderboard,
        name="zone_leaderboard",
    ),
]
