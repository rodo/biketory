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
