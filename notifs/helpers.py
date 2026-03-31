from notifs.models import Notification


def notify(user, notification_type, message, link=""):
    """Create a single notification."""
    return Notification.objects.create(
        user=user,
        notification_type=notification_type,
        message=message,
        link=link,
    )


def notify_bulk(user, notification_type, items):
    """Create multiple notifications.

    *items* is a list of ``(message, link)`` tuples.
    """
    Notification.objects.bulk_create([
        Notification(
            user=user,
            notification_type=notification_type,
            message=message,
            link=link,
        )
        for message, link in items
    ])
