from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import render
from django.views.decorators.http import require_POST

from notifs.models import Notification


@login_required
def notifications_list(request):
    notifications = Notification.objects.filter(user=request.user)[:50]
    return render(request, "notifs/notifications.html", {
        "notifications": notifications,
    })


@login_required
@require_POST
def notifications_mark_read(request):
    Notification.objects.filter(user=request.user, is_read=False).update(
        is_read=True
    )
    return JsonResponse({"ok": True})
