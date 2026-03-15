from django.contrib import admin

from .models import UserProfile


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display  = ("user", "daily_upload_limit")
    search_fields = ("user__username", "user__email")
    ordering      = ("user__username",)
