from django.db import models


class BaseStats(models.Model):
    period = models.DateField(unique=True)
    new_users = models.PositiveIntegerField(default=0)
    traces_uploaded = models.PositiveIntegerField(default=0)
    total_distance_km = models.FloatField(default=0.0)
    surfaces_detected = models.PositiveIntegerField(default=0)
    hexagons_acquired = models.PositiveIntegerField(default=0)
    new_hexagons_acquired = models.PositiveIntegerField(default=0)
    computed_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True
        ordering = ["-period"]

    def __str__(self):
        return f"{self.__class__.__name__} {self.period}"


class DailyStats(BaseStats):
    pass


class WeeklyStats(BaseStats):
    class Meta(BaseStats.Meta):
        constraints = [
            models.CheckConstraint(
                condition=models.Q(period__week_day=2),
                name="weeklystats_period_is_monday",
            ),
        ]


class MonthlyStats(BaseStats):
    class Meta(BaseStats.Meta):
        constraints = [
            models.CheckConstraint(
                condition=models.Q(period__day=1),
                name="monthlystats_period_is_first_of_month",
            ),
        ]


class YearlyStats(BaseStats):
    class Meta(BaseStats.Meta):
        constraints = [
            models.CheckConstraint(
                condition=models.Q(period__month=1, period__day=1),
                name="yearlystats_period_is_jan_first",
            ),
        ]


class BaseUserStats(models.Model):
    period = models.DateField()
    user_id = models.IntegerField()
    hexagons_acquired = models.PositiveIntegerField(default=0)
    computed_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True
        ordering = ["-period"]

    def __str__(self):
        return f"user {self.user_id} {self.period} — {self.hexagons_acquired}"


class UserDailyStats(BaseUserStats):
    pk = models.CompositePrimaryKey("user_id", "period")

    class Meta(BaseUserStats.Meta):
        managed = False


class UserWeeklyStats(BaseUserStats):
    class Meta(BaseUserStats.Meta):
        constraints = [
            models.UniqueConstraint(
                fields=["user_id", "period"],
                name="userweeklystats_user_id_period",
            ),
            models.CheckConstraint(
                condition=models.Q(period__week_day=2),
                name="userweeklystats_period_is_monday",
            ),
        ]


class UserMonthlyStats(BaseUserStats):
    class Meta(BaseUserStats.Meta):
        constraints = [
            models.UniqueConstraint(
                fields=["user_id", "period"],
                name="usermonthlystats_user_id_period",
            ),
            models.CheckConstraint(
                condition=models.Q(period__day=1),
                name="usermonthlystats_period_first_of_month",
            ),
        ]


class UserYearlyStats(BaseUserStats):
    class Meta(BaseUserStats.Meta):
        constraints = [
            models.UniqueConstraint(
                fields=["user_id", "period"],
                name="useryearlystats_user_id_period",
            ),
            models.CheckConstraint(
                condition=models.Q(period__month=1, period__day=1),
                name="useryearlystats_period_is_jan_first",
            ),
        ]


class LeaderboardEntry(models.Model):
    user_id = models.IntegerField()
    username = models.CharField(max_length=150)
    is_premium = models.BooleanField(default=False)
    hexagons_conquered = models.PositiveIntegerField(default=0)
    hexagons_acquired = models.PositiveIntegerField(default=0)
    total_points = models.PositiveIntegerField(default=0, db_default=0)
    rank_conquered = models.PositiveIntegerField()
    rank_acquired = models.PositiveIntegerField()
    rank_points = models.PositiveIntegerField(default=0, db_default=0)
    computed_at = models.DateTimeField()

    class Meta:
        indexes = [
            models.Index(fields=["rank_conquered"]),
            models.Index(fields=["rank_acquired"]),
            models.Index(fields=["rank_points"]),
        ]
        constraints = [
            models.UniqueConstraint(fields=["user_id"], name="leaderboard_user_unique"),
        ]

    def __str__(self):
        return f"{self.username} — conquered:{self.hexagons_conquered} acquired:{self.hexagons_acquired}"
