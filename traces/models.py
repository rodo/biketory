import secrets
import uuid

from django.contrib.auth import get_user_model
from django.contrib.gis.db import models
from django.utils import timezone


class Trace(models.Model):
    STATUS_NOT_ANALYZED = "not_analyzed"
    STATUS_SURFACE_EXTRACTED = "surface_extracted"
    STATUS_ANALYZED = "analyzed"
    STATUS_CHOICES = [
        (STATUS_NOT_ANALYZED, "Not analyzed"),
        (STATUS_SURFACE_EXTRACTED, "Surface extracted"),
        (STATUS_ANALYZED, "Analyzed"),
    ]

    gpx_file = models.FileField(upload_to="gpx/")
    route = models.MultiLineStringField(null=True, blank=True)
    bbox = models.PolygonField(null=True, blank=True, srid=4326)
    length_km = models.FloatField(null=True, blank=True)
    extracted = models.BooleanField(default=False)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_NOT_ANALYZED)
    uuid = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    uploaded_by = models.ForeignKey(
        get_user_model(), null=True, blank=True, on_delete=models.SET_NULL, related_name="traces"
    )
    first_point_date = models.DateTimeField(null=True, blank=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=["uploaded_by", "uploaded_at"], name="trace_user_uploaded_at"),
            models.Index(fields=["uuid", "status"], name="trace_uuid_status"),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["uploaded_by", "first_point_date"],
                name="unique_trace_user_first_point_date",
            )
        ]

    def __str__(self):
        return f"Trace {self.pk} — {self.uploaded_at}"


class ClosedSurface(models.Model):
    trace = models.ForeignKey(Trace, on_delete=models.CASCADE, related_name="closed_surfaces")
    owner = models.ForeignKey(
        get_user_model(), null=True, blank=True, on_delete=models.SET_NULL, related_name="closed_surfaces"
    )
    segment_index = models.PositiveIntegerField(default=0)
    polygon = models.PolygonField()
    detected_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=["owner"], name="closedsurface_owner"),
        ]

    def __str__(self):
        return f"ClosedSurface #{self.pk} from Trace #{self.trace_id}"


class Hexagon(models.Model):
    geom = models.PolygonField(unique=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Hexagon #{self.pk}"


class HexagonScore(models.Model):
    hexagon = models.ForeignKey(Hexagon, on_delete=models.CASCADE, related_name="scores")
    user = models.ForeignKey(
        get_user_model(), on_delete=models.CASCADE, related_name="hexagon_scores"
    )
    points = models.PositiveIntegerField(default=0)
    last_earned_at = models.DateTimeField()

    class Meta:
        unique_together = [("hexagon", "user")]
        indexes = [
            models.Index(fields=["user", "points"], name="hexagonscore_user_points"),
        ]

    def __str__(self):
        return f"{self.user_id} — Hexagon #{self.hexagon_id} — {self.points}pt(s)"


class HexagonGainEvent(models.Model):
    hexagon = models.ForeignKey(Hexagon, on_delete=models.CASCADE, related_name="gain_events")
    user = models.ForeignKey(
        get_user_model(), on_delete=models.CASCADE, related_name="hexagon_gain_events"
    )
    earned_at = models.DateTimeField(db_index=True)
    is_first = models.BooleanField(default=False)

    class Meta:
        indexes = [
            models.Index(fields=["user", "earned_at"], name="hexagongainevent_user_earned"),
        ]

    def __str__(self):
        return f"{self.user_id} — Hexagon #{self.hexagon_id} — {self.earned_at:%Y-%m-%d}"


class UserProfile(models.Model):
    user = models.OneToOneField(
        get_user_model(), on_delete=models.CASCADE, related_name="profile"
    )
    daily_upload_limit = models.PositiveIntegerField(
        default=5,
        help_text="Maximum number of GPX uploads allowed per rolling 24-hour window.",
    )
    home_location = models.PointField(null=True, blank=True, srid=4326)
    hexagram = models.CharField(max_length=6, unique=True, editable=False)

    def __str__(self):
        return f"{self.user.username} (limit: {self.daily_upload_limit}/day)"


class Friendship(models.Model):
    STATUS_PENDING = "pending"
    STATUS_ACCEPTED = "accepted"
    STATUS_CHOICES = [(STATUS_PENDING, "Pending"), (STATUS_ACCEPTED, "Accepted")]

    from_user = models.ForeignKey(
        get_user_model(), on_delete=models.CASCADE, related_name="friendships_sent"
    )
    to_user = models.ForeignKey(
        get_user_model(), on_delete=models.CASCADE, related_name="friendships_received"
    )
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default=STATUS_PENDING)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["from_user", "to_user"], name="unique_friendship")
        ]

    def __str__(self):
        return f"{self.from_user} → {self.to_user} ({self.status})"


class UserSurfaceStats(models.Model):
    user = models.OneToOneField(
        get_user_model(), on_delete=models.CASCADE, related_name="surface_stats"
    )
    total_area = models.FloatField(default=0.0, help_text="Total area of owned closed surfaces in deg²")
    union = models.MultiPolygonField(null=True, blank=True, help_text="Union of all owned closed surfaces")
    secret_uuid = models.UUIDField(default=uuid.uuid4, unique=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.username} — {self.total_area:.6f} deg²"


class ApiToken(models.Model):
    user = models.ForeignKey(
        get_user_model(), on_delete=models.CASCADE, related_name="api_tokens"
    )
    token = models.CharField(max_length=64, unique=True, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()

    def save(self, *args, **kwargs):
        if not self.token:
            self.token = secrets.token_hex(32)
        super().save(*args, **kwargs)

    @property
    def is_valid(self):
        from django.utils import timezone
        return timezone.now() < self.expires_at

    def __str__(self):
        return f"{self.user.username} — expires {self.expires_at:%Y-%m-%d}"

    class Meta:
        ordering = ["-created_at"]


class Subscription(models.Model):
    user = models.OneToOneField(
        get_user_model(), on_delete=models.CASCADE, related_name="subscription"
    )
    start_date = models.DateField()
    end_date = models.DateField()
    created_at = models.DateTimeField(auto_now_add=True)

    def is_active(self):
        today = timezone.now().date()
        return self.start_date <= today <= self.end_date

    def __str__(self):
        return f"{self.user.username} ({self.start_date} → {self.end_date})"


class UserBadge(models.Model):
    user = models.ForeignKey(
        get_user_model(), on_delete=models.CASCADE, related_name="badges"
    )
    badge_id = models.CharField(max_length=50)
    trace = models.ForeignKey(
        "Trace", null=True, blank=True, on_delete=models.SET_NULL, related_name="badges"
    )
    earned_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["user", "badge_id"], name="unique_user_badge"),
        ]

    def __str__(self):
        return f"{self.user} — {self.badge_id}"


class MonthlyStatsRefresh(models.Model):
    """Singleton row tracking when the hexagon_monthly_stats matview was last refreshed."""
    refreshed_at = models.DateTimeField()

    class Meta:
        db_table = "traces_monthlystatsrefresh"
