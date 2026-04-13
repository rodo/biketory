import logging

from django.conf import settings
from django.core.mail import send_mail
from procrastinate.contrib.django import app

logger = logging.getLogger(__name__)


@app.task(queue="emails")
def notify_new_registration(user_id: int, username: str, email: str):
    """Send an email notification when a new user registers."""
    notify_email = settings.REGISTRATION_NOTIFY_EMAIL
    if not notify_email:
        logger.warning("REGISTRATION_NOTIFY_EMAIL not configured, skipping.")
        return

    subject = f"Biketory — New registration: {username}"
    body = (
        f"A new user has registered on Biketory.\n\n"
        f"Username: {username}\n"
        f"Email: {email}\n"
        f"Admin: /admin/auth/user/{user_id}/change/\n"
    )

    send_mail(
        subject=subject,
        message=body,
        from_email=None,
        recipient_list=[notify_email],
        fail_silently=True,
    )
    logger.info("Registration notification sent for user %s (%d).", username, user_id)


@app.task(queue="emails")
def send_notification_email(user_id: int, message: str, link: str):
    """Send a notification email to the user."""
    from django.contrib.auth import get_user_model

    user_model = get_user_model()
    try:
        user = user_model.objects.get(pk=user_id)
    except user_model.DoesNotExist:
        logger.warning("User %d not found, skipping notification email.", user_id)
        return

    if not user.email:
        logger.warning("User %d has no email, skipping notification email.", user_id)
        return

    base_url = getattr(settings, "SITE_URL", "http://localhost:8000").rstrip("/")
    full_link = f"{base_url}{link}" if link else ""

    body = message
    if full_link:
        body += f"\n\n{full_link}"

    send_mail(
        subject=f"Biketory — {message}",
        message=body,
        from_email=None,
        recipient_list=[user.email],
        fail_silently=True,
    )
    logger.info("Notification email sent to user %d.", user_id)
