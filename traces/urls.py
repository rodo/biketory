from django.urls import path

from . import views

urlpatterns = [
    path("", views.landing, name="landing"),
    path("upload/", views.upload_trace, name="upload_trace"),
    path("register/", views.register, name="register"),
    path("create/", views.trace_create, name="trace_create"),
    path("traces/", views.trace_list, name="trace_list"),
    path("traces/<int:pk>/", views.trace_detail, name="trace_detail"),
    path("traces/<int:pk>/delete/", views.delete_trace, name="delete_trace"),
    path("traces/<int:pk>/surfaces/", views.trace_surfaces, name="trace_surfaces"),
    path("about/", views.about, name="about"),
    path("admin-dashboard/", views.admin_dashboard, name="admin_dashboard"),
    path("legal/", views.legal, name="legal"),
    path("stats/", views.stats, name="stats"),
    path("stats/monthly/", views.stats_monthly, name="stats_monthly"),
    path("stats/traces/", views.stats_traces, name="stats_traces"),
    path("stats/badges/", views.stats_badges, name="stats_badges"),
    path("hexagons/<int:pk>/", views.hexagon_detail, name="hexagon_detail"),
    path("profile/", views.profile, name="profile"),
    path("profile/badges/", views.badges, name="badges"),
    path("friends/", views.friends, name="friends"),
    path("api/hexagons/", views.landing_hexagons, name="landing_hexagons"),
    path("api/upload/", views.api_upload_trace, name="api_upload_trace"),
    path("premium/", views.subscription_required, name="subscription_required"),
    path("s/<str:code>/", views.shared_profile, name="shared_profile"),
]
