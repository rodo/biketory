from django.contrib import admin

from .models import DailyStats, MonthlyStats, WeeklyStats, YearlyStats


class BaseStatsAdmin(admin.ModelAdmin):
    list_display = ("period", "new_users", "traces_uploaded", "total_distance_km",
                    "surfaces_detected", "hexagons_acquired", "new_hexagons_acquired",
                    "computed_at")
    list_filter = ("period",)
    ordering = ("-period",)


@admin.register(DailyStats)
class DailyStatsAdmin(BaseStatsAdmin):
    pass


@admin.register(WeeklyStats)
class WeeklyStatsAdmin(BaseStatsAdmin):
    pass


@admin.register(MonthlyStats)
class MonthlyStatsAdmin(BaseStatsAdmin):
    pass


@admin.register(YearlyStats)
class YearlyStatsAdmin(BaseStatsAdmin):
    pass
