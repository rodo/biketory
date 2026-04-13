from notifs.models import Notification
from traces.tasks_emails import send_notification_email

_EMAIL_PREF_FIELD = {
    "badge_awarded": "email_on_badge",
    "friend_request": "email_on_friend",
    "friend_accepted": "email_on_friend",
    "trace_analyzed": "email_on_trace_analyzed",
    "referral_signup": "email_on_referral",
    "challenge_won": "email_on_challenge",
}


def _should_send_email(user, notification_type):
    """Check if the user wants an email for this notification type."""
    field = _EMAIL_PREF_FIELD.get(notification_type)
    if not field:
        return False
    profile = getattr(user, "profile", None)
    if not profile:
        return False
    return getattr(profile, field, False)


def notify(user, notification_type, message, link=""):
    """Create a single notification."""
    notification = Notification.objects.create(
        user=user,
        notification_type=notification_type,
        message=message,
        link=link,
    )
    if _should_send_email(user, notification_type):
        send_notification_email.defer(
            user_id=user.pk, message=message, link=link,
        )
    return notification


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
    if _should_send_email(user, notification_type):
        for message, link in items:
            send_notification_email.defer(
                user_id=user.pk, message=message, link=link,
            )
