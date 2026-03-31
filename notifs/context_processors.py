from notifs.models import Notification


def notifications(request):
    count = 0
    if hasattr(request, "user") and request.user.is_authenticated:
        count = Notification.objects.filter(
            user=request.user, is_read=False
        ).count()
    return {"unread_notifications_count": count}
