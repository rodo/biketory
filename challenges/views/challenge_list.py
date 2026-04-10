from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from django.utils import timezone

from challenges.models import Challenge, ChallengeLeaderboardEntry, ChallengeParticipant


@login_required
def challenge_list(request):
    now = timezone.now()
    user = request.user

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

    # Fetch user's participations with scores
    participant_scores = dict(
        ChallengeParticipant.objects.filter(user=user)
        .values_list("challenge_id", "score")
    )
    user_challenge_ids = set(participant_scores.keys())

    # Fetch user's ranks from leaderboard entries
    user_ranks = dict(
        ChallengeLeaderboardEntry.objects.filter(user_id=user.pk)
        .values_list("challenge_id", "rank")
    )

    # Split active challenges into joined / not joined
    my_challenges = []
    other_challenges = []
    for c in active_challenges:
        if c.pk in user_challenge_ids:
            c.user_score = participant_scores.get(c.pk, 0)
            c.user_rank = user_ranks.get(c.pk)
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
