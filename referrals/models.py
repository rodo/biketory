import secrets

from django.conf import settings
from django.db import models


def _generate_token():
    return secrets.token_urlsafe(24)


class Referral(models.Model):
    PENDING = "pending"
    ACCEPTED = "accepted"
    STATUS_CHOICES = [
        (PENDING, "Pending"),
        (ACCEPTED, "Accepted"),
    ]

    sponsor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="referrals_sent",
    )
    email = models.EmailField()
    token = models.CharField(max_length=64, unique=True, default=_generate_token)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default=PENDING)
    referee = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="referral_received",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    accepted_at = models.DateTimeField(null=True, blank=True)
    rewarded = models.BooleanField(default=False)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["sponsor", "email"],
                name="unique_referral_sponsor_email",
            ),
        ]
        indexes = [
            models.Index(fields=["token"]),
            models.Index(fields=["email"]),
        ]

    def __str__(self):
        return f"Referral {self.sponsor} → {self.email} ({self.status})"
