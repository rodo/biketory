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
