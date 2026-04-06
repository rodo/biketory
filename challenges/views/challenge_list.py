from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from django.utils import timezone

from challenges.models import Challenge, ChallengeParticipant


@login_required
def challenge_list(request):
    now = timezone.now()

    active_challenges = (
        Challenge.objects.filter(start_date__lte=now, end_date__gte=now)
        .order_by("end_date")
    )

    upcoming_challenges = (
        Challenge.objects.filter(start_date__gt=now)
        .order_by("start_date")
    )

    ended_challenges = (
        Challenge.objects.filter(end_date__lt=now)
        .order_by("-end_date")[:20]
    )

    # Fetch user's participations
    user_challenge_ids = set(
        ChallengeParticipant.objects.filter(user=request.user)
        .values_list("challenge_id", flat=True)
    )

    return render(request, "challenges/challenge_list.html", {
        "active_challenges": active_challenges,
        "upcoming_challenges": upcoming_challenges,
        "ended_challenges": ended_challenges,
        "user_challenge_ids": user_challenge_ids,
    })
