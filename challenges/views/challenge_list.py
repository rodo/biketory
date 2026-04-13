from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from django.utils import timezone

from challenges.models import Challenge, ChallengeLeaderboardEntry, ChallengeParticipant


@login_required
def challenge_list(request):
    now = timezone.now()
    user = request.user

    active_challenges = (
        Challenge.objects.filter(start_date__lte=now, end_date__gte=now, is_visible=True)
        .order_by("end_date")
    )

    upcoming_challenges = (
        Challenge.objects.filter(start_date__gt=now, is_visible=True)
        .order_by("start_date")
    )

    ended_challenges = (
        Challenge.objects.filter(end_date__lt=now, is_visible=True)
        .order_by("-end_date")[:20]
    )

    # Fetch user's participations
    user_challenge_ids = set(
        ChallengeParticipant.objects.filter(user=user)
        .values_list("challenge_id", flat=True)
    )

    # Fetch user's scores and ranks from leaderboard entries
    leaderboard_data = {
        row[0]: {"score": row[1], "rank": row[2]}
        for row in ChallengeLeaderboardEntry.objects.filter(user_id=user.pk)
        .values_list("challenge_id", "score", "rank")
    }

    # Split active challenges into joined / not joined
    my_challenges = []
    other_challenges = []
    for c in active_challenges:
        if c.pk in user_challenge_ids:
            entry = leaderboard_data.get(c.pk, {})
            c.user_score = entry.get("score", 0)
            c.user_rank = entry.get("rank")
            my_challenges.append(c)
        else:
            other_challenges.append(c)

    return render(request, "challenges/challenge_list.html", {
        "my_challenges": my_challenges,
        "other_challenges": other_challenges,
        "upcoming_challenges": upcoming_challenges,
        "ended_challenges": ended_challenges,
        "user_challenge_ids": user_challenge_ids,
    })
