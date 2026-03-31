from django.urls import path

from notifs import views

urlpatterns = [
    path("notifications/", views.notifications_list, name="notifications"),
    path(
        "notifications/mark-read/",
        views.notifications_mark_read,
        name="notifications_mark_read",
    ),
]
