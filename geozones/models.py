from django.contrib.gis.db import models as gis_models
from django.db import models


class GeoZone(models.Model):
    code = models.CharField(max_length=20)
    name = models.CharField(max_length=255)
    admin_level = models.PositiveSmallIntegerField()
    parent = models.ForeignKey(
        "self",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="children",
    )
    active = models.BooleanField(default=False)
    geom = gis_models.MultiPolygonField(srid=4326)
    loaded_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=["admin_level"]),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["code"],
                name="geozone_code_unique",
            ),
        ]

    def __str__(self):
        return f"{self.code} — {self.name} (level {self.admin_level})"


class ZoneLeaderboardEntry(models.Model):
    zone = models.ForeignKey(
        GeoZone,
        on_delete=models.CASCADE,
        related_name="leaderboard_entries",
    )
    user_id = models.IntegerField()
    username = models.CharField(max_length=150)
    is_premium = models.BooleanField(default=False)
    hexagons_conquered = models.PositiveIntegerField(default=0)
    hexagons_acquired = models.PositiveIntegerField(default=0)
    rank_conquered = models.PositiveIntegerField()
    rank_acquired = models.PositiveIntegerField()
    computed_at = models.DateTimeField()

    class Meta:
        indexes = [
            models.Index(fields=["zone", "rank_conquered"]),
            models.Index(fields=["zone", "rank_acquired"]),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["zone", "user_id"],
                name="zone_leaderboard_zone_user_unique",
            ),
        ]

    def __str__(self):
        return (
            f"{self.zone.code} — {self.username}"
            f" conquered:{self.hexagons_conquered} acquired:{self.hexagons_acquired}"
        )


class MonthlyZoneRanking(models.Model):
    zone = models.ForeignKey(
        GeoZone,
        on_delete=models.CASCADE,
        related_name="monthly_rankings",
    )
    period = models.DateField()  # first day of the month (e.g. 2026-04-01)
    user_id = models.IntegerField()
    username = models.CharField(max_length=150)
    is_premium = models.BooleanField(default=False)
    hexagons_conquered = models.PositiveIntegerField(default=0)
    hexagons_acquired = models.PositiveIntegerField(default=0)
    rank_conquered = models.PositiveIntegerField()
    rank_acquired = models.PositiveIntegerField()
    computed_at = models.DateTimeField()

    class Meta:
        indexes = [
            models.Index(fields=["zone", "period", "rank_conquered"]),
            models.Index(fields=["user_id", "rank_conquered"]),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["zone", "period", "user_id"],
                name="monthly_zone_ranking_unique",
            ),
        ]

    def __str__(self):
        return (
            f"{self.zone.code} — {self.username} — {self.period:%Y-%m}"
            f" conquered:{self.hexagons_conquered} acquired:{self.hexagons_acquired}"
        )
