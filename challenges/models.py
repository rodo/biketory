from django.conf import settings
from django.contrib.gis.db import models as gis_models
from django.db import models


class Dataset(models.Model):
    name = models.CharField(max_length=255)
    source_file = models.CharField(max_length=500)
    md5_hash = models.CharField(max_length=32, unique=True)
    feature_count = models.PositiveIntegerField(default=0)
    imported_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name


class DatasetFeature(models.Model):
    dataset = models.ForeignKey(
        Dataset,
        on_delete=models.CASCADE,
        related_name="features",
    )
    geom = gis_models.PointField(srid=4326)
    properties = models.JSONField(default=dict)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=["dataset"]),
        ]

    def __str__(self):
        return f"Feature #{self.pk} — Dataset #{self.dataset_id}"


class Challenge(models.Model):
    TYPE_CAPTURE_HEXAGON = "capture_hexagon"
    TYPE_MAX_POINTS = "max_points"
    TYPE_ACTIVE_DAYS = "active_days"
    TYPE_NEW_HEXAGONS = "new_hexagons"
    TYPE_DISTINCT_ZONES = "distinct_zones"
    TYPE_DATASET_POINTS = "dataset_points"
    TYPE_CHOICES = [
        (TYPE_CAPTURE_HEXAGON, "Capture hexagon"),
        (TYPE_MAX_POINTS, "Max points"),
        (TYPE_ACTIVE_DAYS, "Active days"),
        (TYPE_NEW_HEXAGONS, "New hexagons"),
        (TYPE_DISTINCT_ZONES, "Distinct zones"),
        (TYPE_DATASET_POINTS, "Dataset points"),
    ]

    CAPTURE_ANY = "any"
    CAPTURE_ALL = "all"
    CAPTURE_MODE_CHOICES = [
        (CAPTURE_ANY, "Any (at least one)"),
        (CAPTURE_ALL, "All"),
    ]

    title = models.CharField(max_length=255)
    description = models.TextField(blank=True, default="")
    challenge_type = models.CharField(max_length=20, choices=TYPE_CHOICES)
    capture_mode = models.CharField(
        max_length=5,
        choices=CAPTURE_MODE_CHOICES,
        null=True,
        blank=True,
    )
    premium_only = models.BooleanField(default=False)
    geozone = models.ForeignKey(
        "geozones.GeoZone",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="challenges",
    )
    start_date = models.DateTimeField()
    end_date = models.DateTimeField()
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="created_challenges",
    )
    dataset = models.ForeignKey(
        Dataset,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="challenges",
    )
    goal_threshold = models.PositiveIntegerField(null=True, blank=True)
    zone_admin_level = models.PositiveSmallIntegerField(null=True, blank=True)
    hexagons_per_zone = models.PositiveIntegerField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=["start_date"]),
            models.Index(fields=["end_date"]),
        ]

    def __str__(self):
        return self.title


class ChallengeHexagon(models.Model):
    challenge = models.ForeignKey(
        Challenge,
        on_delete=models.CASCADE,
        related_name="challenge_hexagons",
    )
    hexagon = models.ForeignKey(
        "traces.Hexagon",
        on_delete=models.CASCADE,
        related_name="challenge_hexagons",
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["challenge", "hexagon"],
                name="challenge_hexagon_unique",
            ),
        ]

    def __str__(self):
        return f"Challenge #{self.challenge_id} — Hexagon #{self.hexagon_id}"


class ChallengeParticipant(models.Model):
    challenge = models.ForeignKey(
        Challenge,
        on_delete=models.CASCADE,
        related_name="participants",
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="challenge_participations",
    )
    score = models.IntegerField(default=0)
    joined_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["challenge", "user"],
                name="challenge_participant_unique",
            ),
        ]

    def __str__(self):
        return f"Challenge #{self.challenge_id} — User #{self.user_id}"


class ChallengeLeaderboardEntry(models.Model):
    challenge = models.ForeignKey(
        Challenge,
        on_delete=models.CASCADE,
        related_name="leaderboard_entries",
    )
    user_id = models.IntegerField()
    username = models.CharField(max_length=150)
    is_premium = models.BooleanField(default=False)
    score = models.IntegerField(default=0)
    goal_met = models.BooleanField(default=True)
    rank = models.PositiveIntegerField()
    computed_at = models.DateTimeField()

    class Meta:
        indexes = [
            models.Index(fields=["challenge", "rank"]),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["challenge", "user_id"],
                name="challenge_leaderboard_unique",
            ),
        ]

    def __str__(self):
        return f"Challenge #{self.challenge_id} — #{self.rank} {self.username}"


class ChallengeSponsor(models.Model):
    challenge = models.ForeignKey(
        Challenge,
        on_delete=models.CASCADE,
        related_name="sponsors",
    )
    name = models.CharField(max_length=255)
    logo = models.ImageField(upload_to="challenges/sponsors/", blank=True, null=True)
    url = models.URLField(blank=True, default="")

    def __str__(self):
        return f"{self.name} — Challenge #{self.challenge_id}"


class ChallengeReward(models.Model):
    REWARD_BADGE = "badge"
    REWARD_SUB_3M = "subscription_3m"
    REWARD_SUB_6M = "subscription_6m"
    REWARD_SUB_1Y = "subscription_1y"
    REWARD_TYPE_CHOICES = [
        (REWARD_BADGE, "Badge"),
        (REWARD_SUB_3M, "Subscription 3 months"),
        (REWARD_SUB_6M, "Subscription 6 months"),
        (REWARD_SUB_1Y, "Subscription 1 year"),
    ]

    challenge = models.ForeignKey(
        Challenge,
        on_delete=models.CASCADE,
        related_name="rewards",
    )
    rank_threshold = models.PositiveIntegerField()
    reward_type = models.CharField(max_length=20, choices=REWARD_TYPE_CHOICES)
    badge_id = models.CharField(max_length=50, blank=True, default="")

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["challenge", "rank_threshold", "reward_type"],
                name="challenge_reward_unique",
            ),
        ]

    def __str__(self):
        return f"Challenge #{self.challenge_id} — rank≤{self.rank_threshold} → {self.reward_type}"


class ChallengeDatasetScore(models.Model):
    challenge = models.ForeignKey(
        Challenge,
        on_delete=models.CASCADE,
        related_name="dataset_scores",
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="challenge_dataset_scores",
    )
    dataset_feature = models.ForeignKey(
        DatasetFeature,
        on_delete=models.CASCADE,
        related_name="challenge_scores",
    )
    trace = models.ForeignKey(
        "traces.Trace",
        on_delete=models.CASCADE,
        related_name="challenge_dataset_scores",
    )
    earned_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=["challenge", "user"]),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["challenge", "user", "dataset_feature"],
                name="challenge_dataset_score_unique",
            ),
        ]

    def __str__(self):
        return f"Challenge #{self.challenge_id} — User #{self.user_id} — Feature #{self.dataset_feature_id}"
