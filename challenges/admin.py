from django.contrib import admin

from challenges.models import (
    Challenge,
    ChallengeHexagon,
    ChallengeLeaderboardEntry,
    ChallengeParticipant,
    ChallengeReward,
    ChallengeSponsor,
)


class ChallengeHexagonInline(admin.TabularInline):
    model = ChallengeHexagon
    extra = 0
    raw_id_fields = ["hexagon"]


class ChallengeRewardInline(admin.TabularInline):
    model = ChallengeReward
    extra = 0


class ChallengeSponsorInline(admin.TabularInline):
    model = ChallengeSponsor
    extra = 0


@admin.register(Challenge)
class ChallengeAdmin(admin.ModelAdmin):
    list_display = [
        "title", "challenge_type", "start_date", "end_date",
        "premium_only", "is_visible", "rewards_awarded_at",
    ]
    list_filter = ["challenge_type", "premium_only", "is_visible"]
    inlines = [ChallengeHexagonInline, ChallengeRewardInline, ChallengeSponsorInline]


@admin.register(ChallengeParticipant)
class ChallengeParticipantAdmin(admin.ModelAdmin):
    list_display = ["challenge", "user", "joined_at"]
    raw_id_fields = ["challenge", "user"]


@admin.register(ChallengeLeaderboardEntry)
class ChallengeLeaderboardEntryAdmin(admin.ModelAdmin):
    list_display = ["challenge", "rank", "username", "score", "computed_at"]
    list_filter = ["challenge"]
