from django.conf import settings
from django.db import models


class Notification(models.Model):
    BADGE_AWARDED = "badge_awarded"
    FRIEND_REQUEST = "friend_request"
    FRIEND_ACCEPTED = "friend_accepted"
    TRACE_ANALYZED = "trace_analyzed"
    REFERRAL_SIGNUP = "referral_signup"

    TYPE_CHOICES = [
        (BADGE_AWARDED, "Badge awarded"),
        (FRIEND_REQUEST, "Friend request"),
        (FRIEND_ACCEPTED, "Friend accepted"),
        (TRACE_ANALYZED, "Trace analyzed"),
        (REFERRAL_SIGNUP, "Referral signup"),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="notifications",
    )
    notification_type = models.CharField(max_length=20, choices=TYPE_CHOICES)
    message = models.CharField(max_length=255)
    link = models.CharField(max_length=255, blank=True, default="")
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=["user", "-created_at"]),
            models.Index(fields=["user", "is_read"]),
        ]
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.notification_type} for {self.user} — {self.message[:50]}"
