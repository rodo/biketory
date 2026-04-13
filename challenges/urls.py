from django.urls import path

from challenges.views.admin_challenges import (
    admin_challenge_create,
    admin_challenge_detail,
    admin_challenge_duplicate,
    admin_challenges,
)
from challenges.views.api_hexagons import api_challenge_hexagons
from challenges.views.challenge_detail import challenge_detail, join_challenge, leave_challenge
from challenges.views.challenge_list import challenge_list

urlpatterns = [
    # Player views
    path("challenges/", challenge_list, name="challenge_list"),
    path("challenges/<int:pk>/", challenge_detail, name="challenge_detail"),
    path("challenges/<int:pk>/join/", join_challenge, name="join_challenge"),
    path("challenges/<int:pk>/leave/", leave_challenge, name="leave_challenge"),
    # Admin views
    path("admin-dashboard/challenges/", admin_challenges, name="admin_challenges"),
    path("admin-dashboard/challenges/create/", admin_challenge_create, name="admin_challenge_create"),
    path("admin-dashboard/challenges/<int:pk>/", admin_challenge_detail, name="admin_challenge_detail"),
    path("admin-dashboard/challenges/<int:pk>/duplicate/", admin_challenge_duplicate, name="admin_challenge_duplicate"),
    # API
    path("api/challenges/hexagons/", api_challenge_hexagons, name="api_challenge_hexagons"),
]
