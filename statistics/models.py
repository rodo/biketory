from django.db import models


class BaseStats(models.Model):
    period = models.DateField(unique=True)
    new_users = models.PositiveIntegerField(default=0)
    traces_uploaded = models.PositiveIntegerField(default=0)
    total_distance_km = models.FloatField(default=0.0)
    surfaces_detected = models.PositiveIntegerField(default=0)
    hexagons_earned = models.PositiveIntegerField(default=0)
    computed_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True
        ordering = ["-period"]

    def __str__(self):
        return f"{self.__class__.__name__} {self.period}"


class DailyStats(BaseStats):
    pass


class WeeklyStats(BaseStats):
    pass


class MonthlyStats(BaseStats):
    pass


class YearlyStats(BaseStats):
    pass
