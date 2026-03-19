from django.urls import path

from . import views

urlpatterns = [
    path("", views.landing, name="landing"),
    path("upload/", views.upload_trace, name="upload_trace"),
    path("register/", views.register, name="register"),
    path("traces/", views.trace_list, name="trace_list"),
    path("traces/<int:pk>/", views.trace_detail, name="trace_detail"),
    path("traces/<int:pk>/delete/", views.delete_trace, name="delete_trace"),
    path("traces/<int:pk>/surfaces/", views.trace_surfaces, name="trace_surfaces"),
    path("surfaces/", views.surface_list, name="surface_list"),
    path("hexagons/", views.hexagon_stats, name="hexagon_stats"),
    path("legal/", views.legal, name="legal"),
    path("stats/", views.stats, name="stats"),
    path("stats/monthly/", views.stats_monthly, name="stats_monthly"),
    path("stats/pie/", views.stats_pie, name="stats_pie"),
    path("hexagons/<int:pk>/", views.hexagon_detail, name="hexagon_detail"),
    path("profile/", views.profile, name="profile"),
    path("friends/", views.friends, name="friends"),
    path("api/upload/", views.api_upload_trace, name="api_upload_trace"),
]
