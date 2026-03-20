from django.contrib import admin

from .models import Subscription, UserProfile


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display  = ("user", "daily_upload_limit")
    search_fields = ("user__username", "user__email")
    ordering      = ("user__username",)


@admin.register(Subscription)
class SubscriptionAdmin(admin.ModelAdmin):
    list_display  = ("user", "start_date", "end_date", "is_active")
    list_filter   = ("start_date", "end_date")
    search_fields = ("user__username",)
